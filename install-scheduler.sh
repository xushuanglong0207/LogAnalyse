#!/bin/bash

# Install Log Monitor Scheduler Service

echo "Installing Log Monitor Scheduler..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

# Install sshpass if not available
if ! command -v sshpass &> /dev/null; then
    echo "Installing sshpass..."
    apt-get update
    apt-get install -y sshpass
fi

# Copy service file
cp /home/ugreen/log-analyse/log-monitor-scheduler.service /etc/systemd/system/

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable log-monitor-scheduler.service

echo "Service installed. You can now:"
echo "  - Start: sudo systemctl start log-monitor-scheduler"
echo "  - Stop:  sudo systemctl stop log-monitor-scheduler"
echo "  - View logs: sudo journalctl -u log-monitor-scheduler -f"
echo ""
echo "The scheduler will automatically:"
echo "  - Analyze logs every hour"
echo "  - Send daily email reports at 3PM"
echo "  - Only report logs that actually contain errors"