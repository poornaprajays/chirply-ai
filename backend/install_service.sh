#!/bin/bash

# Chirply AI Backend Service Installer Script
# Run this on the Raspberry Pi to register the FastAPI backend as a systemd service.

set -e

# Verify we are running on Linux (Raspberry Pi)
if [ "$(uname)" != "Linux" ]; then
    echo "Error: This script must be run on Linux (Raspberry Pi)."
    exit 1
fi

# Determine the absolute project root path (one level up from this script in backend/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"

echo "=== Chirply AI Backend Service Installer ==="
echo "Project directory detected: $PROJECT_ROOT"

# Check if virtual environment exists
VENV_DIR="$PROJECT_ROOT/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found at $VENV_DIR."
    read -p "Enter the custom path to your python virtual environment (or press Enter to create one at $VENV_DIR): " CUSTOM_VENV
    if [ -z "$CUSTOM_VENV" ]; then
        echo "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        source "$VENV_DIR/bin/activate"
        echo "Installing requirements..."
        pip install -r "$PROJECT_ROOT/backend/requirements.txt"
    else
        VENV_DIR="$CUSTOM_VENV"
    fi
fi

# Define path configurations
TEMPLATE_FILE="$SCRIPT_DIR/chirply-backend.service.template"
TARGET_SERVICE_FILE="/etc/systemd/system/chirply-backend.service"

if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "Error: Template file not found at $TEMPLATE_FILE"
    exit 1
fi

echo "Generating systemd service configuration..."
# Replace placeholders and write to a temp file
TEMP_SERVICE=$(mktemp)
sed -e "s|{{WORKING_DIR}}|$PROJECT_ROOT|g" \
    -e "s|{{VENV_PATH}}|$VENV_DIR|g" \
    "$TEMPLATE_FILE" > "$TEMP_SERVICE"

# Copy the service file (requires root/sudo)
echo "Installing service file to $TARGET_SERVICE_FILE..."
sudo cp "$TEMP_SERVICE" "$TARGET_SERVICE_FILE"
rm "$TEMP_SERVICE"

# Make sure permissions are correct
sudo chmod 644 "$TARGET_SERVICE_FILE"

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service to run on boot
echo "Enabling chirply-backend service..."
sudo systemctl enable chirply-backend.service

# Start or restart the service
echo "Starting chirply-backend service..."
sudo systemctl restart chirply-backend.service

# Configure Firewall
if command -v ufw >/dev/null 2>&1; then
    if sudo ufw status | grep -q "Status: active"; then
        echo "Configuring firewall to allow port 8000..."
        sudo ufw allow 8000/tcp
    fi
fi

echo "============================================="
echo "Chirply AI Backend service installed successfully!"
echo "Check status by running: sudo systemctl status chirply-backend.service"
echo "View live logs by running: journalctl -u chirply-backend.service -f"
echo "============================================="
