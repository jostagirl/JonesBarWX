# Jones Bar WX API Service (FastAPI)

This service provides machine-facing JSON endpoints on the local network.
It will later support generating static files for Tableau Public and accepting local-only ingest from devices.

## Location in repo

<pre>
services/jonesbar_api/
├── app/
│   └── main.py
└── README_API.md
</pre>

## Phase 1: FastAPI skeleton (completed)

We stood up a minimal FastAPI service on the Pi 4 and verified it is reachable on the local network.

Preferred long-term LAN URL:
- <pre>http://rapi4.local:8000</pre>

Fallback if hostname resolution is unavailable:
- <pre>http://192.168.68.75:8000</pre>

Verified these endpoints load from another device on the same Wi-Fi:
- <pre>http://192.168.68.75:8000/health</pre>
- <pre>http://192.168.68.75:8000/docs</pre>
- <pre>http://192.168.68.75:8000/redoc</pre>

Manual run command used for the test:

<pre>
uvicorn app.main:app --host 0.0.0.0 --port 8000
</pre>

Next step:
- Convert the FastAPI service into an always-on systemd-managed service.
