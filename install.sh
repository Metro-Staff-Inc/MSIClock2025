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
apt-get install -y \
    python3-tk \
    python3-pip \
    python3-opencv \
    python3-dev \
    python3-setuptools \
    build-essential \
    cmake \
    pkg-config \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    v4l-utils \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxcb-randr0 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    v41-utils

# Install CUDA only if needed and available
if lspci | grep -i nvidia > /dev/null; then
    echo "NVIDIA GPU detected, installing CUDA toolkit..."
    apt-get install -y nvidia-cuda-toolkit
else
    echo "No NVIDIA GPU detected, skipping CUDA toolkit..."
fi

# Check if system Python is externally managed and install correctly
if python3 -m pip --version 2>/dev/null | grep -q "externally managed"; then
    echo "System Python is externally managed, using --break-system-packages"
    pip3 install --break-system-packages -r requirements.txt
else
    echo "Installing normally..."
    pip3 install -r requirements.txt
fi


echo "Creating required directories..."
mkdir -p logs
mkdir -p photos
mkdir -p data

echo "Setting up fonts..."
# Download fonts if needed
echo "Checking and downloading fonts..."
python3 download_fonts.py

# Create user fonts directory if it doesn't exist
mkdir -p /home/$USERNAME/.fonts
mkdir -p /home/$USERNAME/.local/share/fonts

# Copy required fonts to both locations for compatibility
cp assets/fonts/Roboto-Regular.ttf /home/$USERNAME/.fonts/
cp assets/fonts/IBMPlexSans-Medium.ttf /home/$USERNAME/.fonts/
cp assets/fonts/IBMPlexSansCondensed-Bold.ttf /home/$USERNAME/.fonts/

cp assets/fonts/Roboto-Regular.ttf /home/$USERNAME/.local/share/fonts/
cp assets/fonts/IBMPlexSans-Medium.ttf /home/$USERNAME/.local/share/fonts/
cp assets/fonts/IBMPlexSansCondensed-Bold.ttf /home/$USERNAME/.local/share/fonts/

# Set correct ownership and permissions
chown -R $USERNAME:$USERNAME /home/$USERNAME/.fonts
chown -R $USERNAME:$USERNAME /home/$USERNAME/.local/share/fonts
chmod -R 644 /home/$USERNAME/.fonts/*.ttf
chmod -R 644 /home/$USERNAME/.local/share/fonts/*.ttf
chmod 755 /home/$USERNAME/.fonts
chmod 755 /home/$USERNAME/.local/share/fonts

# Update font cache
fc-cache -f -v

# Verify fonts were installed
echo "Verifying font installation..."
if fc-list | grep -i "IBM Plex" > /dev/null; then
    echo "Fonts installed successfully"
else
    echo "Warning: Some fonts may not have installed correctly"
fi

echo "Setting permissions..."
chown -R $USERNAME:$USERNAME .
chmod 755 main.py

echo "Creating desktop entry..."
cat > /usr/share/applications/MSITimeClock.desktop << EOL
[Desktop Entry]
Type=Application
Name=MSI Time Clock
Comment=Metro Staff Inc Time Clock Application
Exec=/usr/bin/python3 $(pwd)/main.py
Icon=$(pwd)/assets/people-dark-bg.png
Terminal=false
Categories=Utility;Office;
EOL

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

echo "Setting up camera access..."
# Add user to required groups
usermod -a -G video,input,dialout $USERNAME

# Create udev rules for camera access
echo "Creating udev rules for camera access..."
cat > /etc/udev/rules.d/99-camera.rules << EOL
KERNEL=="video[0-9]*", SUBSYSTEM=="video4linux", GROUP="video", MODE="0666"
KERNEL=="vchiq",  GROUP="video", MODE="0666"
EOL

# Reload udev rules
udevadm control --reload-rules
udevadm trigger

# Set permissions on existing devices
echo "Setting permissions on camera devices..."
chmod 0666 /dev/video* 2>/dev/null || true

echo "Installation complete!"
echo
echo "Next steps:"
echo "1. Update settings.json with your SOAP credentials"
echo "2. Test the camera using: python3 test_components.py"
echo "3. Start the service: sudo systemctl start timeclock"
echo
echo "For troubleshooting, check the logs in the logs directory"