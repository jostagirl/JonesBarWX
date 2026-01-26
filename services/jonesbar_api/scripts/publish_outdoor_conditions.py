
#!/usr/bin/env python3
import os
import json
import csv
import subprocess
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

    payload = {
        "dataset": "outdoor_conditions",
        "window": "last_7_days",
        "generated_at_utc": generated_at_utc,
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

    # Syncbefore pushing
    run(["git", "pull", "--rebase"], cwd=PUBLIC_REPO_DIR)

    # Stage only the two files
    run(["git", "add", "data/outdoor_conditions.json", "data/outdoor_conditions.csv"], cwd=PUBLIC_REPO_DIR)

    # If nothing changed, do not commit
    status = run(["git", "status", "--porcelain"], cwd=PUBLIC_REPO_DIR)
    if status.strip() == "":
        return False

    msg = f"Publish outdoor_conditions last 7 days ({generated_at_utc})"
    run(["git", "commit", "-m", msg], cwd=PUBLIC_REPO_DIR)
    run(["git", "push"], cwd=PUBLIC_REPO_DIR)
    return True


def main():
    row_count, generated_at_utc = export_outdoor_conditions_last_7_days()
    changed = git_publish_if_changed(generated_at_utc)
    print(f"Exported rows: {row_count}")
    print(f"Generated at: {generated_at_utc}")
    print(f"Published: {changed}")


if __name__ == "__main__":
    main()
