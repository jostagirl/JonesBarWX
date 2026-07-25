import os
import logging
import pymysql
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("weather_ingest")


def get_db_connection():
    """Establish and return a PyMySQL connection to MariaDB."""
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306)),
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor
    )


def get_maintenance_mode():
    """Check if system maintenance mode is flag-enabled via environment."""
    return os.getenv("MAINTENANCE_MODE", "false").lower() in ("true", "1", "yes")


def sync_table_schema(cursor, table_name, data):
    """
    Dynamically check if columns in payload exist in the target table.
    Adds missing columns as FLOAT or VARCHAR if they do not exist yet.
    """
    if not data:
        return

    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
    existing_cols = {row["Field"] for row in cursor.fetchall()}

    for col_name, val in data.items():
        if col_name not in existing_cols:
            # Determine suitable SQL data type based on sample value
            if isinstance(val, (int, float)):
                col_type = "FLOAT NULL"
            elif isinstance(val, str) and len(val) <= 50:
                col_type = "VARCHAR(50) NULL"
            else:
                col_type = "TEXT NULL"

            alter_query = f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_type}"
            cursor.execute(alter_query)
            logger.info(f"Added new column '{col_name}' ({col_type}) to table '{table_name}'")


def insert_if_changed(cursor, table_name, data):
    """
    Insert observation or update non-primary fields on duplicate key.
    Utilizes composite primary keys (e.g. station_id, timestamp_utc).
    """
    if not data:
        return

    columns = list(data.keys())
    fields = ", ".join([f"`{c}`" for c in columns])
    placeholders = ", ".join(["%s" for _ in columns])
    
    # Build ON DUPLICATE KEY UPDATE clause for dynamic fields
    update_clause = ", ".join([f"`{c}` = VALUES(`{c}`)" for c in columns if c not in ("station_id", "timestamp_utc")])

    if update_clause:
        sql = f"INSERT INTO `{table_name}` ({fields}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause}"
    else:
        sql = f"INSERT IGNORE INTO `{table_name}` ({fields}) VALUES ({placeholders})"

    values = [data[c] for c in columns]
    cursor.execute(sql, values)


def log_system_health(station_id, api_success, db_success):
    """
    Record execution status (API harvest success & DB write success)
    into the system_health table.
    """
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO system_health (timestamp_utc, station_id, api_success, db_success)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (now_utc, station_id, api_success, db_success))
            conn.commit()
            logger.info(f"Logged health status for '{station_id}': API={api_success}, DB={db_success}")
    except Exception as err:
        logger.error(f"Failed to write system_health log for '{station_id}': {err}")
    finally:
        conn.close()
