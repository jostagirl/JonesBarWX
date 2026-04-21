# JonesBarWX — Weather Station Logger

Personal weather data collection system running on a headless Raspberry Pi 4 (hostname: `rapi4`) on the home network.

Pulls live data from a Davis WeatherLink station, stores it in a local MariaDB database, publishes a public JSON/CSV data file to GitHub Pages, and reports system health to Grafana Cloud.

---

## Architecture

```
Davis WeatherLink API
        │
        ▼ (every 15 min)
   wxtest.py  ──────────────────────────► MariaDB (weather_data)
        │                                      │
        └── heartbeat ──► Healthchecks.io      │
                                               ▼ (every 15 min, 2 min after ingest)
                              publish_outdoor_conditions.py
                                               │
                                               ├── heartbeat ──► Healthchecks.io
                                               └── git push ──► GitHub Pages (public JSON/CSV)

MariaDB ◄── jonesbar-api (FastAPI :8000)
                │  /health      — liveness + data freshness check
                │  /metrics     — Prometheus-format system health metrics
                └── /api/system_health/recent

/metrics ◄── Grafana Alloy (every 60s) ──► Grafana Cloud (dashboard)

Pi hardware ──► BCM2835 Watchdog ──► auto-reboot on kernel hang
```

---

## Project Structure

```
JonesBarWX/
├── wxtest.py                              # Data ingest script (Davis API → MariaDB)
├── services/
│   └── jonesbar_api/
│       ├── app/
│       │   ├── main.py                    # FastAPI app (/health, /metrics, API endpoints)
│       │   └── db.py                      # DB connection helper
│       └── scripts/
│           └── publish_outdoor_conditions.py  # DB → JSON/CSV → GitHub push
├── legacy/                                # Retired scripts (Windows-era)
├── logs/
│   └── weather_log.txt                    # Ingest log (rotated daily, 7-day retention)
├── .env                                   # Secrets — NOT committed (see Credentials)
├── requirements.txt
└── README.md
```

**Outside the repo** (on the Pi, not version-controlled):

| Path | Purpose |
|------|---------|
| `/etc/jonesbar/heartbeats.env` | Healthchecks.io ping URLs |
| `/etc/jonesbar/notify.env` | Push notification webhook URL |
| `/etc/jonesbar/alloy.env` | Grafana Alloy DB reader credentials |
| `/home/pi4/repo_public/PublicJonesBarWX_API/` | Public git repo pushed to GitHub Pages |

---

## Data Pipeline

### Ingest (`wxtest.py`)
Runs every 15 min via systemd. Calls the Davis WeatherLink v2 API, maps sensor blocks by type ID, and inserts new rows into four MariaDB tables only when values have changed:

| Sensor type ID | Table |
|---|---|
| 43 | `outdoor_conditions` |
| 243 | `indoor_conditions` |
| 242 | `barometric_conditions` |
| 504 | `network_status` |

On every run — success or failure — a row is written to `system_health` recording what happened. On success, a heartbeat ping is sent to Healthchecks.io. On failure, the script exits with a non-zero code so systemd can react.

Schema auto-expands: if the API returns a new field, an `ALTER TABLE ... ADD COLUMN` runs automatically.

### Publish (`publish_outdoor_conditions.py`)
Runs 2 minutes after each ingest cycle (every 15 min at :02/:17/:32/:47). Queries the last 7 days of `outdoor_conditions`, writes `data/outdoor_conditions.json` and `.csv` to a local clone of the public repo, then commits and pushes to GitHub Pages.

**Self-healing git behavior:** before every run, the script checks the public repo's state and repairs it automatically:
- If a previous rebase was interrupted → runs `git rebase --abort`
- If a previous merge was interrupted → runs `git merge --abort`
- Resets to match the remote (`git reset --hard origin/<branch>` + `git clean -fd`)

This means a failed or interrupted run never blocks future runs. Git push also retries up to 3 times with exponential backoff for transient network errors.

---

## Services & Scheduling

All scheduled work runs as systemd units. Check status with `systemctl status <name>` or logs with `journalctl -u <name> -n 50`.

| Unit | Type | Schedule | What it does |
|------|------|----------|-------------|
| `jonesbar-ingest.timer` | timer | Every 15 min at :00/:15/:30/:45 | Triggers ingest service |
| `jonesbar-ingest.service` | oneshot | — | Runs `wxtest.py` |
| `jonesbar-publish-outdoor.timer` | timer | Every 15 min at :02/:17/:32/:47 | Triggers publish service |
| `jonesbar-publish-outdoor.service` | oneshot | — | Runs `publish_outdoor_conditions.py` |
| `jonesbar-api.service` | persistent | Always running | FastAPI on port 8000 |
| `pi-alive.timer` | timer | Every 1 min | Triggers pi-alive heartbeat |
| `pi-alive.service` | oneshot | — | Curls Healthchecks.io pi-alive URL |
| `alloy.service` | persistent | Always running | Grafana metrics agent |

