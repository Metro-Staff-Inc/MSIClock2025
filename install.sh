#!/bin/bash
# MSI TimeClock 2025 Ubuntu 24.04 Installer
# Run as root after fresh Ubuntu Desktop install

set -e  # Exit on error
set -o pipefail

### --- Configuration ---
USERNAME="msi-clock"
PASSWORD="Metro2024!"
RUSTDESK_PASSWORD="12345678"
CUSTOM_ANYDESK_URL="https://my.anydesk.com/v2/builds/download/708681/Linux-AnyDesk.tar.gz"
REPO_URL="https://github.com/Metro-Staff-Inc/MSIClock2025"
INSTALL_DIR="/opt/msi-clock"
FONT_DIR="/usr/local/share/fonts/msi-clock"
TMP_DIR="/tmp/msi-timeclock-install"

### --- Must be run as root ---
if [[ $EUID -ne 0 ]]; then
    echo "❌ This script must be run as root."
    exit 1
fi

echo "🛠️ Starting MSI TimeClock installation..."

### --- 0. Cleanup ---
echo "🧹 Cleaning up previous installations..."
systemctl stop msi-clock || true
systemctl stop rustdesk || true
systemctl stop anydesk || true
rm -rf "$INSTALL_DIR" /var/lib/msi-clock "$TMP_DIR"
rm -f /etc/systemd/system/{msi-clock.service,rustdesk.service}
rm -f /etc/udev/rules.d/99-webcam.rules
systemctl daemon-reexec
systemctl daemon-reload

### --- 1. Remove Unwanted Applications ---
echo "🧼 Removing default Ubuntu apps..."
apt purge -y libreoffice-* thunderbird gnome-games gnome-calendar rhythmbox cheese aisleriot shotwell transmission-gtk simple-scan firefox snapd || true
rm -rf /home/*/snap
apt autoremove -y

### --- 2. Create msi-clock User ---
echo "👤 Creating user: $USERNAME"
if ! id "$USERNAME" >/dev/null 2>&1; then
    useradd -m -s /bin/bash "$USERNAME"
    echo "$USERNAME:$PASSWORD" | chpasswd
fi
usermod -aG sudo,video,input,tty "$USERNAME"

### --- 3. Force GDM to use X11 & Autologin ---
echo "🖥️ Configuring GDM to use X11..."
mkdir -p /etc/gdm3
sed -i '/^\[daemon\]/a AutomaticLoginEnable=true\nAutomaticLogin='$USERNAME /etc/gdm3/custom.conf || echo -e "[daemon]\nAutomaticLoginEnable=true\nAutomaticLogin=$USERNAME" > /etc/gdm3/custom.conf
sed -i 's/^#WaylandEnable=/WaylandEnable=/;s/^WaylandEnable=.*/WaylandEnable=false/' /etc/gdm3/custom.conf

mkdir -p /var/lib/AccountsService/users
cat <<EOF > /var/lib/AccountsService/users/$USERNAME
[User]
Session=ubuntu-xorg
XSession=ubuntu-xorg
EOF

### --- 4. Disable Power Saving, Locking, Notifications ---
echo "🔌 Disabling power saving and screen blanking for $USERNAME..."
sudo -u "$USERNAME" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u $USERNAME)/bus" bash <<EOF
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing'
gsettings set org.gnome.desktop.session idle-delay 0
gsettings set org.gnome.desktop.screensaver lock-enabled false
gsettings set org.gnome.desktop.screensaver idle-activation-enabled false
gsettings set org.gnome.desktop.notifications show-banners false
gsettings set org.gnome.desktop.notifications application-activate false
EOF

### --- 5. Clone Application ---
echo "📦 Cloning MSI TimeClock..."
git clone "$REPO_URL" "$INSTALL_DIR"
chown -R "$USERNAME:$USERNAME" "$INSTALL_DIR"

