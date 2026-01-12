##PI Migration Branch##

WeatherLogger Windows → Raspberry Pi Migration (Action Summary)

- Reimaged the Raspberry Pi with a clean Raspberry Pi OS install

- Established reliable SSH access to the Pi

- Created a dedicated Git branch (pi-migration) to isolate Pi/Linux work from the Windows baseline

- Installed and started MariaDB on the Raspberry Pi

- Secured MariaDB with local-only access and application-level credentials

- Created the application database (weather_data) on the Pi

- Generated a logical dump of the existing MySQL database on Windows

- Transferred the database dump file to the Raspberry Pi

- Imported historical weather data into MariaDB on the Pi

- Verified database tables, row counts, and timestamp integrity after import

- Cloned the GitHub repository onto the Raspberry Pi

- Switched the Pi working copy to the pi-migration branch

- Created a Python virtual environment on the Pi for application isolation

- Activated and verified the virtual environment

- Began installing Python application dependencies inside the virtual environment

### Additional Actions (Post-install failure & recovery)

Observed stalled / failed Python dependency installation during pip install -r requirements.txt

Rebooted the Raspberry Pi to clear package install state and reassess system health

Determined the Pi was in an unknown state: unreachable via SSH, not visible on the network, and showing ambiguous behavior on HDMI

Connected the Pi to a monitor to inspect boot state and confirmed it was running a full desktop GUI OS, which was heavier than required for a headless appliance

Decided to reimage the Pi again to a minimal OS after confirming no irreplaceable state existed on the device

Saved a copy of the existing config.txt (HDMI / diagnostic settings) prior to reflashing for reference and recovery knowledge (ultimately not reused)

Reimaged the Raspberry Pi with Raspberry Pi OS Lite (32-bit, Bookworm) to eliminate GUI overhead and ensure predictable headless behavior

Enabled SSH and Wi-Fi during imaging to allow immediate remote access after first boot

Confirmed successful boot and network connectivity by locating the Pi in the router and connecting via SSH using both hostname and IP

Verified kernel console configuration and login services (tty1, getty) were correctly enabled on the Lite OS

Identified HDMI output as a good troubleshooting tool, neededto do some stuff to enable it onlite OS:

Identified kernel mode-setting (KMS) graphics overlays as the cause of missing HDMI output on the Pi Zero

Disabled KMS overlays to restore reliable HDMI text console output without installing a GUI

Enabled HDMI text console output as a diagnostic fallback on an otherwise headless system

Verified the Pi displays a local text login prompt on HDMI while remaining SSH-first for normal operation

Reinstalled MariaDB on the fresh Raspberry Pi OS Lite system after reimage

Recreated the application database (weather_data) and application database user on the Pi

Re-transferred the historical database dump to the Pi after reimage

Resolved MySQL → MariaDB collation incompatibility and successfully imported historical data

Verified restored data integrity by checking table counts and latest timestamps

Removed temporary database dump files from the Pi after successful import

Re-cloned the GitHub repository onto the Pi after reimage and switched to the pi-migration branch

Recreated the Python virtual environment on the Pi after OS rebuild

Installed required system-level build dependencies (compiler toolchain, SSL, ffi, Python headers) needed for Python packages on ARM

Successfully installed all Python application dependencies inside the virtual environment, including cryptography and Flask stack

Verified .env configuration loading correctly on the Pi

Verified database connectivity from Python within the virtual environment

Updated application logging paths to be Linux-safe and relative to the repository directory

Successfully executed the ingestion script manually on the Pi and confirmed new data writes

Verified correct UTC-based timestamp handling and system time synchronization (NTP active, local timezone set)

Configured secure MySQL Workbench access from Windows to the Pi using an SSH tunnel (no exposed database ports)

Verified live database writes and historical data visibility via MySQL Workbench GUI

Installed tmux on the Pi to support persistent interactive sessions during setup and troubleshooting

Configured a cron job to execute the ingestion script every 5 minutes using the virtual environment Python interpreter

Verified unattended, automated ingestion is running correctly via database health records and timestamps

Achieved a stable, headless Raspberry Pi deployment performing automated weather data ingestion with secure remote observability and recovery paths

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
