# Publishing Apps as Tor Hidden Services with Eddi

**Purpose:** Guide for configuring web apps to be served as Tor hidden (onion) services using eddi-msgsrv, gunicorn, and nginx with Unix Domain Sockets.

---

## Architecture Overview

### Simple Setup (Recommended)

eddi connects directly to gunicorn - no nginx needed:

```
                    Tor Network
                         │
                         ▼
┌─────────────────────────────────────────┐
│  eddi-msgsrv                            │
│  (Tor hidden service proxy)             │
│  *.onion:80 → UDS                       │
└─────────────────┬───────────────────────┘
                  │ /tmp/myapp.sock
                  ▼
┌─────────────────────────────────────────┐
│  gunicorn                               │
│  (WSGI/ASGI server)                     │
│  Serves your Python app                 │
└─────────────────────────────────────────┘
```

### With nginx (Optional)

Only add nginx if you need: static file serving, rate limiting, multiple backends, or additional buffering:

```
eddi → nginx (UDS) → gunicorn (UDS) → app
```

---

## Quick Start

### 1. Install eddi-msgsrv

```bash
idlergear eddi install
```

### 2. Configure gunicorn for UDS

```bash
# gunicorn_config.py
bind = "unix:/tmp/myapp.sock"
workers = 4
worker_class = "sync"  # or "uvicorn.workers.UvicornWorker" for ASGI
```

### 3. Start your app

```bash
gunicorn --config gunicorn_config.py myapp:app
```

### 4. Start eddi hidden service

```bash
~/.idlergear/bin/eddi-msgsrv serve --socket /tmp/myapp.sock
```

Your app is now accessible via the `.onion` address printed by eddi.

---

## Detailed Configuration

### Gunicorn Configuration

#### Basic Flask/Django (WSGI)

```python
# gunicorn_config.py
import multiprocessing

# Bind to Unix socket
bind = "unix:/tmp/myapp.sock"

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"

# Timeouts
timeout = 120
keepalive = 5

# Security
umask = 0o007  # Socket permissions: owner and group only

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

#### FastAPI/Starlette (ASGI)

```python
# gunicorn_config.py
bind = "unix:/tmp/myapp.sock"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
```

### Start Commands

```bash
# Flask
gunicorn --config gunicorn_config.py "app:create_app()"

# Django
gunicorn --config gunicorn_config.py myproject.wsgi:application

# FastAPI
gunicorn --config gunicorn_config.py "main:app"
```

---

## With nginx (Optional)

Only add nginx if you need these features:
- Static file serving (images, CSS, JS)
- Rate limiting
- Request buffering for large uploads
- Load balancing across multiple gunicorn instances
- Additional security headers

For most apps, eddi → gunicorn directly is sufficient.

### nginx Configuration

```nginx
# /etc/nginx/sites-available/myapp

upstream myapp {
    server unix:/tmp/myapp-gunicorn.sock fail_timeout=0;
}

