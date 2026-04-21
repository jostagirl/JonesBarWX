import os
import pymysql
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
local_tz = ZoneInfo(os.getenv("LOCAL_TIMEZONE", "America/Los_Angeles"))
# === Database Configuration ===

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

# === Time Range: last 12 hours ===
now_local = datetime.now(local_tz)
now_utc = now_local.astimezone(timezone.utc)
past_12h_utc = now_utc - timedelta(hours=12)

# === Connect to MySQL ===
connection = pymysql.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASS,
    database=DB_NAME
)

try:
    with connection.cursor() as cursor:
        # === OUTDOOR DATA ===
        cursor.execute("""
            SELECT timestamp_utc, temp, hum, dew_point
            FROM outdoor_conditions
            WHERE timestamp_utc >= %s
            ORDER BY timestamp_utc
        """, (past_12h_utc,))
        outdoor_rows = cursor.fetchall()

        ot_times = [row[0] for row in outdoor_rows]
        ot_temp = [row[1] for row in outdoor_rows]
        ot_hum = [row[2] for row in outdoor_rows]
        ot_dew = [row[3] for row in outdoor_rows]

        # === INDOOR DATA ===
        cursor.execute("""
            SELECT timestamp_utc, temp_in, hum_in, dew_point_in
            FROM indoor_conditions
            WHERE timestamp_utc >= %s
            ORDER BY timestamp_utc
        """, (past_12h_utc,))
        indoor_rows = cursor.fetchall()

        it_times = [row[0] for row in indoor_rows]
        it_temp = [row[1] for row in indoor_rows]
        it_hum = [row[2] for row in indoor_rows]
        it_dew = [row[3] for row in indoor_rows]
        
        # === BAROMETRIC DATA ===
        cursor.execute("""
            SELECT timestamp_utc, bar_absolute
            FROM barometric_conditions
            WHERE timestamp_utc >= %s
            ORDER BY timestamp_utc
        """, (past_12h_utc,))
        barometric_rows = cursor.fetchall()

        bp_times = [row[0] for row in barometric_rows]
        bp_abs = [row[1] for row in barometric_rows]

finally:
    connection.close()

# Convert timestamps to local time
ot_times = [row[0].replace(tzinfo=timezone.utc).astimezone(local_tz) for row in outdoor_rows]
it_times = [row[0].replace(tzinfo=timezone.utc).astimezone(local_tz) for row in indoor_rows]
bp_times = [t.replace(tzinfo=timezone.utc).astimezone(local_tz) for t in bp_times]

# TEST FOR TIME CONVERSION
print("Local Now:", now_local)
print("UTC Now:", now_utc)
print("Querying for data since (UTC):", past_12h_utc)
# === PLOT ===
fig, ax1 = plt.subplots(figsize=(14, 6))

# === Temperature & Dew Point on Left Axis ===
# ax1.set_xlabel("Time (UTC)")
ax1.set_xlabel(f"Time ({local_tz.key})")
ax1.set_ylabel("Temperature / Dew Point (°F)", color='black')
if ot_times:
    ax1.plot(ot_times, ot_temp, label="Outdoor Temp (°F)", color="tab:blue")
    ax1.plot(ot_times, ot_dew, label="Outdoor Dew Point (°F)", color="tab:cyan")
if it_times:
    ax1.plot(it_times, it_temp, label="Indoor Temp (°F)", color="tab:orange")
    ax1.plot(it_times, it_dew, label="Indoor Dew Point (°F)", color="tab:green")
ax1.tick_params(axis='y', labelcolor='black')
   

# === Humidity and BP on Right Axis ===
ax2 = ax1.twinx()
ax2.set_ylabel("Humidity (%)", color='black')
if ot_times:
    ax2.plot(ot_times, ot_hum, label="Outdoor Humidity (%)", linestyle='--', color="tab:purple")
if it_times:
    ax2.plot(it_times, it_hum, label="Indoor Humidity (%)", linestyle='--', color="tab:red")
ax2.tick_params(axis='y', labelcolor='black')
if bp_times:
    ax2.plot(bp_times, bp_abs, label="Barometric Pressure (hPa)", linestyle='-.', color="tab:gray")
ax2.set_ylabel("Humidity (%) / Pressure (hPa)", color='black')

# === Legends ===
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
plt.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

# === Formatting ===
plt.title("Indoor & Outdoor Conditions (Last 12 Hours)")
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
