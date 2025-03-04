#!/bin/bash

### MSI Time Clock Automated Installation Script ###
# Run this script as root after a fresh Ubuntu 24.04 LTS installation.

set -e  # Exit immediately if a command fails

# --- Cleanup Previous Partial Installations ---
echo "Cleaning up any previous partial installations..."
systemctl stop msi-clock || true
systemctl stop rustdesk || true
rm -rf /opt/msi-clock
rm -rf /var/lib/msi-clock
rm -rf /etc/systemd/system/msi-clock.service
rm -rf /etc/systemd/system/rustdesk.service
rm -rf /etc/udev/rules.d/99-webcam.rules
rm -rf /home/msi-time-clock/.xinitrc
rm -rf /home/msi-time-clock/.bash_profile
rm -rf /home/msi-time-clock/.config/openbox
systemctl daemon-reload

# --- User Account Setup ---
USERNAME="msi-time-clock"
PASSWORD="Metro2024!"

# Ensure the user exists (skip creation if already exists)
echo "Ensuring user exists: $USERNAME"
id -u $USERNAME &>/dev/null || useradd -m -s /bin/bash "$USERNAME"
echo "$USERNAME:$PASSWORD" | chpasswd
usermod -aG sudo "$USERNAME"
usermod -aG video "$USERNAME"  # Ensure webcam access

# --- System Update and Package Installation ---
echo "Updating system and installing required packages..."
apt update && apt upgrade -y
apt install -y xserver-xorg x11-xserver-utils xinit openbox obconf python3 python3-pip python3-venv sqlite3 curl wget git network-manager v4l-utils

# --- Configure Auto-Login ---
echo "Setting up auto-login..."
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat <<EOF > /etc/systemd/system/getty@tty1.service.d/autologin.conf
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $USERNAME --noclear %I \$TERM
EOF

# --- Configure Xorg and Openbox to Start UI Automatically ---
cat <<EOF > "/home/$USERNAME/.xinitrc"
#!/bin/sh
exec openbox &
exec /opt/msi-clock/venv/bin/python /opt/msi-clock/main.py
EOF
chown $USERNAME:$USERNAME "/home/$USERNAME/.xinitrc"
chmod +x "/home/$USERNAME/.xinitrc"

# --- Configure Bash Profile to Start Xorg on Login ---
echo "if [[ -z \$DISPLAY ]] && [[ \$(tty) == /dev/tty1 ]]; then startx; fi" >> "/home/$USERNAME/.bash_profile"
chown $USERNAME:$USERNAME "/home/$USERNAME/.bash_profile"

# --- Configure Network (Prompt for Wi-Fi Setup) ---
echo "Checking network connection..."
if ! ping -c 1 google.com &> /dev/null; then
    echo "No internet detected. Would you like to set up Wi-Fi now? (y/n)"
    read -r WIFI_SETUP
    if [ "$WIFI_SETUP" == "y" ]; then
        nmcli dev wifi list
        echo "Enter Wi-Fi SSID: "
        read -r WIFI_SSID
        echo "Enter Wi-Fi Password (leave blank for none): "
        read -rs WIFI_PASS
        nmcli dev wifi connect "$WIFI_SSID" password "$WIFI_PASS"
    fi
fi

# --- Clone and Install MSI Time Clock Application ---
echo "Cloning MSI Clock application..."
git clone https://github.com/Metro-Staff-Inc/MSIClock2025 /opt/msi-clock
chown -R $USERNAME:$USERNAME /opt/msi-clock

# --- Set Up Python Virtual Environment ---
echo "Creating Python virtual environment..."
python3 -m venv /opt/msi-clock/venv
source /opt/msi-clock/venv/bin/activate
pip install -r /opt/msi-clock/requirements.txt
chown -R $USERNAME:$USERNAME /opt/msi-clock/venv

# --- Configure SQLite Database ---
mkdir -p /var/lib/msi-clock
cp /opt/msi-clock/database_template.db /var/lib/msi-clock/data.db
chown -R $USERNAME:$USERNAME /var/lib/msi-clock

# --- Install RustDesk ---
echo "Installing RustDesk..."
wget https://github.com/rustdesk/rustdesk/releases/latest/download/rustdesk-1.2.3-x86_64.deb
apt install -y ./rustdesk-1.2.3-x86_64.deb
rm rustdesk-1.2.3-x86_64.deb

# --- Configure RustDesk for Unattended Access ---
sudo -u $USERNAME mkdir -p "/home/$USERNAME/.config/openbox"
echo "rustdesk &" >> "/home/$USERNAME/.config/openbox/autostart"

cat <<EOF > /etc/systemd/system/rustdesk.service
[Unit]
Description=RustDesk Remote Desktop
After=network.target graphical.target

[Service]
ExecStart=/usr/bin/rustdesk
Restart=always
User=$USERNAME
Environment=DISPLAY=:0
WorkingDirectory=/home/$USERNAME

[Install]
WantedBy=graphical.target
EOF

systemctl daemon-reload
systemctl enable rustdesk
systemctl start rustdesk

# --- Configure Webcam Access (Udev Rules) ---
echo "Configuring webcam access..."
cat <<EOF > /etc/udev/rules.d/99-webcam.rules
SUBSYSTEM=="video4linux", GROUP="video", MODE="0666"
EOF
udevadm control --reload-rules && udevadm trigger

# --- Disable Automatic Updates and MOTD ---
echo "Disabling automatic updates..."
apt remove -y unattended-upgrades
sed -i 's/\(\s*\)\(.*motd.*\)/#\1\2/' /etc/pam.d/sshd
rm -f /etc/update-motd.d/*

# --- Configure Systemd Service for MSI Clock ---
cat <<EOF > /etc/systemd/system/msi-clock.service
[Unit]
Description=MSI Time Clock Application
After=network.target graphical.target

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=/opt/msi-clock
ExecStart=/opt/msi-clock/venv/bin/python /opt/msi-clock/main.py
Restart=always
RestartSec=5
StandardOutput=append:/var/log/msi-clock.log
StandardError=append:/var/log/msi-clock.log

[Install]
WantedBy=graphical.target
EOF

systemctl daemon-reload
systemctl enable msi-clock
systemctl start msi-clock

# --- Final Reboot ---
echo "Installation complete. Rebooting now..."
reboot
