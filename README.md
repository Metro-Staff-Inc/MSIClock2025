# MSI Time Clock Application

A Python-based time clock application for Ubuntu systems that allows employees to clock in and out using barcode scanning, with photo capture and SOAP integration.

## Features

- Full-screen kiosk mode interface
- Barcode scanner support (USB HID device)
- Webcam photo capture on punch
- SOAP integration with MSIWebTrax
- Offline operation support
- Bilingual interface (English/Spanish)
- Admin control panel
- Automatic data synchronization
- Local storage with cleanup

## Requirements

- Ubuntu Operating System
- Python 3.8 or higher
- USB Barcode Scanner (HID mode)
- USB Webcam
- Network connection for SOAP integration

## Installation

### Ubuntu Installation

1. Install system dependencies:

```bash
sudo apt-get update
sudo apt-get install python3-tk python3-pip python3-opencv
```

2. Clone the repository and install Python dependencies:

```bash
git clone [repository-url]
cd TimeClock2024
pip install -r requirements.txt
```

3. Configure the application:

- Copy `settings.json` to the application directory
- Update SOAP credentials and other settings as needed

4. Run the installation script:

```bash
sudo chmod +x install.sh
sudo ./install.sh
```

### Windows Installation

#### Option 1: Using the Installer

1. Download `MSITimeClockSetup.exe` from the releases page
2. Run the installer
3. Update settings through the admin panel (Ctrl+Alt+A)

#### Option 2: Building from Source

1. Install required software:

   - Python 3.8 or higher
   - NSIS (Nullsoft Scriptable Install System)

2. Clone the repository:

```bash
git clone [repository-url]
cd TimeClock2024
```

3. Run the build script:

```bash
build_windows.bat
```

This will:

- Install required dependencies
- Create an executable using PyInstaller
- Generate an installer using NSIS

The installer will be created as `MSITimeClockSetup.exe`

## Configuration

The `settings.json` file contains all application configuration:

- SOAP Settings:

  - `username`: MSIWebTrax API username
  - `password`: MSIWebTrax API password
  - `endpoint`: API endpoint URL
  - `timeout`: Connection timeout in seconds

- Camera Settings:

  - `deviceId`: Webcam device ID (usually 0)
  - `captureQuality`: JPEG quality (0-100)
  - `resolution`: Capture resolution

- UI Settings:

  - `fullscreen`: Enable/disable fullscreen mode
  - `language`: Default language
  - `adminShortcut`: Admin panel shortcut key combination

- Storage Settings:
  - `retentionDays`: Days to keep offline records
  - `dbPath`: Local database path
  - `maxOfflineRecords`: Maximum offline records to store

## Auto-start Setup

1. Create a systemd service file:

```bash
sudo nano /etc/systemd/system/timeclock.service
```

2. Add the following content:

```ini
[Unit]
Description=MSI Time Clock
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/TimeClock2024/main.py
WorkingDirectory=/path/to/TimeClock2024
User=your-username
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/your-username/.Xauthority

[Install]
WantedBy=graphical.target
```

3. Enable and start the service:

```bash
sudo systemctl enable timeclock
sudo systemctl start timeclock
```

## Usage

### Employee Punch Operations

1. The main screen displays current time and punch instructions
2. Scan employee badge or enter ID manually
3. System captures photo and records punch
4. Status is displayed in both English and Spanish

### Admin Functions

Access the admin panel using the configured shortcut (default: Ctrl+Alt+A):

- View system status
- Configure settings
- Test camera
- View logs
- Clean up old records
- Exit kiosk mode

### Offline Operation

- System automatically stores punches when offline
- Punches are synchronized when connection is restored
- Photos are stored locally and uploaded later
- Status indicators show offline/online state

## Troubleshooting

### Camera Issues

- Check USB connection
- Verify device ID in settings
- Check permissions (user should be in video group)
- Review logs for error messages

### Network Issues

- Verify network connectivity
- Check SOAP endpoint accessibility
- Review offline storage status
- Check sync logs

### Interface Issues

- Verify X server is running
- Check user permissions
- Review application logs
- Verify display settings

## Maintenance

Regular maintenance tasks:

1. Monitor disk space:

   - Check photos directory
   - Review database size
   - Clean old logs

2. Update system:

   - Keep Ubuntu updated
   - Update Python packages
   - Check for application updates

3. Backup:
   - Regular database backups
   - Configuration backup
   - Log archives

## Support

For technical support:

- Email: support@example.com
- Phone: (555) 123-4567
- Hours: 8:00 AM - 5:00 PM CST

## License

Copyright © 2024 Metro Staff Inc. All rights reserved.
