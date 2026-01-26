# Jones Bar WX API Service (FastAPI)

This service provides machine-facing JSON endpoints on the local network.
It will later support generating static files for Tableau Public and accepting local-only ingest from devices.

## Host and environment

Hostname:
- <pre>rapi4</pre>

Primary user:
- <pre>pi4</pre>

Repo root on Pi 4:
- <pre>/home/pi4/repo/JonesBarWX</pre>

FastAPI service folder (runs from here):
- <pre>/home/pi4/repo/JonesBarWX/services/jonesbar_api</pre>

FastAPI virtual environment path (used by systemd):
- <pre>/home/pi4/repo/JonesBarWX/services/jonesbar_api/venv</pre>

FastAPI app entrypoint:
- <pre>/home/pi4/repo/JonesBarWX/services/jonesbar_api/app/main.py</pre>

Systemd unit file path:
- <pre>/etc/systemd/system/jonesbar-api.service</pre>

## LAN URLs

Preferred long-term LAN URL (mDNS):
- <pre>http://rapi4.local:8000</pre>

Fallback if hostname resolution is unavailable:
- <pre>http://192.168.68.75:8000</pre>

Verified endpoints:
- <pre>http://192.168.68.75:8000/health</pre>
- <pre>http://192.168.68.75:8000/docs</pre>
- <pre>http://192.168.68.75:8000/redoc</pre>

## Location in repo

Repo-relative:

<pre>
services/jonesbar_api/
├── app/
│   └── main.py
├── venv/
├── .gitignore
└── README_API.md
</pre>

Absolute paths:

<pre>
/home/pi4/repo/JonesBarWX/services/jonesbar_api/app/main.py
/home/pi4/repo/JonesBarWX/services/jonesbar_api/README_API.md
/home/pi4/repo/JonesBarWX/services/jonesbar_api/.gitignore
/home/pi4/repo/JonesBarWX/services/jonesbar_api/venv/
</pre>

## Phase 1: FastAPI skeleton (completed)

Minimal app code is in:

<pre>
/home/pi4/repo/JonesBarWX/services/jonesbar_api/app/main.py
</pre>

Manual run command (development test):

<pre>
cd /home/pi4/repo/JonesBarWX/services/jonesbar_api
source /home/pi4/repo/JonesBarWX/services/jonesbar_api/venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
</pre>

Stop manual run:
- Ctrl+C

## Phase 2: systemd service (completed)

Systemd service name:
- <pre>jonesbar-api.service</pre>

Systemd unit file location:
- <pre>/etc/systemd/system/jonesbar-api.service</pre>

Service runs from:
- <pre>/home/pi4/repo/JonesBarWX/services/jonesbar_api</pre>

Service executable used:
- <pre>/home/pi4/repo/JonesBarWX/services/jonesbar_api/venv/bin/uvicorn</pre>

Service start command (embedded in systemd unit):
- <pre>uvicorn app.main:app --host 0.0.0.0 --port 8000</pre>

Useful systemd commands:

<pre>
sudo systemctl status jonesbar-api --no-pager
sudo systemctl restart jonesbar-api
sudo systemctl stop jonesbar-api
sudo systemctl start jonesbar-api
</pre>

Enable or disable start-on-boot:

<pre>
sudo systemctl enable jonesbar-api
sudo systemctl disable jonesbar-api
</pre>

View logs:

<pre>
sudo journalctl -u jonesbar-api -n 50 --no-pager
</pre>

If the unit file is edited, reload systemd:

<pre>
sudo systemctl daemon-reload
</pre>

## Notes on paths we intentionally did not use

We created an API folder under <pre>/opt/jonesbar_api</pre> earlier during initial testing.
We are not using that location for the running service in Model 1.

Source of truth is the repo path:

<pre>
/home/pi4/repo/JonesBarWX/services/jonesbar_api
</pre>

## Phase 3: DB-backed endpoint (completed)

A read-only endpoint now returns recent rows from MariaDB.

Endpoint:
- <pre>GET /api/system_health/recent?limit=5</pre>

Example URLs:
- <pre>http://rapi4.local:8000/api/system_health/recent?limit=5</pre>
- <pre>http://192.168.68.75:8000/api/system_health/recent?limit=5</pre>

Implementation files:
- <pre>/home/pi4/repo/JonesBarWX/services/jonesbar_api/app/main.py</pre>
- <pre>/home/pi4/repo/JonesBarWX/services/jonesbar_api/app/db.py</pre>

API venv packages added:
- <pre>python-dotenv</pre>
- <pre>pymysql</pre>

Notes:
- After a reboot, your shell is not in any venv until you run:
  <pre>source /home/pi4/repo/JonesBarWX/services/jonesbar_api/venv/bin/activate</pre>
