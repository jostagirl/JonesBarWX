# JonesBarWX — Full Rebuild Guide

Use this document to reconstruct the entire project from a fresh Raspberry Pi OS install. Follow the sections in order.

**Reference documents:**
- `README.md` — operational reference (architecture, troubleshooting)
- `SERVICES.md` — full contents of all systemd unit files and scripts

---

## 1. Hardware & OS

**Hardware:** Raspberry Pi 4, hostname `rapi4`

**OS:** Raspberry Pi OS Lite 64-bit (Debian 13 / Bookworm), headless

**Image with Raspberry Pi Imager:**
- Set hostname: `rapi4`
- Enable SSH (password or key-based)
- Configure Wi-Fi SSID and password
- Set locale/timezone: `America/Los_Angeles`

**After first boot, verify:**
```bash
ssh pi4@rapi4
hostname        # should print: rapi4
uname -m        # should print: aarch64
timedatectl     # confirm timezone and NTP active
```

---

## 2. System Packages

```bash
sudo apt update && sudo apt upgrade -y

# Build tools needed for Python cryptography package on ARM
sudo apt install -y \
    git curl wget \
    python3-pip python3-venv \
    build-essential libssl-dev libffi-dev python3-dev \
    mariadb-server \
    tmux
```

---

## 3. GitHub SSH Key

The Pi uses SSH key auth to push to GitHub. Generate a new key and add it to your GitHub account.

```bash
ssh-keygen -t ed25519 -C "rapi4-jonesbar" -f ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub
```

Copy the output. In GitHub → Settings → SSH and GPG keys → New SSH key → paste it.

**Test auth:**
```bash
ssh -T git@github.com
# Expected: Hi jostagirl! You've successfully authenticated...
```

---

## 4. Clone Repositories

**Main project repo** (private, on `pi-migration` branch):
```bash
mkdir -p /home/pi4/repo
cd /home/pi4/repo
git clone git@github.com:jostagirl/JonesBarWX.git
cd JonesBarWX
git checkout pi-migration
```

**Public data repo** (pushed to GitHub Pages):
```bash
mkdir -p /home/pi4/repo_public
cd /home/pi4/repo_public
git clone git@github.com:jostagirl/PublicJonesBarWX_API.git
```

---

## 5. Python Environments

Two separate virtual environments — one for the ingest script, one for the FastAPI service.

**Ingest venv** (at repo root):
```bash
cd /home/pi4/repo/JonesBarWX
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install requests pymysql cryptography python-dotenv
```

**FastAPI service venv:**
```bash
cd /home/pi4/repo/JonesBarWX/services/jonesbar_api
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install \
    fastapi==0.129.0 \
    uvicorn==0.41.0 \
    pymysql==1.1.2 \
    python-dotenv==1.2.1 \
    pydantic==2.12.5 \
    starlette==0.52.1 \
    anyio==4.12.1
```

---

## 6. MariaDB Setup

### Install and secure

```bash
sudo systemctl enable --now mariadb
sudo mysql_secure_installation
# Answer: set root password, remove anonymous users, disallow remote root, remove test DB
```

### Create database and users

```bash
sudo mysql
```

```sql
-- Application database
CREATE DATABASE weather_data
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

-- Application user (read/write for ingest and API)
CREATE USER 'weather_user'@'localhost' IDENTIFIED BY 'YOUR_WEATHER_USER_PASSWORD';
GRANT ALL PRIVILEGES ON weather_data.* TO 'weather_user'@'localhost';

-- Read-only user for Grafana Alloy metrics agent
CREATE USER 'alloy_reader'@'localhost' IDENTIFIED BY 'YOUR_ALLOY_READER_PASSWORD';
GRANT SELECT ON weather_data.* TO 'alloy_reader'@'localhost';

FLUSH PRIVILEGES;
EXIT;
```

### Create tables

```bash
sudo mysql weather_data
```

