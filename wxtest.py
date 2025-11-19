import pymysql
import requests
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from dotenv import load_dotenv
import os
import time

# === CONFIGURATION ===
load_dotenv()

# Load Credentials
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
API_KEY = os.getenv("API_KEY", "").strip()
API_SECRET = os.getenv("API_SECRET", "").strip()
STATION_ID = os.getenv("STATION_ID", "").strip()

API_URL = f'https://api.weatherlink.com/v2/current/{STATION_ID}?api-key={API_KEY}'
headers = {'X-Api-Secret': API_SECRET}

#####LOGGING SETUP

#######DEPRICATED
# LOG_PATH = r'C:\Users\Anna\Projects\WeatherLogger\logs\weather_log.txt'
# logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#######

# --- logging config (replaces previous logging.basicConfig call) ---
LOG_DIR = r'C:\Users\Anna\Projects\WeatherLogger\logs'
LOG_FILENAME = 'weather_log.txt'
LOG_PATH = os.path.join(LOG_DIR, LOG_FILENAME)

# make sure directory exists
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger()           # root logger (same as logging.* calls)
logger.setLevel(logging.INFO)

# Remove any existing handlers to avoid duplicate logs if the module is reloaded
if logger.handlers:
    for h in logger.handlers[:]:
        logger.removeHandler(h)

# Timed rotating handler: rotate at midnight every day, keep 7 backups.
# Using utc=True makes rotation schedule independent of local TZ (good for consistent timestamps).
handler = TimedRotatingFileHandler(
    filename=LOG_PATH,
    when='midnight',     # rotate at midnight 
    interval=1,
    backupCount=7,       # keep last 7 files
    utc=True,            # rotate based on UTC; set False if you prefer local midnight rotation
    encoding='utf-8'
)

# Optional: add a header when opening a new log file
handler.suffix = "%Y-%m-%d"  # file suffix format used for backups, e.g. weather_log.txt.2025-11-19
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Also keep a simple stream handler so you can see logs on console while testing
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(formatter)
logger.addHandler(console)

# Write a startup line so the log shows that the script started
logger.info("=== Logger started (TimedRotatingFileHandler) ===")
# ---------------------------------------------------------------------

# === METRIC TRACKING ===
metrics = {
    "api_success": 0,
    "db_success": 0,
    "insert_outdoor": 0,
    "insert_indoor": 0,
    "insert_barometric": 0,
    "insert_network": 0,
    "skipped_inserts": 0,
    "errors": None
}

# === UTILITY FUNCTIONS ===

def get_sensor_data(sensors, sensor_type):
    for s in sensors:
        if s.get('sensor_type') == sensor_type and s.get('data'):
            return s['data'][0]
    return None

def data_changed(cursor, table, fields, values):
    select = f"SELECT {', '.join(fields)} FROM {table} ORDER BY timestamp_utc DESC LIMIT 1"
    cursor.execute(select)
    row = cursor.fetchone()
    return row != values

def insert_if_changed(cursor, table, timestamp, data_dict):
    fields = sorted(data_dict.keys())
    values = tuple(data_dict[f] for f in fields)
    if data_changed(cursor, table, fields, values):
        placeholders = ', '.join(['%s'] * len(fields))
        query = f"""
            INSERT INTO {table} (timestamp_utc, {', '.join(fields)})
            VALUES (%s, {placeholders})
        """
        cursor.execute(query, (timestamp,) + values)
        logging.info(f"Inserted new data into {table} at {timestamp}")
        return True
    else:
        logging.info(f"No change in {table} at {timestamp} — skipping insert.")
        return False

def sync_table_schema(cursor, table_name, data_dict):
    cursor.execute(f"SHOW COLUMNS FROM {table_name}")
    existing_columns = set(row[0] for row in cursor.fetchall())

    for key, value in data_dict.items():
        if key not in existing_columns:
            # Guess column type
            if isinstance(value, int):
                sql_type = "INT"
            elif isinstance(value, float):
                sql_type = "FLOAT"
            elif isinstance(value, str):
                sql_type = "VARCHAR(255)"
            else:
                sql_type = "TEXT"

            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {key} {sql_type}"
            try:
                cursor.execute(alter_sql)
                logging.info(f"✅ Added column `{key}` to `{table_name}` as {sql_type}")
            except Exception as e:
                logging.error(f"❌ Failed to add column `{key}` to `{table_name}`: {e}")

# === MAIN SCRIPT ===

start_time = time.time()

try:
    response = requests.get(API_URL, headers=headers)
    response.raise_for_status()
    api_data = response.json()
    sensors = api_data.get('sensors', [])
    metrics['api_success'] = 1

    outdoor = get_sensor_data(sensors, 43)
    indoor = get_sensor_data(sensors, 243)
    baro = get_sensor_data(sensors, 242)
    network = get_sensor_data(sensors, 504)

    with pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME) as connection:
        with connection.cursor() as cursor:
            
            # outdoor
            if outdoor:
                sync_table_schema(cursor, 'outdoor_conditions', outdoor)
                if insert_if_changed(cursor, 'outdoor_conditions', datetime.utcfromtimestamp(outdoor['ts']), outdoor):
                    metrics["insert_outdoor"] = 1
                else:
                    metrics["skipped_inserts"] += 1

            # indoor
            if indoor:
                sync_table_schema(cursor, 'indoor_conditions', indoor)
                if insert_if_changed(cursor, 'indoor_conditions', datetime.utcfromtimestamp(indoor['ts']), indoor):
                    metrics["insert_indoor"] = 1
                else:
                    metrics["skipped_inserts"] += 1

            # baro
            if baro:
                sync_table_schema(cursor, 'barometric_conditions', baro)
                if insert_if_changed(cursor, 'barometric_conditions', datetime.utcfromtimestamp(baro['ts']), baro):
                    metrics["insert_barometric"] = 1
                else:
                    metrics["skipped_inserts"] += 1

            # network
            if network:
                sync_table_schema(cursor, 'network_status', network)
                if insert_if_changed(cursor, 'network_status', datetime.utcfromtimestamp(network['ts']), network):
                    metrics["insert_network"] = 1
                else:
                    metrics["skipped_inserts"] += 1

            metrics["db_success"] = 1
        connection.commit()

except Exception as e:
    metrics["errors"] = str(e)[:250]
    logging.error(f"Error: {e}")

finally:
    # duration_ms = int((time.time() - start_time) * 1000)
    timestamp = datetime.utcnow()

    try:
        with pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO system_health 
                    (timestamp_utc, api_success, db_success, insert_outdoor,
                     insert_indoor, insert_barometric, insert_network, skipped_inserts,
                     errors)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    timestamp,
                    metrics["api_success"],
                    metrics["db_success"],
                    metrics["insert_outdoor"],
                    metrics["insert_indoor"],
                    metrics["insert_barometric"],
                    metrics["insert_network"],
                    metrics["skipped_inserts"],
                    metrics["errors"]
                ))
            conn.commit()
    except Exception as e2:
        logging.error(f"Failed to write to system_health table: {e2}")