server {
    listen unix:/tmp/myapp.sock;

    # For eddi to connect
    server_name _;

    # Increase buffer sizes for Tor latency
    proxy_buffer_size 128k;
    proxy_buffers 4 256k;
    proxy_busy_buffers_size 256k;

    # Timeouts for Tor
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    location / {
        proxy_pass http://myapp;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static files (optional)
    location /static/ {
        alias /path/to/static/;
        expires 30d;
    }
}
```

### Enable nginx Configuration

```bash
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

When using nginx, update gunicorn to use a separate socket:

```python
# gunicorn_config.py
bind = "unix:/tmp/myapp-gunicorn.sock"  # nginx connects here
# eddi connects to nginx socket: /tmp/myapp.sock
```

---

## Eddi Hidden Service Configuration

### Basic Usage

```bash
# Serve app via UDS
~/.idlergear/bin/eddi-msgsrv serve --socket /tmp/myapp.sock

# With custom onion key directory
~/.idlergear/bin/eddi-msgsrv serve \
    --socket /tmp/myapp.sock \
    --key-dir ~/.idlergear/tor/myapp
```

### Persistent Onion Address

By default, eddi generates a new `.onion` address each time. For a persistent address:

```bash
# First run generates keys
~/.idlergear/bin/eddi-msgsrv serve \
    --socket /tmp/myapp.sock \
    --key-dir ~/.idlergear/tor/myapp

# Keys are saved in ~/.idlergear/tor/myapp/
# - hs_ed25519_secret_key
# - hs_ed25519_public_key
# - hostname (your .onion address)

# Subsequent runs use the same address
```

### Security: Protect Your Keys

```bash
# Set restrictive permissions
chmod 700 ~/.idlergear/tor/myapp
chmod 600 ~/.idlergear/tor/myapp/hs_ed25519_secret_key

# NEVER commit these to git
# .gitignore already includes:
# hs_ed25519_secret_key
# hs_ed25519_public_key
# hostname
# tor_data/
```

---

## Complete Startup Script

Create `run.sh` for your project (direct eddi → gunicorn, no nginx):

```bash
#!/bin/bash
set -e

APP_NAME="myapp"
SOCKET="/tmp/${APP_NAME}.sock"
TOR_KEY_DIR="$HOME/.idlergear/tor/$APP_NAME"

# Cleanup on exit
cleanup() {
    echo "Shutting down..."
    kill $GUNICORN_PID 2>/dev/null || true
    kill $EDDI_PID 2>/dev/null || true
    rm -f $SOCKET
}
trap cleanup EXIT

# Create key directory
mkdir -p "$TOR_KEY_DIR"
chmod 700 "$TOR_KEY_DIR"

# Start gunicorn (eddi connects directly to this socket)
echo "Starting gunicorn..."
gunicorn --bind "unix:$SOCKET" myapp:app &
GUNICORN_PID=$!

# Wait for socket
while [ ! -S "$SOCKET" ]; do
    sleep 0.1
done

# Start eddi (connects directly to gunicorn)
echo "Starting eddi hidden service..."
~/.idlergear/bin/eddi-msgsrv serve \
    --socket "$SOCKET" \
    --key-dir "$TOR_KEY_DIR" &
EDDI_PID=$!

# Show onion address
sleep 5
if [ -f "$TOR_KEY_DIR/hostname" ]; then
    ONION_ADDR=$(cat "$TOR_KEY_DIR/hostname")
    echo ""
    echo "=========================================="
    echo "App available at: http://$ONION_ADDR"
    echo "=========================================="
    echo ""
fi

# Wait for processes
wait
```

Make executable:

```bash
chmod +x run.sh
```

---

## Systemd Service (Production)

### Gunicorn Service

```ini
# /etc/systemd/system/myapp-gunicorn.service
[Unit]
Description=Gunicorn daemon for myapp
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/myapp
ExecStart=/path/to/venv/bin/gunicorn --bind unix:/tmp/myapp.sock myapp:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Eddi Service

eddi connects directly to gunicorn's socket:

```ini
# /etc/systemd/system/myapp-eddi.service
[Unit]
Description=Eddi hidden service for myapp
After=network.target myapp-gunicorn.service
Requires=myapp-gunicorn.service

[Service]
User=www-data
Group=www-data
ExecStart=/home/www-data/.idlergear/bin/eddi-msgsrv serve \
    --socket /tmp/myapp.sock \
    --key-dir /home/www-data/.idlergear/tor/myapp
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable myapp-gunicorn myapp-eddi
sudo systemctl start myapp-gunicorn myapp-eddi
```

---

## Testing Your Hidden Service

### From Tor Browser

1. Install Tor Browser: https://www.torproject.org/download/
2. Navigate to your `.onion` address
3. Your app should load

### From Command Line

```bash
# Install torsocks
sudo apt install torsocks

# Test via curl
torsocks curl -v http://your-address.onion/

# Test via Python
torsocks python -c "
import requests
r = requests.get('http://your-address.onion/')
print(r.status_code, r.text[:100])
"
```

### With IdlerGear Logging

```bash
# Terminal 1: Start log capture
idlergear logs serve --name myapp

# Terminal 2: Start app with logging
./run.sh 2>&1 | idlergear logs stream --to myapp

# Terminal 3: Follow logs
idlergear logs follow --session 1
```

---

## Troubleshooting

### Socket Permission Denied

```bash
# Check permissions
ls -la /tmp/myapp*.sock

# Set correct ownership
sudo chown www-data:www-data /tmp/myapp*.sock

# Or set umask in gunicorn config
umask = 0o000  # World readable/writable (less secure)
```

### Connection Refused

```bash
# Check gunicorn is running
ps aux | grep gunicorn

# Check socket exists
ls -la /tmp/myapp*.sock

# Check nginx config
sudo nginx -t
```

### Tor Connection Issues

```bash
# Check Tor is running (eddi starts its own)
ps aux | grep tor

# Check eddi logs
~/.idlergear/bin/eddi-msgsrv serve --socket /tmp/myapp.sock --verbose

# Verify onion address is valid
cat ~/.idlergear/tor/myapp/hostname
```

### Slow Initial Connection

Tor hidden services take 30-60 seconds to establish on first start. This is normal.

---

## Security Considerations

1. **Protect Tor keys**: Never commit `hs_ed25519_secret_key` to version control
2. **Restrict socket permissions**: Use `umask = 0o007` in gunicorn
3. **Run as non-root**: Use dedicated service account
4. **Keep eddi updated**: `idlergear eddi install --force`
5. **Monitor logs**: Use IdlerGear logging for anomaly detection

---

## Integration with IdlerGear Workflows

### Teleport with Hidden Service

```bash
# Prepare for teleport
idlergear teleport prepare

# After teleport, restart services
idlergear teleport watch --command "./run.sh"

# Finish and push
idlergear teleport finish
```

### Multi-LLM Development

```bash
# Local LLM streams logs
./run.sh 2>&1 | idlergear logs stream --to debug

# Remote LLM (via eddi messaging) can request log sections
idlergear message send --to local --body "Show last 100 lines of logs"
```

---

## Example: Flask App with Hidden Service

### app.py

```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        "status": "ok",
        "message": "Hello from the hidden service!"
    })

@app.route('/health')
def health():
    return jsonify({"healthy": True})

if __name__ == '__main__':
    app.run()
```

### gunicorn_config.py

```python
bind = "unix:/tmp/flask-app.sock"
workers = 2
timeout = 120
```

### run.sh

```bash
#!/bin/bash
set -e

# Start gunicorn
gunicorn --config gunicorn_config.py app:app &
GUNICORN_PID=$!

sleep 2

# Start eddi
~/.idlergear/bin/eddi-msgsrv serve \
    --socket /tmp/flask-app.sock \
    --key-dir ~/.idlergear/tor/flask-app &
EDDI_PID=$!

wait
```

### Deploy

```bash
# Install dependencies
pip install flask gunicorn

# Install eddi
idlergear eddi install

# Start
chmod +x run.sh
./run.sh
```

---

## See Also

- `AI_INSTRUCTIONS/IDLERGEAR_TOOLS.md` - All IdlerGear tools
- `AI_INSTRUCTIONS/LOGGING_DEBUGGING.md` - Log capture setup
- `EDDI_INTEGRATION.md` - Eddi messaging features
