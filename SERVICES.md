# JonesBarWX — systemd Unit Files & Scripts Reference

All service and timer unit files installed on the Pi, plus the notify helper script. Use this document to reinstall units on a fresh OS or to audit the current configuration.

Unit files live in `/etc/systemd/system/`. After creating or modifying any file, run `sudo systemctl daemon-reload`.

---

## Unit Files

### `jonesbar-api.service`
FastAPI service exposing `/health`, `/metrics`, and `/api/system_health/recent` on port 8000. Runs continuously; restarts automatically on failure.

```ini
[Unit]
Description=Jones Bar WX FastAPI Service
After=network.target mariadb.service
OnFailure=notify@%n.service

[Service]
User=pi4
Group=pi4
WorkingDirectory=/home/pi4/repo/JonesBarWX/services/jonesbar_api
ExecStart=/home/pi4/repo/JonesBarWX/services/jonesbar_api/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

### `jonesbar-ingest.service`
Runs `wxtest.py` once. Triggered by `jonesbar-ingest.timer`. Exits non-zero on any failure, which triggers `notify@`.

```ini
[Unit]
Description=Jones Bar WX Weather Ingest
After=network.target mariadb.service
OnFailure=notify@%n.service

[Service]
Type=oneshot
User=pi4
WorkingDirectory=/home/pi4/repo/JonesBarWX
EnvironmentFile=-/etc/jonesbar/heartbeats.env
ExecStart=/home/pi4/repo/JonesBarWX/.venv/bin/python /home/pi4/repo/JonesBarWX/wxtest.py
```

### `jonesbar-ingest.timer`
Fires `jonesbar-ingest.service` every 15 minutes at :00, :15, :30, :45.

```ini
[Unit]
Description=Run Jones Bar WX Weather Ingest every 15 minutes

[Timer]
OnCalendar=*:00/15
Persistent=true

[Install]
WantedBy=timers.target
```

---

### `jonesbar-publish-outdoor.service`
Runs `publish_outdoor_conditions.py` once. Triggered by `jonesbar-publish-outdoor.timer`. Self-heals the public git repo before each run. Exits non-zero on failure.

```ini
[Unit]
Description=Jones Bar WX Publish Outdoor Conditions
After=network.target mariadb.service
OnFailure=notify@%n.service

[Service]
Type=oneshot
User=pi4
WorkingDirectory=/home/pi4/repo_public/PublicJonesBarWX_API
EnvironmentFile=-/etc/jonesbar/heartbeats.env
ExecStart=/home/pi4/repo/JonesBarWX/services/jonesbar_api/venv/bin/python /home/pi4/repo/JonesBarWX/services/jonesbar_api/scripts/publish_outdoor_conditions.py
```

### `jonesbar-publish-outdoor.timer`
Fires `jonesbar-publish-outdoor.service` every 15 minutes at :02, :17, :32, :47 — 2 minutes after ingest so published data is always fresh.

```ini
[Unit]
Description=Run Jones Bar WX Outdoor Publisher every 15 minutes (offset 2 min after ingest)

[Timer]
OnCalendar=*:02/15
Persistent=true

[Install]
WantedBy=timers.target
```

---

### `pi-alive.service`
Curls the `PI_ALIVE_URL` heartbeat endpoint. Triggered by `pi-alive.timer`. Best-effort — always exits 0 so a network hiccup doesn't fill the journal with failures.

```ini
[Unit]
Description=Jones Bar Pi Alive Heartbeat

[Service]
Type=oneshot
EnvironmentFile=-/etc/jonesbar/heartbeats.env
ExecStart=/bin/bash -c 'test -n "$PI_ALIVE_URL" && /usr/bin/curl -fsS --max-time 10 -o /dev/null "$PI_ALIVE_URL" || true'
```

### `pi-alive.timer`
Fires `pi-alive.service` every minute.

```ini
[Unit]
Description=Pi Alive Heartbeat every minute

[Timer]
OnCalendar=minutely
Persistent=true

