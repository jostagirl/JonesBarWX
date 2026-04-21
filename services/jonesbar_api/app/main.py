from datetime import datetime, timezone

from fastapi import FastAPI, Query, Response
from fastapi.responses import PlainTextResponse

from .db import get_connection

app = FastAPI(title="Jones Bar API")

FRESHNESS_THRESHOLD_SECONDS = 30 * 60


def _freshness_check(latest_ts):
    if latest_ts is None:
        return {"ok": False, "error": "no rows"}
    if latest_ts.tzinfo is None:
        latest_ts = latest_ts.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - latest_ts).total_seconds()
    return {
        "ok": age <= FRESHNESS_THRESHOLD_SECONDS,
        "age_seconds": int(age),
        "latest": latest_ts.isoformat(),
    }


@app.get("/health")
def health(response: Response):
    checks = {}

    try:
        conn = get_connection()
    except Exception as e:
        response.status_code = 503
        return {
            "status": "degraded",
            "checks": {"db": {"ok": False, "error": str(e)[:200]}},
        }

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(timestamp_utc) AS latest FROM outdoor_conditions")
            row = cur.fetchone() or {}
            checks["outdoor_conditions_fresh"] = _freshness_check(row.get("latest"))

            cur.execute(
                "SELECT timestamp_utc, api_success FROM system_health "
                "ORDER BY timestamp_utc DESC LIMIT 1"
            )
            row = cur.fetchone()
            if row:
                sh = _freshness_check(row["timestamp_utc"])
                sh["api_success"] = row["api_success"]
                if row["api_success"] != 1:
                    sh["ok"] = False
                checks["system_health_fresh"] = sh
            else:
                checks["system_health_fresh"] = {"ok": False, "error": "no rows"}

            checks["db"] = {"ok": True}
    except Exception as e:
        response.status_code = 503
        return {
            "status": "degraded",
            "checks": {"db": {"ok": False, "error": str(e)[:200]}},
        }
    finally:
        conn.close()

    ok = all(c.get("ok") for c in checks.values())
    if not ok:
        response.status_code = 503
    return {"status": "ok" if ok else "degraded", "checks": checks}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    try:
        conn = get_connection()
    except Exception as e:
        return PlainTextResponse(f"# DB unavailable: {e}\n", status_code=503)

    lines = []

    def gauge(name, help_text, value):
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name} {value}")

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT api_success, db_success, insert_outdoor, insert_indoor,
                       insert_barometric, insert_network, skipped_inserts,
                       is_maintenance, errors, timestamp_utc
                FROM system_health ORDER BY timestamp_utc DESC LIMIT 1
            """)
            sh = cur.fetchone()

            cur.execute("SELECT MAX(timestamp_utc) AS latest FROM outdoor_conditions")
            oc = cur.fetchone()
    finally:
        conn.close()

    now = datetime.now(timezone.utc)

    if sh:
        ts = sh["timestamp_utc"]
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ingest_age = int((now - ts).total_seconds()) if ts else -1

        gauge("jonesbar_api_success",        "Last ingest API call succeeded (1=yes 0=no)",   sh["api_success"] or 0)
        gauge("jonesbar_db_success",         "Last ingest DB write succeeded (1=yes 0=no)",   sh["db_success"] or 0)
        gauge("jonesbar_insert_outdoor",     "Last run inserted outdoor row",                 sh["insert_outdoor"] or 0)
        gauge("jonesbar_insert_indoor",      "Last run inserted indoor row",                  sh["insert_indoor"] or 0)
        gauge("jonesbar_insert_barometric",  "Last run inserted barometric row",              sh["insert_barometric"] or 0)
        gauge("jonesbar_insert_network",     "Last run inserted network row",                 sh["insert_network"] or 0)
        gauge("jonesbar_skipped_inserts",    "Rows skipped (no change) last run",             sh["skipped_inserts"] or 0)
        gauge("jonesbar_is_maintenance",     "Station in maintenance mode (1=yes)",           sh["is_maintenance"] or 0)
        gauge("jonesbar_ingest_has_error",   "Last ingest run had an error (1=yes)",          1 if sh["errors"] else 0)
        gauge("jonesbar_ingest_age_seconds", "Seconds since last ingest run",                 ingest_age)

    if oc and oc.get("latest"):
        latest = oc["latest"]
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=timezone.utc)
        gauge("jonesbar_outdoor_data_age_seconds", "Seconds since newest outdoor_conditions row",
              int((now - latest).total_seconds()))

    return PlainTextResponse("\n".join(lines) + "\n")


@app.get("/api/system_health/recent")
def recent_system_health(limit: int = Query(10, ge=1, le=200)):
    sql = """
        SELECT timestamp_utc, api_success, insert_network, skipped_inserts
        FROM system_health
        ORDER BY timestamp_utc DESC
        LIMIT %s
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
        return {"count": len(rows), "rows": rows}
    finally:
        conn.close()
