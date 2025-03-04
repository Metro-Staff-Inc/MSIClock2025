#!/bin/bash

### MSI Time Clock Installation Script for Ubuntu Desktop ###
# Run this script as root after a fresh Ubuntu 24.04 Desktop installation.

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
systemctl daemon-reload

# --- Remove Unnecessary Ubuntu Desktop Applications ---
echo "Removing unnecessary Ubuntu Desktop applications..."
apt remove -y libreoffice-* thunderbird gnome-games gnome-calendar rhythmbox cheese aisleriot shotwell transmission-gtk simple-scan firefox
apt autoremove -y
apt purge -y snapd
rm -rf ~/snap

# --- User Account Setup ---
USERNAME="msi-clock"
PASSWORD="Metro2024!"

# Ensure the user exists (skip creation if already exists)
echo "Ensuring user exists: $USERNAME"
id -u $USERNAME &>/dev/null || useradd -m -s /bin/bash "$USERNAME"
echo "$USERNAME:$PASSWORD" | chpasswd
usermod -aG sudo "$USERNAME"
usermod -aG video,input,tty "$USERNAME"  # Ensure webcam and input access

# --- System Update and Package Installation ---
echo "Updating system and installing required packages..."
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv python3-tk sqlite3 curl wget git network-manager v4l-utils

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

# --- Configure MSI Clock to Auto-Start ---
echo "Configuring MSI Clock to start on login..."
sudo -u $USERNAME mkdir -p /home/$USERNAME/.config/autostart
cat <<EOF > /home/$USERNAME/.config/autostart/msi-clock.desktop
[Desktop Entry]
Type=Application
Exec=/opt/msi-clock/venv/bin/python /opt/msi-clock/main.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=MSI Clock
EOF
chown $USERNAME:$USERNAME /home/$USERNAME/.config/autostart/msi-clock.desktop

# --- Install RustDesk ---
echo "Installing RustDesk..."
LATEST_VERSION=$(curl -s https://api.github.com/repos/rustdesk/rustdesk/releases/latest | grep "tag_name" | cut -d '"' -f 4)
DEB_URL="https://github.com/rustdesk/rustdesk/releases/download/${LATEST_VERSION}/rustdesk-${LATEST_VERSION#v}-x86_64.deb"

wget -O rustdesk.deb "$DEB_URL" || { echo "Failed to download RustDesk."; exit 1; }
apt install -y ./rustdesk.deb || apt --fix-broken install -y
rm rustdesk.deb

# --- Configure RustDesk for Unattended Access ---
sudo -u $USERNAME mkdir -p /home/$USERNAME/.config/autostart
cat <<EOF > /home/$USERNAME/.config/autostart/rustdesk.desktop
[Desktop Entry]
Type=Application
Exec=rustdesk
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=RustDesk
EOF
chown $USERNAME:$USERNAME /home/$USERNAME/.config/autostart/rustdesk.desktop

# --- Configure Webcam Access (Udev Rules) ---
echo "Configuring webcam access..."
cat <<EOF > /etc/udev/rules.d/99-webcam.rules
SUBSYSTEM=="video4linux", GROUP="video", MODE="0666"
EOF
udevadm control --reload-rules && udevadm trigger

# --- Disable Automatic Updates and MOTD ---
echo "Disabling automatic updates..."
apt remove -y unattended-upgrades
if [ -f /etc/pam.d/sshd ]; then
    sed -i 's/\\(\\s*\\)\\(.*motd.*\\)/#\\1\\2/' /etc/pam.d/sshd
fi
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