```sql
CREATE TABLE outdoor_conditions (
  id int(11) NOT NULL AUTO_INCREMENT,
  timestamp_utc datetime NOT NULL,
  dew_point float DEFAULT NULL,
  heat_index float DEFAULT NULL,
  hum float DEFAULT NULL,
  rain_rate_hi_clicks int(11) DEFAULT NULL,
  rain_rate_hi_in float DEFAULT NULL,
  rain_rate_last_in float DEFAULT NULL,
  rain_storm_last_in float DEFAULT NULL,
  rainfall_daily_in float DEFAULT NULL,
  rainfall_monthly_in float DEFAULT NULL,
  rainfall_year_in float DEFAULT NULL,
  solar_rad float DEFAULT NULL,
  temp float DEFAULT NULL,
  thsw_index float DEFAULT NULL,
  thw_index float DEFAULT NULL,
  uv_index float DEFAULT NULL,
  wet_bulb float DEFAULT NULL,
  wind_chill float DEFAULT NULL,
  wind_dir_last int(11) DEFAULT NULL,
  wind_dir_scalar_avg_last_10_min int(11) DEFAULT NULL,
  wind_speed_avg_last_10_min float DEFAULT NULL,
  wind_speed_hi_last_10_min float DEFAULT NULL,
  wind_speed_last float DEFAULT NULL,
  rx_state int(11) DEFAULT NULL,
  wind_speed_hi_last_2_min int(11) DEFAULT NULL,
  wind_dir_at_hi_speed_last_10_min int(11) DEFAULT NULL,
  rain_rate_hi_last_15_min_clicks int(11) DEFAULT NULL,
  rain_size int(11) DEFAULT NULL,
  tz_offset int(11) DEFAULT NULL,
  rainfall_last_60_min_clicks int(11) DEFAULT NULL,
  rainfall_monthly_clicks int(11) DEFAULT NULL,
  wind_dir_at_hi_speed_last_2_min int(11) DEFAULT NULL,
  rainfall_daily_mm int(11) DEFAULT NULL,
  rain_storm_last_clicks int(11) DEFAULT NULL,
  tx_id int(11) DEFAULT NULL,
  rain_storm_last_start_at int(11) DEFAULT NULL,
  rainfall_last_15_min_in int(11) DEFAULT NULL,
  rainfall_daily_clicks int(11) DEFAULT NULL,
  rainfall_last_15_min_mm int(11) DEFAULT NULL,
  rain_storm_clicks int(11) DEFAULT NULL,
  rain_rate_hi_mm int(11) DEFAULT NULL,
  rainfall_year_clicks int(11) DEFAULT NULL,
  rain_storm_in int(11) DEFAULT NULL,
  rain_storm_last_end_at int(11) DEFAULT NULL,
  rain_storm_mm int(11) DEFAULT NULL,
  wind_dir_scalar_avg_last_2_min int(11) DEFAULT NULL,
  rainfall_last_24_hr_in int(11) DEFAULT NULL,
  rainfall_last_60_min_mm int(11) DEFAULT NULL,
  trans_battery_flag int(11) DEFAULT NULL,
  rainfall_last_60_min_in int(11) DEFAULT NULL,
  rain_storm_start_time text DEFAULT NULL,
  rainfall_last_24_hr_mm int(11) DEFAULT NULL,
  rainfall_last_15_min_clicks int(11) DEFAULT NULL,
  rainfall_year_mm float DEFAULT NULL,
  wind_dir_scalar_avg_last_1_min int(11) DEFAULT NULL,
  wind_speed_avg_last_2_min float DEFAULT NULL,
  rainfall_monthly_mm int(11) DEFAULT NULL,
  rain_storm_last_mm float DEFAULT NULL,
  wind_speed_avg_last_1_min float DEFAULT NULL,
  rain_rate_last_mm int(11) DEFAULT NULL,
  rain_rate_last_clicks int(11) DEFAULT NULL,
  rainfall_last_24_hr_clicks int(11) DEFAULT NULL,
  rain_rate_hi_last_15_min_mm int(11) DEFAULT NULL,
  rain_rate_hi_last_15_min_in int(11) DEFAULT NULL,
  ts int(11) DEFAULT NULL,
  is_maintenance int(11) DEFAULT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE indoor_conditions (
  id int(11) NOT NULL AUTO_INCREMENT,
  timestamp_utc datetime NOT NULL,
  temp_in float DEFAULT NULL,
  hum_in float DEFAULT NULL,
  dew_point_in float DEFAULT NULL,
  heat_index_in float DEFAULT NULL,
  tz_offset int(11) DEFAULT NULL,
  ts int(11) DEFAULT NULL,
  is_maintenance int(11) DEFAULT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE barometric_conditions (
  id int(11) NOT NULL AUTO_INCREMENT,
  timestamp_utc datetime NOT NULL,
  bar_sea_level float DEFAULT NULL,
  bar_absolute float DEFAULT NULL,
  bar_offset float DEFAULT NULL,
  bar_trend float DEFAULT NULL,
  tz_offset int(11) DEFAULT NULL,
  ts int(11) DEFAULT NULL,
  is_maintenance int(11) DEFAULT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE network_status (
  id int(11) NOT NULL AUTO_INCREMENT,
  timestamp_utc datetime NOT NULL,
  battery_voltage int(11) DEFAULT NULL,
  wifi_rssi int(11) DEFAULT NULL,
  input_voltage int(11) DEFAULT NULL,
  rx_bytes bigint(20) DEFAULT NULL,
  tx_bytes bigint(20) DEFAULT NULL,
  ip_v4_address varchar(45) DEFAULT NULL,
  ip_v4_netmask varchar(45) DEFAULT NULL,
  ip_v4_gateway varchar(45) DEFAULT NULL,
  uptime bigint(20) DEFAULT NULL,
  link_uptime bigint(20) DEFAULT NULL,
  firmware_version bigint(20) DEFAULT NULL,
  bootloader_version bigint(20) DEFAULT NULL,
  health_version int(11) DEFAULT NULL,
  radio_version bigint(20) DEFAULT NULL,
  network_error text DEFAULT NULL,
  bluetooth_version text DEFAULT NULL,
  bgn text DEFAULT NULL,
  tz_offset int(11) DEFAULT NULL,
  local_api_queries int(11) DEFAULT NULL,
  ip_address_type int(11) DEFAULT NULL,
  rapid_records_sent int(11) DEFAULT NULL,
  touchpad_wakeups int(11) DEFAULT NULL,
  espressif_version int(11) DEFAULT NULL,
  dns_type_used text DEFAULT NULL,
  network_type int(11) DEFAULT NULL,
  ts int(11) DEFAULT NULL,
  is_maintenance int(11) DEFAULT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE system_health (
  id int(11) NOT NULL AUTO_INCREMENT,
  timestamp_utc datetime NOT NULL,
  api_success tinyint(1) NOT NULL,
  db_success tinyint(1) NOT NULL,
  insert_outdoor tinyint(1) NOT NULL,
  insert_indoor tinyint(1) NOT NULL,
  insert_barometric tinyint(1) NOT NULL,
  insert_network tinyint(1) NOT NULL,
  skipped_inserts int(11) NOT NULL,
  is_maintenance tinyint(1) DEFAULT 0,
  errors varchar(255) DEFAULT NULL,
  error_code int(11) DEFAULT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE station_state (
  station_id varchar(50) NOT NULL,
  maintenance_mode int(11) DEFAULT 0,
  PRIMARY KEY (station_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

-- Seed the default station row
INSERT INTO station_state (station_id, maintenance_mode) VALUES ('default', 0);


CREATE TABLE current_conditions (
  id int(11) NOT NULL AUTO_INCREMENT,
  timestamp_utc datetime DEFAULT NULL,
  temperature float DEFAULT NULL,
  humidity float DEFAULT NULL,
  dew_point float DEFAULT NULL,
  wind_speed float DEFAULT NULL,
  wind_direction int(11) DEFAULT NULL,
  solar_radiation float DEFAULT NULL,
  uv_index float DEFAULT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

EXIT;
```

