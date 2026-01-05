##PI Migration Branch##

### WeatherLogger

A Python-based system that collects, stores, and visualizes weather data from my personal Davis WeatherLink station.
Designed for reliability, schema auto-expansion, secure credential handling, and easy long-term operation on Windows.

### 🚀 Overview

WeatherLogger connects to my WeatherLink station API, downloads the latest sensor data, and inserts new observations into a MySQL database only when something changes, minimizing storage and noise.

The system also:

Automatically expands SQL table schemas when new fields appear.

Generates local 12-hour weather plots.

Uses structured logging for safe unattended operation.

Loads API keys and database credentials from a secure .env file.

---

### 📂 Project Structure

<pre>
WeatherLogger/
├── data/                     # (optional future use, used for testing)
├── logs/
│   └── weather_log.txt       # runtime logs
├── legacy/
│   └── old__run_weather_logger.bat
├── .env                      # secrets (NOT committed)
├── config.py                 # unused (optional constants)
├── requirements.txt
├── run_weather_logger.bat    # Windows scheduler entry point
├── wxtest.py                 # main ingestion script
├── wxplot.py                 # graphing script
└── wxtestver*.py             # older test versions
</pre>
---

### ⚙️ Installation & Setup
1. Install Python packages

```bash
pip install -r requirements.txt
```

2. Create your .env file

(Do not commit this to GitHub)
```env
DB_HOST=localhost
DB_USER=weather_user
DB_PASS=your_password
DB_NAME=weather_data

API_KEY=your_weatherlink_key
API_SECRET=your_weatherlink_secret
STATION_ID=your_station_id

LOCAL_TIMEZONE=America/Los_Angeles
```

3. MySQL Database Setup

Create a schema:
```SQL
CREATE DATABASE weather_data;

```
You do not need to create tables manually —
WeatherLogger automatically adds columns as needed using:
```SQL
SHOW COLUMNS

ALTER TABLE <table> ADD COLUMN ...
```
This allows the system to adapt when new sensors or firmware fields appear.

### ▶️ Running the Logger
Manual Run
```bash
python wxtest.py
```
Scheduled Run (Windows Task Scheduler - <b>"WeatherLogger"</b>)

Configure a New task on a schedule to run every 5 minutes for continuous ingestion.
**Action:** Start a Program

**Program/Script:** 
```
C:\Python311\python.exe
```
**Add args:**
```
C:\Users\Anna\Projects\WeatherLogger\wxtest.py
```
**Start in:**
```
C:\Users\Anna\Projects\WeatherLogger
```

### 📝 Logging

All operations and errors are written to:
```text
logs/weather_log.txt
```

Includes timestamps, inserts, schema changes, and error stacks.

### 📊 Plotting Weather Data

Run:
```bash
python wxplot.py
```

Generates 12-hour charts for:

Temperature

Dew point

Humidity

Barometric pressure

All timestamps convert automatically to the configured LOCAL_TIMEZONE.

#### SAMPLE PLOT:
<img width="1390" height="593" alt="image" src="https://github.com/user-attachments/assets/c45bdc76-2e58-4c02-889d-f22f49d25505" />

### 🧠 How the Ingestion Works

WeatherLink's JSON payload contains sensor blocks.
The script maps them like this:
```python
outdoor = get_sensor_data(sensors, 43)
indoor = get_sensor_data(sensors, 243)
baro = get_sensor_data(sensors, 242)
network = get_sensor_data(sensors, 504)
```

This design makes adding new sensor types trivial.

Data is inserted only if changed:

- Fetch the latest row from the table
- Compare against the new values
- Insert only if different

This reduces clutter and improves database performance.

---

### 🔧 Technical Highlights

- **Dynamic schema expansion** – Auto-adds missing columns in MySQL tables
- **Change detection** – Prevents duplicate inserts
- **Secure credentials** – `.env` + `python-dotenv`
- **Structured logging** – Helpful for long-term unattended operation
- **Timezone normalization** – Charts use the local timezone
- **Extensible architecture** – Easily add new sensors or datasets

---

### 🧭 Future Enhancements (Roadmap)

- Dockerized deployment (database + collector)
- Grafana dashboard for live visualization
- MQTT/WebSocket feed for smart home integrations
- Alerting for sensor disconnects or abnormal readings

---

### 📄 License

This project is for personal and professional demonstration purposes only.
