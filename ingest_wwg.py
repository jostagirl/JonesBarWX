import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

# Import shared helper functions from ingest_common
from ingest_common import (
    get_db_connection,
    sync_table_schema,
    insert_if_changed,
    log_system_health,
    get_maintenance_mode,
    logger
)

# Load environment variables from .env
load_dotenv()

# --- API Configuration ---
WWG_API_KEY = os.getenv("WWG_API_KEY")
WWG_API_SECRET = os.getenv("WWG_API_SECRET")

# Use the actual station name for your API endpoint
WWG_STATION_ID = "PGE-2116"

# Base API URL pointing to Western Weather Group's v2 endpoint
WWG_BASE_URL = f"https://api.westernwx.com/v2/stationdata/10/{WWG_STATION_ID}/latest?utc=true"


def fetch_wwg_data():
    """Fetch raw station observations from the Western Weather Group API."""
    headers = {
        "Accept": "application/json",
	"X-Api-Key": WWG_API_KEY
    }
    
    response = requests.get(WWG_BASE_URL, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()

def parse_wwg_payload(data: dict) -> dict:
    """Parses nested WWG v2 payload into flat dictionary for MariaDB."""
    if not data or "values" not in data:
        logging.error("Invalid or empty payload received from WWG API.")
        return {}

    # Extract nested observations dictionary
    vals = data.get("values", {})

    # Strip or replace ISO chars from date
    raw_date = data.get("date")
    clean_timestamp = raw_date.replace("T", " ").replace("Z", "") if raw_date else None

    record = {
        "timestamp_utc": clean_timestamp,
        "station_id": data.get("stationId"),
        "latitude": data.get("lat"),
        "longitude": data.get("lon"),
        "interval_min": data.get("interval"),
        
        # Weather Measurements
        "temp_out": vals.get("Temp"),
        "temp_max_day": vals.get("TempMaxDay"),
        "temp_min_day": vals.get("TempMinDay"),
        "dew_point": vals.get("DewPoint"),
        "hum_out": vals.get("RH"),
        "wind_speed": vals.get("WindSpeed"),
        "wind_dir": vals.get("WindDir"),
        "wind_max": vals.get("WindMax"),
        "wind_max_dir": vals.get("WindMaxDir"),
        "wind_max_day": vals.get("WindMaxDay"),
        "wind_max_day_dir": vals.get("WindMaxDayDir"),
        "wind_max_day_time": vals.get("WindMaxDayTime"),
        "battery_volts": vals.get("BatVolt"),
        
        "maintenance_flag": 0
    }

    # Filter out None values so dynamic schema sync only handles present keys
    return {k: v for k, v in record.items() if v is not None}

def main():
    api_success = 0
    db_success = 0
    
    # Skip execution if maintenance mode is active
    if get_maintenance_mode():
        logger.info("Maintenance mode enabled. Skipping WWG ingestion.")
        return

    try:
        # 1. Fetch API Data
        logger.info(f"Fetching WWG data for station: {WWG_STATION_ID}")
        raw_data = fetch_wwg_data()
        api_success = 1
        
        # 2. Parse Data
        station_data = parse_wwg_payload(raw_data)
        
        # 3. Write to Database
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Ensure database table schema matches payload keys
                sync_table_schema(cursor, "wwg_stations", station_data)
                
                # Insert data record
                insert_if_changed(cursor, "wwg_stations", station_data)
                conn.commit()
                db_success = 1
                logger.info(f"Successfully recorded WWG data for {WWG_STATION_ID}")
        finally:
            conn.close()

    except requests.RequestException as req_err:
        logger.error(f"WWG API connection error: {req_err}")
    except Exception as err:
        logger.error(f"Unexpected error during WWG ingestion: {err}")
    finally:
        # 4. Always record system health under WWG_STATION_ID
        log_system_health(WWG_STATION_ID, api_success, db_success)


if __name__ == "__main__":
    main()