### Restore historical data (if migrating, not a fresh start)

```bash
# On the source machine, dump the database:
mysqldump -u root -p weather_data > weather_data_dump.sql

# Transfer to Pi:
scp weather_data_dump.sql pi4@rapi4:/home/pi4/

# Import on Pi:
sudo mysql weather_data < /home/pi4/weather_data_dump.sql

# Verify row counts:
sudo mysql weather_data -e "SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema='weather_data';"

# Clean up dump file:
rm /home/pi4/weather_data_dump.sql
```

---

## 7. Application .env Files

These are never committed to the repository. Create them manually.

**`/home/pi4/repo/JonesBarWX/.env`** (ingest script credentials):
```env
DB_HOST=localhost
DB_USER=weather_user
DB_PASS=YOUR_WEATHER_USER_PASSWORD
DB_NAME=weather_data

API_KEY=your_davis_weatherlink_api_key
API_SECRET=your_davis_weatherlink_api_secret
STATION_ID=your_davis_station_id

LOCAL_TIMEZONE=America/Los_Angeles
```

**`/home/pi4/repo/JonesBarWX/services/jonesbar_api/.env`** (FastAPI service credentials):
```env
DB_HOST=127.0.0.1
DB_USER=weather_user
DB_PASS=YOUR_WEATHER_USER_PASSWORD
DB_NAME=weather_data
```

