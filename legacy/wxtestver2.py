import pymysql
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv
import os

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

LOG_PATH = r'C:\Users\Anna\Projects\WeatherLogger\logs\weather_log.txt'

logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# .env test
print("DB_HOST:", os.getenv("DB_HOST"))
print("API_KEY:", os.getenv("API_KEY"))
print("STATION_ID:", os.getenv("STATION_ID"))
print("Request URL:", API_URL)
print("Headers:", headers)

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
        logging.info(f"✅ Inserted new data into {table} at {timestamp}")
    else:
        logging.info(f"ℹ️ No change in {table} at {timestamp} — skipping insert.")

try:
    response = requests.get(API_URL, headers=headers)
    response.raise_for_status()
    api_data = response.json()
    sensors = api_data.get('sensors', [])
    
    # Get data by sensor type
    outdoor = get_sensor_data(sensors, 43)
    indoor = get_sensor_data(sensors, 243)
    baro = get_sensor_data(sensors, 242)
    network = get_sensor_data(sensors, 504)

    with pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME) as connection:
        with connection.cursor() as cursor:
            if outdoor:
                insert_if_changed(cursor, 'outdoor_conditions', datetime.utcfromtimestamp(outdoor['ts']), outdoor)
            if indoor:
                insert_if_changed(cursor, 'indoor_conditions', datetime.utcfromtimestamp(indoor['ts']), indoor)
            if baro:
                insert_if_changed(cursor, 'barometric_conditions', datetime.utcfromtimestamp(baro['ts']), baro)
            if network:
                insert_if_changed(cursor, 'network_status', datetime.utcfromtimestamp(network['ts']), network)

        connection.commit()

except Exception as e:
    logging.error(f"❌ Error: {e}")
