
#!/usr/bin/env python3
import os
import sys
import json
import csv
import time
import subprocess
import urllib.request
from datetime import datetime, timezone,date

import pymysql
from dotenv import load_dotenv


# Paths (edit only if you move folders)
API_ENV_FILE = "/home/pi4/repo/JonesBarWX/services/jonesbar_api/.env"
PUBLIC_REPO_DIR = "/home/pi4/repo_public/PublicJonesBarWX_API"
PUBLIC_DATA_DIR = os.path.join(PUBLIC_REPO_DIR, "data")
JSON_OUT = os.path.join(PUBLIC_DATA_DIR, "outdoor_conditions.json")
CSV_OUT = os.path.join(PUBLIC_DATA_DIR, "outdoor_conditions.csv")


def run(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result.stdout.strip()


def run_with_retry(cmd, cwd=None, attempts=3, initial_delay=2.0):
    # Use for network-touching git commands (fetch, push) to ride out transient failures.
    last_err = None
    for i in range(attempts):
        try:
            return run(cmd, cwd=cwd)
        except RuntimeError as e:
            last_err = e
            if i < attempts - 1:
                delay = initial_delay * (2 ** i)
                print(f"[{cmd[0]} {cmd[1] if len(cmd) > 1 else ''}] attempt {i+1}/{attempts} failed; retrying in {delay:.0f}s", file=sys.stderr)
                time.sleep(delay)
    raise last_err


def ensure_clean_public_repo():
    # Public repo is a pure publisher — working tree is disposable.
    # Abort any interrupted rebase/merge, then hard-reset to match origin.
    if not os.path.isdir(os.path.join(PUBLIC_REPO_DIR, ".git")):
        raise RuntimeError(f"Not a git repo: {PUBLIC_REPO_DIR}")

    git_dir = os.path.join(PUBLIC_REPO_DIR, ".git")
    for state_dir in ("rebase-merge", "rebase-apply"):
        if os.path.isdir(os.path.join(git_dir, state_dir)):
            print(f"Interrupted rebase detected ({state_dir}); aborting.")
            try:
                run(["git", "rebase", "--abort"], cwd=PUBLIC_REPO_DIR)
            except RuntimeError as e:
                print(f"rebase --abort failed ({e}); continuing with hard reset.", file=sys.stderr)
            break
    if os.path.isfile(os.path.join(git_dir, "MERGE_HEAD")):
        print("Interrupted merge detected; aborting.")
        try:
            run(["git", "merge", "--abort"], cwd=PUBLIC_REPO_DIR)
        except RuntimeError as e:
            print(f"merge --abort failed ({e}); continuing with hard reset.", file=sys.stderr)

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=PUBLIC_REPO_DIR)
    if branch == "HEAD":
        raise RuntimeError("Public repo is in detached HEAD state; refusing to auto-recover.")

    run_with_retry(["git", "fetch", "origin", branch], cwd=PUBLIC_REPO_DIR)
    run(["git", "reset", "--hard", f"origin/{branch}"], cwd=PUBLIC_REPO_DIR)
    run(["git", "clean", "-fd"], cwd=PUBLIC_REPO_DIR)


def get_db_connection():
    load_dotenv(API_ENV_FILE)

    host = os.getenv("DB_HOST", "127.0.0.1")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")
    database = os.getenv("DB_NAME")

    if not user or not password or not database:
        raise RuntimeError("Missing DB_USER, DB_PASS, or DB_NAME in API .env file")

    return pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )

def make_json_safe(value):
    if isinstance(value, (datetime, date)):
        # ISO format, keep it consistent
        return value.isoformat()
    return value

def rows_json_safe(rows):
    safe = []
    for row in rows:
        safe.append({k: make_json_safe(v) for k, v in row.items()})
    return safe

def export_outdoor_conditions_last_7_days():
    os.makedirs(PUBLIC_DATA_DIR, exist_ok=True)

    sql = """
        SELECT *
        FROM outdoor_conditions
        WHERE timestamp_utc >= (UTC_TIMESTAMP() - INTERVAL 7 DAY)
        ORDER BY timestamp_utc ASC
    """

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

        latest_row_timestamp_utc = None
        if rows and "timestamp_utc" in rows[-1]:
            # rows are ordered ASC, so last row is newest
            ts = rows[-1]["timestamp_utc"]
            if ts is not None:
                latest_row_timestamp_utc = (
                    ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
                )

    finally:
        conn.close()


    generated_at_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    safe_rows = rows_json_safe(rows)

    latest_row_timestamp_utc = None
    if safe_rows:
        # Prefer ISO timestamp string if present
        latest_row_timestamp_utc = safe_rows[-1].get("timestamp_utc")

        # Fallback: if only epoch seconds exists (field "ts"), convert to ISO UTC
        if not latest_row_timestamp_utc and safe_rows[-1].get("ts") is not None:
            latest_row_timestamp_utc = datetime.fromtimestamp(
                int(safe_rows[-1]["ts"]), tz=timezone.utc
            ).isoformat().replace("+00:00", "Z")

    payload = {
        "dataset": "outdoor_conditions",
        "window": "last_7_days",
        "generated_at_utc": generated_at_utc,
        "latest_row_timestamp_utc": latest_row_timestamp_utc,
	"row_count": len(safe_rows),
        "rows": safe_rows,
    }

    # Write JSON
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    # Write CSV
    if safe_rows:
        fieldnames = list(safe_rows[0].keys())
        with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(safe_rows)
    else:
        with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
            f.write("")

    return len(safe_rows), generated_at_utc


def git_publish_if_changed(generated_at_utc):
    # Ensure we are in the public repo
    if not os.path.isdir(os.path.join(PUBLIC_REPO_DIR, ".git")):
        raise RuntimeError(f"Not a git repo: {PUBLIC_REPO_DIR}")

    # Stage only the two files
    run(["git", "add", "data/outdoor_conditions.json", "data/outdoor_conditions.csv"], cwd=PUBLIC_REPO_DIR)

    # If nothing changed, do not commit
    status = run(["git", "status", "--porcelain"], cwd=PUBLIC_REPO_DIR)
    if status.strip() == "":
        return False

    msg = f"Publish outdoor_conditions last 7 days ({generated_at_utc})"
    run(["git", "commit", "-m", msg], cwd=PUBLIC_REPO_DIR)
    run_with_retry(["git", "push"], cwd=PUBLIC_REPO_DIR)
    return True


def _heartbeat(url):
    if not url:
        return
    try:
        urllib.request.urlopen(url, timeout=10).read()
    except Exception as e:
        print(f"Publish heartbeat ping failed (non-fatal): {e}", file=sys.stderr)


def main():
    try:
        ensure_clean_public_repo()
        row_count, generated_at_utc = export_outdoor_conditions_last_7_days()
        changed = git_publish_if_changed(generated_at_utc)
        print(f"Exported rows: {row_count}")
        print(f"Generated at: {generated_at_utc}")
        print(f"Published: {changed}")
        _heartbeat(os.getenv("PUBLISH_OK_URL", "").strip())
    except Exception as e:
        print(f"ERROR: publish_outdoor_conditions failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