---

## 8. /etc/jonesbar/ Config Directory

This directory holds all runtime config that is outside the repository (credentials, URLs).

```bash
sudo mkdir -p /etc/jonesbar
```

**`/etc/jonesbar/heartbeats.env`** — Healthchecks.io ping URLs (see Section 11 to get these):
```bash
sudo tee /etc/jonesbar/heartbeats.env > /dev/null <<'EOF'
PI_ALIVE_URL=https://hc-ping.com/YOUR-PI-ALIVE-UUID
INGEST_OK_URL=https://hc-ping.com/YOUR-INGEST-OK-UUID
PUBLISH_OK_URL=https://hc-ping.com/YOUR-PUBLISH-OK-UUID
EOF
sudo chmod 600 /etc/jonesbar/heartbeats.env
```

**`/etc/jonesbar/notify.env`** — push notification webhook (configure to activate failure alerts):
```bash
sudo tee /etc/jonesbar/notify.env > /dev/null <<'EOF'
# Set NOTIFY_URL to activate push alerts on service failure.
# Works with ntfy.sh (https://ntfy.sh/your-topic), Pushover, Discord webhooks, etc.
NOTIFY_URL=
EOF
sudo chmod 600 /etc/jonesbar/notify.env
```

**`/etc/jonesbar/alloy.env`** — Grafana Alloy DB reader credentials:
```bash
sudo tee /etc/jonesbar/alloy.env > /dev/null <<'EOF'
ALLOY_DB_USER=alloy_reader
ALLOY_DB_PASS=YOUR_ALLOY_READER_PASSWORD
ALLOY_DB_HOST=127.0.0.1
ALLOY_DB_NAME=weather_data
EOF
sudo chmod 600 /etc/jonesbar/alloy.env
```

---

## 9. Notification Script

