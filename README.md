# Uptime Monitor

Python-Dienst für den Raspberry Pi, der Websites überwacht, Response-Zeiten misst und bei Ausfällen Push-Notifications via Pushover sendet. Dazu ein Web-Dashboard mit Status, Uptime-Statistiken und Response-Zeit-Graphen.

## Installation

```bash
# Repository klonen
git clone https://github.com/Werizu/UptimeMonitor.git /tmp/uptime-monitor
cd /tmp/uptime-monitor

# Pushover konfigurieren (siehe unten)
nano config.json

# Installieren
sudo ./install.sh
```

## Pushover einrichten

1. Account auf [pushover.net](https://pushover.net) erstellen
2. Neue Application erstellen: [pushover.net/apps/build](https://pushover.net/apps/build)
3. In `config.json` eintragen:
   - `user_key`: Dein User Key (auf der Pushover-Startseite)
   - `api_token`: API Token der erstellten Application

## Sites konfigurieren

`/opt/uptime-monitor/config.json` bearbeiten:

```json
{
  "sites": [
    {
      "name": "Meine Website",
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

- `check_interval`: Prüfintervall in Sekunden (default: 300 = 5 min)
- `timeout`: Sekunden bis Timeout (default: 10)
- `expected_status`: Erwarteter HTTP-Statuscode (default: 200)

Nach Änderungen: `sudo systemctl restart uptime-monitor`

## Services verwalten

```bash
# Status prüfen
sudo systemctl status uptime-monitor
sudo systemctl status uptime-dashboard

# Stoppen / Starten
sudo systemctl stop uptime-monitor
sudo systemctl start uptime-monitor

# Logs anzeigen
sudo journalctl -u uptime-monitor -f
sudo journalctl -u uptime-dashboard -f
```

## Dashboard

Das Web-Dashboard läuft auf Port 5000: `http://<pi-ip>:5000`

### Apache Reverse Proxy

Als Subdomain (`uptime.marlonheck.de`):

```apache
<VirtualHost *:80>
    ServerName uptime.marlonheck.de
    ProxyPass / http://localhost:5000/
    ProxyPassReverse / http://localhost:5000/
</VirtualHost>
```

Oder als Unterverzeichnis (`marlonheck.de/uptime`):

```apache
ProxyPass /uptime http://localhost:5000
ProxyPassReverse /uptime http://localhost:5000
```

Apache-Module aktivieren:

```bash
sudo a2enmod proxy proxy_http
sudo systemctl restart apache2
```

## Datenbank

SQLite-Datenbank unter `/opt/uptime-monitor/data/uptime.db`. Daten älter als 90 Tage werden automatisch bereinigt (täglich um 03:00).