All project services have `OnFailure=notify@%n.service` — if any service exits with an error, the notify handler fires automatically.

---

## Alerting & Monitoring

This section documents every layer of the alerting and monitoring system. If something breaks, work through these in order.

### Layer 1 — Healthchecks.io Heartbeats

**What it is:** Healthchecks.io is an external service (healthchecks.io). The Pi sends periodic HTTP pings to unique URLs. If a ping is missed past its grace period, Healthchecks sends an alert via email and SMS.

**Why it matters:** This is the only layer that detects total Pi failure (power outage, kernel hang, network loss). All other monitoring runs *on* the Pi — if the Pi is dead, only an external watcher can notify you.

**Three monitors:**

| Monitor | Ping interval | Grace period | What a miss means |
|---|---|---|---|
| `jonesbar-pi-alive` | 1 min | 5 min | Pi is off, hung, or has no internet |
| `jonesbar-ingest-ok` | 15 min | 30 min | Ingest failed or Davis API is down |
| `jonesbar-publish-ok` | 15 min | 30 min | Publish to GitHub failed |

**Where the URLs are stored:** `/etc/jonesbar/heartbeats.env` (root-owned, mode 600).

**To check current state:** Log in to healthchecks.io and view the dashboard. All three should be green.

**To test manually:**
```bash
sudo bash -c 'source /etc/jonesbar/heartbeats.env && curl -fsS "$PI_ALIVE_URL"'
```

---

### Layer 2 — systemd `OnFailure` Handler

**What it is:** Every project service has `OnFailure=notify@%n.service` in its unit file. When a service exits with a non-zero code (real failure, not just "no new data"), systemd automatically starts `notify@<unitname>.service`, which runs `/usr/local/bin/jonesbar-notify`.

**What the handler does:**
1. Reads `NOTIFY_URL` from `/etc/jonesbar/notify.env`
2. If set, POSTs the unit name + last 20 journal lines to that URL (works with ntfy.sh, Pushover, Discord webhooks, or any HTTP POST endpoint)
3. Always exits 0 — a broken notification path never causes a loop

**Current state:** `NOTIFY_URL` is not yet configured (stub only). The handler logs "NOTIFY_URL unset; skipping" via `logger` when it fires, visible in:
```bash
journalctl -t jonesbar-notify -n 20
```