### --- 6. Install Fonts ---
echo "🔤 Installing fonts..."
mkdir -p "$FONT_DIR"
cp "$INSTALL_DIR/assets/fonts/"*.ttf "$FONT_DIR/"
chmod 644 "$FONT_DIR"/*
fc-cache -f -v

### --- 7. Python Environment ---
echo "🐍 Setting up Python virtual environment..."
apt update
apt install -y python3 python3-venv python3-pip python3-tk sqlite3 git curl wget network-manager v4l-utils

python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r "$INSTALL_DIR/requirements.txt"
deactivate

chown -R "$USERNAME:$USERNAME" "$INSTALL_DIR/venv"

### --- 8. Autostart Entry ---
echo "🚀 Creating autostart entry..."
sudo -u "$USERNAME" mkdir -p "/home/$USERNAME/.config/autostart"
cat <<EOF > "/home/$USERNAME/.config/autostart/msi-clock.desktop"
[Desktop Entry]
Type=Application
Exec=bash -c 'cd $INSTALL_DIR && $INSTALL_DIR/venv/bin/python main.py'
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=MSI Clock
Path=$INSTALL_DIR
Icon=$INSTALL_DIR/assets/people-dark-bg.png
EOF
chown "$USERNAME:$USERNAME" "/home/$USERNAME/.config/autostart/msi-clock.desktop"

sudo -u "$USERNAME" mkdir -p "/home/$USERNAME/Desktop"
cp "/home/$USERNAME/.config/autostart/msi-clock.desktop" "/home/$USERNAME/Desktop/msi-clock.desktop"
chmod +x "/home/$USERNAME/Desktop/msi-clock.desktop"
chown "$USERNAME:$USERNAME" "/home/$USERNAME/Desktop/msi-clock.desktop"

### --- 9. Install RustDesk ---
echo "📡 Installing RustDesk..."
LATEST_VERSION=$(curl -s https://api.github.com/repos/rustdesk/rustdesk/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
DEB_URL="https://github.com/rustdesk/rustdesk/releases/download/${LATEST_VERSION}/rustdesk-${LATEST_VERSION#v}-x86_64.deb"
wget -O /tmp/rustdesk.deb "$DEB_URL"
apt install -y /tmp/rustdesk.deb || apt --fix-broken install -y
rm /tmp/rustdesk.deb

CONFIG_DIR="/home/$USERNAME/.config/rustdesk"
mkdir -p "$CONFIG_DIR"
PASSWORD_HASH=$(echo -n "$RUSTDESK_PASSWORD" | sha256sum | awk '{print $1}')
cat <<EOF > "$CONFIG_DIR/config.json"
{
  "pswd_h": "$PASSWORD_HASH"
}
EOF
cat <<EOF > "$CONFIG_DIR/settings.json"
{
  "selected_display": "all",
  "session_always_accept": true,
  "session_permission_dialog": false
}
EOF
chown -R "$USERNAME:$USERNAME" "$CONFIG_DIR"
chmod 600 "$CONFIG_DIR"/*.json

cat <<EOF > /etc/systemd/system/rustdesk.service
[Unit]
Description=RustDesk Remote Desktop
After=network.target

[Service]
ExecStart=/usr/bin/rustdesk --headless
User=$USERNAME
Restart=always
RestartSec=5
Environment=DISPLAY=:0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable rustdesk.service
systemctl restart rustdesk.service

### --- 10. Install AnyDesk and Patch ---
echo "📥 Installing AnyDesk..."
wget -qO - https://keys.anydesk.com/repos/DEB-GPG-KEY | gpg --dearmor -o /usr/share/keyrings/anydesk.gpg
echo "deb [signed-by=/usr/share/keyrings/anydesk.gpg] http://deb.anydesk.com/ all main" > /etc/apt/sources.list.d/anydesk.list
apt update
apt install -y anydesk

echo "🔧 Replacing AnyDesk with custom build..."
mkdir -p "$TMP_DIR"
wget -O "$TMP_DIR/custom.tar.gz" "$CUSTOM_ANYDESK_URL"
tar -xzf "$TMP_DIR/custom.tar.gz" -C "$TMP_DIR"
systemctl stop anydesk.service || true
mv "$TMP_DIR/anydesk" /usr/bin/anydesk
chmod +x /usr/bin/anydesk
systemctl restart anydesk.service
rm -rf "$TMP_DIR"

### --- 11. Webcam Access ---
echo "🎥 Setting webcam access permissions..."
cat <<EOF > /etc/udev/rules.d/99-webcam.rules
SUBSYSTEM=="video4linux", GROUP="video", MODE="0666"
EOF
udevadm control --reload-rules
udevadm trigger

### --- 12. Disable Updates & MOTD (with error handling) ---
echo "⚙️ Disabling automatic updates and MOTD..."
if dpkg -l | grep -q unattended-upgrades; then
    apt remove -y unattended-upgrades || echo "⚠️ Failed to remove unattended-upgrades."
else
    echo "ℹ️ Unattended-upgrades not installed, skipping."
fi

if [ -d /etc/update-motd.d ]; then
    rm -f /etc/update-motd.d/* || echo "⚠️ Failed to remove some MOTD scripts."
else
    echo "ℹ️ /etc/update-motd.d does not exist, skipping."
fi

if [ -f /etc/pam.d/sshd ]; then
    sed -i 's/^\(.*motd.*\)/# \1/' /etc/pam.d/sshd || echo "⚠️ Failed to update /etc/pam.d/sshd."
else
    echo "ℹ️ /etc/pam.d/sshd not found, skipping PAM MOTD update."
fi

### --- 13. Disable Wi-Fi Powersave ---
echo "📶 Disabling Wi-Fi power management..."
sed -i 's/^wifi.powersave = .*/wifi.powersave = 2/' /etc/NetworkManager/conf.d/default-wifi-powersave-on.conf || true

### --- 14. Done ---
echo "✅ MSI TimeClock installation complete!"
echo "📄 RustDesk password: $RUSTDESK_PASSWORD" > /root/rustdesk-info.txt
chmod 600 /root/rustdesk-info.txt

# Uncomment if auto-reboot is desired:
# reboot