[Install]
WantedBy=timers.target
```

---

### `notify@.service`
Templated unit. Invoked automatically when any project service fails via `OnFailure=notify@%n.service`. Passes the failed unit name to the `/usr/local/bin/jonesbar-notify` script.

The `%i` in the unit expands to the instance name — the name of the failed unit.

```ini
[Unit]
Description=Notify on failure of %i

[Service]
Type=oneshot
ExecStart=/usr/local/bin/jonesbar-notify %i
```

---

## Helper Script

### `/usr/local/bin/jonesbar-notify`

Called by `notify@.service`. Reads `NOTIFY_URL` from `/etc/jonesbar/notify.env` and POSTs the unit name plus the last 20 journal lines to that URL. If `NOTIFY_URL` is empty, logs a message and exits cleanly. Always exits 0 to prevent alert loops.

```bash
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
```

**Install the script:**
```bash
sudo tee /usr/local/bin/jonesbar-notify > /dev/null < services/jonesbar_api/scripts/notify-template.sh
# Or paste the contents above directly, then:
sudo chmod 755 /usr/local/bin/jonesbar-notify
```

---

## Grafana Alloy Config

`/etc/alloy/config.alloy` — the base section is generated by the Grafana Cloud setup wizard; the `jonesbar` scrape block at the bottom is custom.

```alloy
prometheus.exporter.self "alloy_check" { }

discovery.relabel "alloy_check" {
  targets = prometheus.exporter.self.alloy_check.targets

  rule {
    target_label = "instance"
    replacement  = constants.hostname
  }

  rule {
    target_label = "alloy_hostname"
    replacement  = constants.hostname
  }

  rule {
    target_label = "job"
    replacement  = "integrations/alloy-check"
  }
}

prometheus.scrape "alloy_check" {
  targets    = discovery.relabel.alloy_check.output
  forward_to = [prometheus.relabel.alloy_check.receiver]

  scrape_interval = "60s"
}

prometheus.relabel "alloy_check" {
  forward_to = [prometheus.remote_write.metrics_service.receiver]

  rule {
    source_labels = ["__name__"]
    regex         = "(prometheus_target_sync_length_seconds_sum|prometheus_target_scrapes_.*|prometheus_target_interval.*|prometheus_sd_discovered_targets|alloy_build.*|prometheus_remote_write_wal_samples_appended_total|process_start_time_seconds)"
    action        = "keep"
  }
}

prometheus.remote_write "metrics_service" {
  endpoint {
    url = "https://prometheus-prod-67-prod-us-west-0.grafana.net/api/prom/push"

    basic_auth {
      username = "3133368"
      password = sys.env("GCLOUD_RW_API_KEY")
    }
  }
}

loki.write "grafana_cloud_loki" {
  endpoint {
    url = "https://logs-prod-021.grafana.net/loki/api/v1/push"

    basic_auth {
      username = "1562359"
      password = sys.env("GCLOUD_RW_API_KEY")
    }
  }
}

// ── Jones Bar WX custom metrics ──────────────────────────────────────────────
prometheus.scrape "jonesbar" {
  targets = [{__address__ = "localhost:8000"}]
  metrics_path    = "/metrics"
  scrape_interval = "60s"
  forward_to      = [prometheus.remote_write.metrics_service.receiver]
}
```

**Alloy API key** is stored in `/etc/systemd/system/alloy.service.d/env.conf`:

```ini
[Service]
Environment=GCLOUD_RW_API_KEY=YOUR_GRAFANA_CLOUD_API_KEY
```

---

## Install All Units at Once

```bash
# Copy all unit file contents into /etc/systemd/system/ as shown above, then:
sudo systemctl daemon-reload

# Enable persistent services and timers
sudo systemctl enable --now jonesbar-api.service
sudo systemctl enable --now jonesbar-ingest.timer
sudo systemctl enable --now jonesbar-publish-outdoor.timer
sudo systemctl enable --now pi-alive.timer

# notify@ and pi-alive.service are static (no enable needed — triggered on demand)

# Verify
systemctl list-timers jonesbar-ingest.timer jonesbar-publish-outdoor.timer pi-alive.timer
systemctl is-active jonesbar-api.service alloy.service mariadb.service
```
