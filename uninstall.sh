#!/bin/bash

echo "MSI Time Clock Uninstall Script"
echo "=============================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo)"
    exit 1
fi

echo "Stopping service..."
systemctl stop timeclock

echo "Disabling service..."
systemctl disable timeclock

echo "Removing service file..."
rm -f /etc/systemd/system/timeclock.service

echo "Reloading systemd..."
systemctl daemon-reload

echo "Cleaning up data directories..."
read -p "Do you want to remove all data (logs, photos, database)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Removing data directories..."
    rm -rf logs/
    rm -rf photos/
    rm -rf data/
    echo "Data removed."
else
    echo "Data preserved."
fi

echo "Uninstall complete!"
echo
echo "Note: Python packages and system dependencies were not removed."
echo "To remove them manually:"
echo "1. pip3 uninstall -r requirements.txt"
echo "2. apt-get remove python3-tk python3-pip python3-opencv libsm6 libxext6 libxrender1 libgl1-mesa-glx v4l-utils"