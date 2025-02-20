#!/bin/bash

echo "MSI Time Clock Installation Script"
echo "================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo)"
    exit 1
fi

# Get username for service file
read -p "Enter username for service file: " USERNAME

echo "Installing system dependencies..."
apt-get update
apt-get install -y python3-tk python3-pip python3-opencv nvidia-cuda-toolkit

echo "Installing Python dependencies..."
pip3 install -r requirements.txt

echo "Creating required directories..."
mkdir -p logs
mkdir -p photos
mkdir -p data

echo "Setting up fonts..."
# Create user fonts directory if it doesn't exist
mkdir -p /home/$USERNAME/.fonts

# Copy fonts to user's fonts directory
cp assets/fonts/Roboto-Regular.ttf /home/$USERNAME/.fonts/
cp assets/fonts/OpenSans-Regular.ttf /home/$USERNAME/.fonts/

# Update font cache
fc-cache -f -v

echo "Setting permissions..."
chown -R $USERNAME:$USERNAME .
chmod 755 main.py

echo "Creating systemd service..."
cat > /etc/systemd/system/timeclock.service << EOL
[Unit]
Description=MSI Time Clock
After=network.target

[Service]
ExecStart=/usr/bin/python3 $(pwd)/main.py
WorkingDirectory=$(pwd)
User=$USERNAME
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/$USERNAME/.Xauthority

[Install]
WantedBy=graphical.target
EOL

echo "Enabling service..."
systemctl enable timeclock

echo "Adding user to required groups..."
usermod -a -G video $USERNAME

echo "Installation complete!"
echo
echo "Next steps:"
echo "1. Update settings.json with your SOAP credentials"
echo "2. Test the camera using: python3 test_components.py"
echo "3. Start the service: sudo systemctl start timeclock"
echo
echo "For troubleshooting, check the logs in the logs directory"