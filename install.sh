#!/bin/bash
set -e

INSTALL_DIR="/opt/uptime-monitor"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Uptime Monitor Installation ==="

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./install.sh)"
    exit 1
fi

# Create install directory
echo "Creating $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR/data"
mkdir -p "$INSTALL_DIR/templates"

# Copy project files
echo "Copying files..."
cp "$SCRIPT_DIR/monitor.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/dashboard.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/database.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/config.json" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/templates/index.html" "$INSTALL_DIR/templates/"

# Create venv and install dependencies
echo "Setting up Python venv..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Create systemd service for monitor
cat > /etc/systemd/system/uptime-monitor.service << 'EOF'
[Unit]
Description=Uptime Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/uptime-monitor
ExecStart=/opt/uptime-monitor/venv/bin/python3 monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for dashboard
cat > /etc/systemd/system/uptime-dashboard.service << 'EOF'
[Unit]
Description=Uptime Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/uptime-monitor
ExecStart=/opt/uptime-monitor/venv/bin/python3 dashboard.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
echo "Enabling services..."
systemctl daemon-reload
systemctl enable uptime-monitor.service
systemctl enable uptime-dashboard.service
systemctl start uptime-monitor.service
systemctl start uptime-dashboard.service

echo ""
echo "=== Installation complete ==="
echo "Monitor: systemctl status uptime-monitor"
echo "Dashboard: systemctl status uptime-dashboard"
echo "Web UI: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "Edit config: $INSTALL_DIR/config.json"
echo "Then restart: sudo systemctl restart uptime-monitor"
