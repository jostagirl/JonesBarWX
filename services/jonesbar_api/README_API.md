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
