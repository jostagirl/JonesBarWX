import pymysql
import requests
import logging
from datetime import datetime

# === API CONFIG ===
API_KEY = 'xfw2kddy2p6lo7thideyoq12lxqov5om'
API_SECRET = 'ia1ieetrht76zpzbmzvfva0dzqgsm3cg'
STATION_ID = '5b32a69b-88e9-4867-8067-2f4bb11c145d'
url = f'https://api.weatherlink.com/v2/current/{STATION_ID}?api-key={API_KEY}'
headers = {'X-Api-Secret': API_SECRET}

# === MYSQL CONFIG ===
DB_HOST = 'localhost'
DB_USER = 'weather_user'
DB_PASS = 'wx'
DB_NAME = 'weather_data'

# === LOGGING SETUP ===
logging.basicConfig(
    filename=r'C:\Users\Anna\Projects\WeatherLogger\logs\weather_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

try:
    # === FETCH WEATHER DATA ===
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    sensor = next((s for s in data['sensors'] if s['sensor_type'] == 43), None)
    if not sensor:
        raise ValueError("Sensor type 43 (outdoor) not found in API response.")

    d = sensor['data'][0]

    # Print all available key-value pairs (for debugging/inspection)
    for key, value in d.items():
        print(f"{key}: {value}")

    # Prepare a basic set of values (customize as needed)
    values = (
        datetime.utcfromtimestamp(d['ts']),
        d.get('temp'),
        d.get('hum'),
        d.get('dew_point'),
        d.get('wind_speed_last'),
        d.get('wind_dir_last'),
        d.get('solar_rad'),
        d.get('uv_index')
    )

    # === INSERT INTO MYSQL ===
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

    with connection.cursor() as cursor:
        query = """
        INSERT INTO current_conditions
        (timestamp_utc, temperature, humidity, dew_point, wind_speed, wind_direction, solar_radiation, uv_index)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, values)
        connection.commit()

    logging.info(f"✅ Weather data logged at {values[0]}")

except Exception as e:
    logging.error(f"❌ Error: {e}")

finally:
    if 'connection' in locals():
        connection.close()