```bash
sudo tee /usr/local/bin/jonesbar-notify > /dev/null <<'EOF'
#!/bin/bash
# Fires on systemd unit failure via OnFailure=notify@%n.service.
# Always exits 0 so a broken notify path cannot cause an alert loop.

UNIT="$1"
[ -z "$UNIT" ] && exit 0

[ -r /etc/jonesbar/notify.env ] && . /etc/jonesbar/notify.env

if [ -z "${NOTIFY_URL:-}" ]; then
    logger -t jonesbar-notify "NOTIFY_URL unset; skipping alert for $UNIT"
    exit 0
fi

HOST=$(hostname)
TS=$(date -Is)
JOURNAL=$(journalctl -u "$UNIT" -n 20 --no-pager 2>/dev/null)

MESSAGE="[${HOST}] ${TS}
FAILED: ${UNIT}

${JOURNAL}"

curl -fsS --max-time 10 -d "$MESSAGE" "$NOTIFY_URL" > /dev/null 2>&1 \
    || logger -t jonesbar-notify "POST to notify endpoint failed for $UNIT"

exit 0
EOF
sudo chmod 755 /usr/local/bin/jonesbar-notify
```

---

## 10. systemd Units

Install all unit files from `SERVICES.md`, then enable them:

```bash
sudo systemctl daemon-reload

sudo systemctl enable --now jonesbar-api.service
sudo systemctl enable --now jonesbar-ingest.timer
sudo systemctl enable --now jonesbar-publish-outdoor.timer
sudo systemctl enable --now pi-alive.timer

# Verify all active:
systemctl is-active jonesbar-api.service jonesbar-ingest.timer jonesbar-publish-outdoor.timer pi-alive.timer
```

---

## 11. Healthchecks.io

Create a free account at **healthchecks.io**.

Create three monitors with these settings:

| Name | Period | Grace |
|---|---|---|
| `jonesbar-pi-alive` | 1 minute | 5 minutes |
| `jonesbar-ingest-ok` | 15 minutes | 30 minutes |
| `jonesbar-publish-ok` | 15 minutes | 30 minutes |

For each monitor, copy its **Ping URL** (`https://hc-ping.com/<uuid>`) into `/etc/jonesbar/heartbeats.env`.

Add at least one **notification channel** (email is auto-configured; SMS and push apps are available in Integrations).

**Test that pings reach Healthchecks:**
```bash
sudo bash -c 'source /etc/jonesbar/heartbeats.env && curl -fsS "$PI_ALIVE_URL" && echo OK'
```

---

## 12. Grafana Alloy (Metrics Agent)

Alloy runs as a systemd service and ships metrics to Grafana Cloud every 60 seconds.

### Install Alloy

The easiest path is the Grafana Cloud setup wizard, which installs Alloy and pre-configures your credentials automatically:

1. Log in to **grafana.com** → your org → Cloud Portal
2. Go to **Connections** → **Add new connection** → search **"Linux node"** or **"Alloy"**
3. Follow the wizard — it provides a shell script that installs Alloy, registers it with your Grafana Cloud stack, and writes `/etc/alloy/config.alloy` and the API key drop-in

**Manual install (if not using the wizard):**
```bash
sudo apt install -y apt-transport-https software-properties-common
wget -q -O - https://apt.grafana.com/gpg.key | sudo apt-key add -
echo "deb https://apt.grafana.com stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt update && sudo apt install alloy
```

### Wire the API key

The API key is stored in a systemd drop-in. Create one if the wizard didn't:

```bash
sudo mkdir -p /etc/systemd/system/alloy.service.d
sudo tee /etc/systemd/system/alloy.service.d/env.conf > /dev/null <<'EOF'
[Service]
Environment=GCLOUD_RW_API_KEY=YOUR_GRAFANA_CLOUD_API_KEY
EOF
sudo systemctl daemon-reload
```

To get a new API key: Grafana Cloud Portal → your stack → **API Keys** (or **Access Policies**) → create key with `metrics:write` scope.

### Append the jonesbar scrape block to the Alloy config

After the wizard creates `/etc/alloy/config.alloy`, append this block:

