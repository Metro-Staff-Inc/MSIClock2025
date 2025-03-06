#!/bin/bash
### MSI TimeClock Installation Script for Ubuntu Desktop ###
# Run this script as root after a fresh Ubuntu 24.04 Desktop installation.

# Ensure the script is run as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root."
    exit 1
fi

set -e  # Exit immediately if any command fails

echo "Starting MSI TimeClock installation..."

# --- Cleanup Previous Partial Installations ---
echo "Cleaning up any previous partial installations..."
systemctl stop msi-clock || true
systemctl stop rustdesk || true
rm -rf /opt/msi-clock
rm -rf /var/lib/msi-clock
rm -f /etc/systemd/system/msi-clock.service
rm -f /etc/systemd/system/rustdesk.service
rm -f /etc/udev/rules.d/99-webcam.rules
systemctl daemon-reload

# --- Remove Unnecessary Ubuntu Desktop Applications ---
echo "Removing unnecessary Ubuntu Desktop applications..."
apt remove -y libreoffice-* thunderbird gnome-games gnome-calendar rhythmbox cheese aisleriot shotwell transmission-gtk simple-scan firefox || true
apt autoremove -y
apt purge -y snapd || true
rm -rf /home/*/snap

# --- User Account Setup ---
USERNAME="msi-clock"
PASSWORD="Metro2024!"
echo "Setting up user account: $USERNAME"
if ! id -u $USERNAME >/dev/null 2>&1; then
    useradd -m -s /bin/bash "$USERNAME"
    echo "$USERNAME:$PASSWORD" | chpasswd
fi
usermod -aG sudo "$USERNAME"
usermod -aG video,input,tty "$USERNAME"  # Grant webcam and input permissions

# --- Configure Autologin ---
echo "Configuring autologin for $USERNAME..."
mkdir -p /etc/systemd/system/getty@tty1.service.d/
cat <<EOF > /etc/systemd/system/getty@tty1.service.d/override.conf
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $USERNAME --noclear %I \$TERM
EOF

# Also configure GDM autologin for desktop environment
mkdir -p /etc/gdm3
cat <<EOF > /etc/gdm3/custom.conf
[daemon]
AutomaticLoginEnable=true
AutomaticLogin=$USERNAME
EOF

# --- System Update and Package Installation ---
echo "Updating system and installing required packages..."
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv python3-tk sqlite3 curl wget git network-manager v4l-utils

# --- Clone and Install MSI TimeClock Application ---
echo "Cloning MSI TimeClock application..."
git clone https://github.com/Metro-Staff-Inc/MSIClock2025 /opt/msi-clock
chown -R $USERNAME:$USERNAME /opt/msi-clock

# --- Install Fonts ---
echo "Installing required fonts..."
mkdir -p /usr/local/share/fonts/msi-clock
cp /opt/msi-clock/assets/fonts/*.ttf /usr/local/share/fonts/msi-clock/
chmod 644 /usr/local/share/fonts/msi-clock/*
fc-cache -f -v

# --- Set Up Python Virtual Environment ---
echo "Setting up Python virtual environment..."
python3 -m venv /opt/msi-clock/venv
source /opt/msi-clock/venv/bin/activate
pip install --upgrade pip
pip install -r /opt/msi-clock/requirements.txt
deactivate
chown -R $USERNAME:$USERNAME /opt/msi-clock/venv

# --- Configure MSI TimeClock Autostart (Desktop) ---
echo "Configuring MSI TimeClock to autostart on user login..."
sudo -u $USERNAME mkdir -p /home/$USERNAME/.config/autostart
cat <<EOF > /home/$USERNAME/.config/autostart/msi-clock.desktop
[Desktop Entry]
Type=Application
Exec=bash -c 'cd /opt/msi-clock && /opt/msi-clock/venv/bin/python main.py'
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=MSI Clock
Path=/opt/msi-clock
Icon=/opt/msi-clock/assets/people-dark-bg.png
EOF
chown $USERNAME:$USERNAME /home/$USERNAME/.config/autostart/msi-clock.desktop

# --- Create Desktop Launcher ---
echo "Creating desktop launcher..."
sudo -u $USERNAME mkdir -p /home/$USERNAME/Desktop
cat <<EOF > /home/$USERNAME/Desktop/msi-clock.desktop
[Desktop Entry]
Type=Application
Exec=bash -c 'cd /opt/msi-clock && /opt/msi-clock/venv/bin/python main.py'
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=MSI Clock
Path=/opt/msi-clock
Icon=/opt/msi-clock/assets/people-dark-bg.png
EOF
chmod +x /home/$USERNAME/Desktop/msi-clock.desktop
chown $USERNAME:$USERNAME /home/$USERNAME/Desktop/msi-clock.desktop

# --- Install RustDesk ---
echo "Installing RustDesk..."
LATEST_VERSION=$(curl -s https://api.github.com/repos/rustdesk/rustdesk/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
DEB_URL="https://github.com/rustdesk/rustdesk/releases/download/${LATEST_VERSION}/rustdesk-${LATEST_VERSION#v}-x86_64.deb"
wget -O /tmp/rustdesk.deb "$DEB_URL" || { echo "Failed to download RustDesk."; exit 1; }
apt install -y /tmp/rustdesk.deb || apt --fix-broken install -y
rm /tmp/rustdesk.deb

# --- Configure RustDesk Autostart (Desktop) ---
echo "Configuring RustDesk to autostart on user login..."
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
echo "Disabling automatic updates and MOTD..."
apt remove -y unattended-upgrades || true
if [ -f /etc/pam.d/sshd ]; then
    sed -i 's/\(\s*\)\(.*motd.*\)/#\1\2/' /etc/pam.d/sshd
fi
rm -f /etc/update-motd.d/*

# --- Disable Automatic Suspend and Screen Blackout ---
echo "Disabling automatic suspend and screen blackout..."
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'
gsettings set org.gnome.desktop.session idle-delay 0
gsettings set org.gnome.desktop.screensaver lock-enabled false
gsettings set org.gnome.desktop.screensaver idle-activation-enabled false

# --- Disable Notifications ---
echo "Disabling notifications..."
gsettings set org.gnome.desktop.notifications show-banners false
gsettings set org.gnome.desktop.notifications application-activate false

echo "Installation complete."
# --- Optional Reboot ---
# Uncomment the next line to reboot automatically after installation.
# reboot