- systemd always runs the API using:
  <pre>/home/pi4/repo/JonesBarWX/services/jonesbar_api/venv/bin/uvicorn</pre>

## Phase 4: Public static data publishing (completed)

Selected datasets are now published as static JSON and CSV files for public access via GitHub Pages.
The Pi remains private and is never exposed to inbound public traffic.

This publishing mechanism is intentionally separate from the local FastAPI service.

## Public data goals

- Allow one or more external users to consume data without direct Pi access
- Support Tableau Public and other tools that prefer static URLs
- Keep all credentials and database access private
- Use only free tools already in use
- Preserve clear observability when something stops updating

## Public repository and hosting

Public GitHub repository:
<pre>
https://github.com/jostagirl/PublicJonesBarWX_API
</pre>

Local clone on Pi:
<pre>
/home/pi4/repo_public/PublicJonesBarWX_API
</pre>

GitHub Pages hosting with Cloudflare in front.

Primary public URL:
<pre>
https://data.annabellizzi.com/
</pre>

Current published datasets:
<pre>
https://data.annabellizzi.com/data/outdoor_conditions.json
https://data.annabellizzi.com/data/outdoor_conditions.csv
</pre>

## Publisher script

Publisher script path:
<pre>
/home/pi4/repo/JonesBarWX/services/jonesbar_api/scripts/publish_outdoor_conditions.py
</pre>

This script:
- reads from MariaDB
- exports the last 7 days of data
- writes JSON and CSV files
- commits changes
- pushes to the public repo
- triggers GitHub Pages auto-publish

Logical flow:
<pre>
MariaDB
  → JSON + CSV files
    → git commit
      → git push
        → GitHub Pages publish
</pre>

Manual run (for testing):
<pre>
source /home/pi4/repo/JonesBarWX/services/jonesbar_api/venv/bin/activate
python /home/pi4/repo/JonesBarWX/services/jonesbar_api/scripts/publish_outdoor_conditions.py
</pre>

## Public index page behavior

The public index page displays:
- dataset download links
- file generation timestamp
- newest data timestamp
- short publisher description

Two timestamps are intentionally shown:
- File generated at
- Newest data timestamp

This makes it clear whether:
- ingestion has stalled
- publishing has stalled
- or both are healthy

Timestamp notes:
- JSON timestamps are not modified after generation
- Browser-side JavaScript normalizes UTC timestamps for display
- UTC and viewer-local time are shown side by side

## Automated publishing schedule (completed)

Public data publishing is now automated using a systemd timer.

We intentionally use systemd timers instead of cron for this task because:
- the job depends on a Python virtual environment
- git and SSH credentials must be available
- logs need to be easily inspectable
- behavior must survive reboots cleanly
- this matches the FastAPI service model already in use

## Publisher systemd service

Service name:
<pre>
jonesbar-publish-outdoor.service
</pre>

Service unit file:
<pre>
/etc/systemd/system/jonesbar-publish-outdoor.service
</pre>

Service runs as:
<pre>
pi4
</pre>

Service working directory:
<pre>
/home/pi4/repo_public/PublicJonesBarWX_API
</pre>

Service executable:
<pre>
/home/pi4/repo/JonesBarWX/services/jonesbar_api/venv/bin/python
</pre>

Script executed:
<pre>
/home/pi4/repo/JonesBarWX/services/jonesbar_api/scripts/publish_outdoor_conditions.py
</pre>

View logs:
<pre>
sudo journalctl -u jonesbar-publish-outdoor.service -n 50 --no-pager
</pre>

## Publisher systemd timer

Timer name:
<pre>
jonesbar-publish-outdoor.timer
</pre>

Timer unit file:
<pre>
/etc/systemd/system/jonesbar-publish-outdoor.timer
</pre>

Schedule:
- runs every 15 minutes
- persistent across reboots

Verify schedule:
<pre>
systemctl list-timers --all | grep jonesbar-publish-outdoor
</pre>

## End-to-end system architecture

<pre>
[ cron ]
  → Davis WeatherLink API
    → Python fetch script
      → MariaDB                (every 15 minutes)

[ systemd timer ]
  → publish_outdoor_conditions.py
      → MariaDB
        → JSON + CSV
          → git commit + push   (every 15 minutes)

[ GitHub Pages ]
  → static site publish
    → data.annabellizzi.com
</pre>

## Design notes

- The Pi is never exposed to the public internet
- No inbound ports are opened for public access
- GitHub Pages is used only for static files
- Cloudflare provides DNS and HTTPS
- The local FastAPI service and the public static data serve different purposes and are intentionally decoupled

## Status

This phase is complete and stable.

The system can be left running unattended.
