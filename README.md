# Uptime Monitor

Python uptime monitor for Raspberry Pi — checks websites, measures response times, sends Pushover push notifications on downtime, with a web dashboard showing status, uptime statistics, and response time graphs.

## Installation

```bash
# Clone the repository
git clone https://github.com/Werizu/UptimeMonitor.git /tmp/uptime-monitor
cd /tmp/uptime-monitor

# Configure Pushover (see below)
cp config.example.json config.json
nano config.json

# Install
sudo ./install.sh
```

## Pushover setup

1. Create an account at [pushover.net](https://pushover.net)
2. Create a new application at [pushover.net/apps/build](https://pushover.net/apps/build)
3. Add to `config.json`:
   - `user_key`: Your User Key (shown on the Pushover homepage)
   - `api_token`: API Token of the created application

## Configure sites

Edit `/opt/uptime-monitor/config.json`:

```json
{
  "sites": [
    {
      "name": "My Website",
      "url": "https://example.com",
      "check_interval": 300
    },
    {
      "name": "API Server",
      "url": "https://api.example.com/health",
      "check_interval": 60
    }
  ]
}
```

- `check_interval`: Check interval in seconds (default: 300 = 5 min)
- `timeout`: Seconds until timeout (default: 10)
- `expected_status`: Expected HTTP status code (default: 200)

After changes: `sudo systemctl restart uptime-monitor`

## Manage services

```bash
# Check status
sudo systemctl status uptime-monitor
sudo systemctl status uptime-dashboard

# Stop / Start
sudo systemctl stop uptime-monitor
sudo systemctl start uptime-monitor

# View logs
sudo journalctl -u uptime-monitor -f
sudo journalctl -u uptime-dashboard -f
```

## Dashboard

The web dashboard runs on port 5000: `http://<pi-ip>:5000`

### Apache Reverse Proxy

As a subdomain (`uptime.example.com`):

```apache
<VirtualHost *:80>
    ServerName uptime.example.com
    ProxyPass / http://localhost:5000/
    ProxyPassReverse / http://localhost:5000/
</VirtualHost>
```

Or as a subdirectory (`example.com/uptime`):

```apache
ProxyPass /uptime http://localhost:5000
ProxyPassReverse /uptime http://localhost:5000
```

Enable Apache modules:

```bash
sudo a2enmod proxy proxy_http
sudo systemctl restart apache2
```

## Database

SQLite database at `/opt/uptime-monitor/data/uptime.db`. Data older than 90 days is automatically cleaned up daily at 03:00.