```bash
sudo tee -a /etc/alloy/config.alloy > /dev/null <<'EOF'

// ── Jones Bar WX custom metrics ──────────────────────────────────────────────
prometheus.scrape "jonesbar" {
  targets = [{__address__ = "localhost:8000"}]
  metrics_path    = "/metrics"
  scrape_interval = "60s"
  forward_to      = [prometheus.remote_write.metrics_service.receiver]
}
EOF
```

**Note:** The block references `prometheus.remote_write.metrics_service` — this name must match what the wizard generated. Check `/etc/alloy/config.alloy` and adjust if the name differs.

```bash
sudo systemctl restart alloy
systemctl status alloy
```

### Verify metrics are flowing

```bash
# Check the local /metrics endpoint:
curl http://localhost:8000/metrics

# Check Alloy logs for scrape errors:
journalctl -u alloy -n 20

# In Grafana Cloud: Explore → Prometheus datasource → query jonesbar_api_success
```

---

## 13. Hardware Watchdog

The Pi's BCM2835 hardware watchdog auto-reboots the Pi if the kernel hangs.

**Enable the watchdog chip** (add to `/boot/firmware/config.txt` under the `[all]` section):
```bash
echo 'dtparam=watchdog=on' | sudo tee -a /boot/firmware/config.txt
```

**Configure systemd to use it** (edit `/etc/systemd/system.conf`, uncomment and set):
```bash
sudo sed -i 's/^#RuntimeWatchdogSec=off/RuntimeWatchdogSec=15s/' /etc/systemd/system.conf
sudo sed -i 's/^#RebootWatchdogSec=10min/RebootWatchdogSec=10min/' /etc/systemd/system.conf
```

**Reboot to activate:**
```bash
sudo reboot
```

**Verify after reboot:**
```bash
ls /dev/watchdog*
# Expected: /dev/watchdog  /dev/watchdog0

dmesg | grep -i watchdog
# Expected: systemd[1]: Using hardware watchdog 'Broadcom BCM2835 Watchdog timer'
```

---

## 14. HDMI Console (Headless Diagnostic Fallback)

The Pi is headless (SSH-first) but can output a text login prompt to HDMI for physical debugging without a network.

If HDMI output is blank on Raspberry Pi OS Lite, KMS overlays may be blocking it. In `/boot/firmware/config.txt`, the relevant settings are:

```
dtoverlay=vc4-kms-v3d     # 3D graphics overlay (fine for headless, keep it)
disable_fw_kms_setup=1    # prevents firmware from interfering with KMS
enable_uart=1             # ensures serial console is available
```

If you plug in an HDMI monitor and get no output, try adding `hdmi_force_hotplug=1` under `[all]` in `config.txt`.

---

## 15. Final Verification

Run through this checklist after a full rebuild:

```bash
# 1. All services active
systemctl is-active jonesbar-api.service jonesbar-ingest.timer \
  jonesbar-publish-outdoor.timer pi-alive.timer alloy.service mariadb.service

# 2. Deep health check returns 200
curl -s http://localhost:8000/health | python3 -m json.tool

# 3. Metrics endpoint responding
curl -s http://localhost:8000/metrics | head -5

# 4. Trigger a manual ingest and confirm DB write
sudo systemctl start jonesbar-ingest.service
journalctl -u jonesbar-ingest.service -n 10 --no-pager

# 5. Trigger a manual publish and confirm GitHub push
sudo systemctl start jonesbar-publish-outdoor.service
journalctl -u jonesbar-publish-outdoor.service -n 10 --no-pager

# 6. Confirm heartbeats reach Healthchecks.io
sudo bash -c 'source /etc/jonesbar/heartbeats.env && curl -fsS "$INGEST_OK_URL" && echo OK'

# 7. Hardware watchdog active
dmesg | grep -i watchdog

# 8. Check Grafana Cloud: Explore → Prometheus → query jonesbar_api_success
```
