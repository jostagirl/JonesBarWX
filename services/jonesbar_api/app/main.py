from fastapi import FastAPI, Query
from .db import get_connection

app = FastAPI(title="Jones Bar API")

@app.get("/health")
def health():
    return {"status": "ok"}

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