**To activate push alerts:** Get a free push endpoint (e.g. https://ntfy.sh/your-topic-name — no signup required, just pick a unique topic), then:
```bash
sudo nano /etc/jonesbar/notify.env
# Set: NOTIFY_URL=https://ntfy.sh/your-unique-topic
```

**To test the handler manually:**
```bash
sudo systemctl start 'notify@jonesbar-ingest.service.service'
journalctl -t jonesbar-notify -n 5
```

**To trigger a real failure test** (temporarily bad DB password):
```bash
sudo mkdir -p /etc/systemd/system/jonesbar-ingest.service.d
echo -e '[Service]\nEnvironment=DB_PASS=wrong' | sudo tee /etc/systemd/system/jonesbar-ingest.service.d/99-test.conf
sudo systemctl daemon-reload && sudo systemctl start jonesbar-ingest.service
journalctl -t jonesbar-notify -n 5
# Clean up after testing:
sudo rm -rf /etc/systemd/system/jonesbar-ingest.service.d && sudo systemctl daemon-reload
sudo systemctl reset-failed jonesbar-ingest.service
```

---

### Layer 3 — Hardware Watchdog

**What it is:** The Raspberry Pi has a built-in hardware watchdog chip (BCM2835). Once enabled, systemd must "pet" it every 15 seconds. If systemd itself freezes (kernel panic, full hang), the watchdog chip forces a hard reboot after 15 seconds — without any human intervention.

**Configuration:**
- `/boot/firmware/config.txt` — `dtparam=watchdog=on` (loads the watchdog kernel driver at boot)
- `/etc/systemd/system.conf` — `RuntimeWatchdogSec=15s` (systemd petting interval) and `RebootWatchdogSec=10min` (timeout if a reboot itself hangs)

**To verify it's active after a reboot:**
```bash
ls /dev/watchdog*
# Should show: /dev/watchdog  /dev/watchdog0

dmesg | grep -i watchdog
# Should show: systemd[1]: Using hardware watchdog 'Broadcom BCM2835 Watchdog timer'
```

**Note:** The watchdog only helps with kernel-level hangs. It does not restart individual services — systemd handles that via `Restart=always` (FastAPI) or re-triggering via timers (ingest, publish).

---

### Layer 4 — FastAPI `/health` Endpoint

**What it is:** A deep health check endpoint on the local API that any monitoring tool can probe.

**URL:** `http://rapi4:8000/health` (or `http://localhost:8000/health` on the Pi)

**What it checks:**
- Can the Pi connect to MariaDB?
- Is the newest `outdoor_conditions` row less than 30 minutes old?
- Is the newest `system_health` row less than 30 minutes old and `api_success=1`?

**Returns:** HTTP 200 with `"status": "ok"` if all pass; HTTP 503 with `"status": "degraded"` and per-check detail if anything fails.

```bash
curl http://localhost:8000/health
```

---

### Layer 5 — Grafana Cloud Metrics Dashboard

**What it is:** Grafana Alloy (running as `alloy.service`) scrapes the `/metrics` endpoint on the local FastAPI every 60 seconds and ships the data to Grafana Cloud. This gives a time-series dashboard of system health over time.

**Metrics published** (all prefixed `jonesbar_`):

| Metric | What it shows |
|---|---|
| `jonesbar_api_success` | Last ingest API call succeeded (1/0) |
| `jonesbar_db_success` | Last ingest DB write succeeded (1/0) |
| `jonesbar_insert_outdoor` | Outdoor row inserted last run (1/0) |
| `jonesbar_insert_indoor` | Indoor row inserted last run (1/0) |
| `jonesbar_insert_barometric` | Barometric row inserted last run (1/0) |
| `jonesbar_insert_network` | Network row inserted last run (1/0) |
| `jonesbar_skipped_inserts` | Rows skipped (no data change) |
| `jonesbar_is_maintenance` | Station in maintenance mode (1/0) |
| `jonesbar_ingest_has_error` | Last ingest had an error (1/0) |
| `jonesbar_ingest_age_seconds` | Seconds since last ingest ran |
| `jonesbar_outdoor_data_age_seconds` | Seconds since newest sensor reading |

**To verify metrics are flowing:**
```bash
curl http://localhost:8000/metrics
journalctl -u alloy -n 20
```

**In Grafana Cloud:** Explore → select the Prometheus datasource → query `jonesbar_api_success` or any `jonesbar_` metric.

**Alloy config file:** `/etc/alloy/config.alloy`

---

## Credentials Reference

None of these files are committed to the repository.

| File | Owner | Contents |
|------|-------|---------|
| `.env` (repo root) | pi4 | Davis API key/secret/station ID, MariaDB app credentials |
| `services/jonesbar_api/.env` | pi4 | MariaDB credentials for the FastAPI service |
| `/etc/jonesbar/heartbeats.env` | root, 600 | Healthchecks.io ping URLs (3 monitors) |
| `/etc/jonesbar/notify.env` | root, 600 | `NOTIFY_URL` for push alerts (configure to activate) |
| `/etc/jonesbar/alloy.env` | root, 600 | `alloy_reader` MariaDB credentials for Grafana Alloy |

---

## Troubleshooting Quick Reference

**Check all timers and their next scheduled run:**
```bash
systemctl list-timers jonesbar-ingest.timer jonesbar-publish-outdoor.timer pi-alive.timer
```

**Check if all services are up:**
```bash
systemctl is-active jonesbar-api.service jonesbar-ingest.timer jonesbar-publish-outdoor.timer pi-alive.timer alloy.service mariadb.service
```

**View recent ingest logs:**
```bash
journalctl -u jonesbar-ingest.service -n 50
# or the rotating log file:
tail -50 /home/pi4/repo/JonesBarWX/logs/weather_log.txt
```

**View recent publish logs:**
```bash
journalctl -u jonesbar-publish-outdoor.service -n 50
```

**Check the deep health endpoint:**
```bash
curl http://localhost:8000/health
```

**Check the last 10 system_health rows in the database:**
```bash
mysql -u weather_user -p weather_data -e \
  "SELECT timestamp_utc, api_success, db_success, errors FROM system_health ORDER BY timestamp_utc DESC LIMIT 10;"
```

**Restart a service manually:**
```bash
sudo systemctl restart jonesbar-api.service
sudo systemctl start jonesbar-ingest.service    # run ingest now
sudo systemctl start jonesbar-publish-outdoor.service  # run publish now
```

**Check if watchdog is active:**
```bash
dmesg | grep -i watchdog
```

**Check notify handler history:**
```bash
journalctl -t jonesbar-notify -n 20
```

---

## License

Personal and professional demonstration purposes only.
