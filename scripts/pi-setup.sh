#!/usr/bin/env bash

# Optional helper script for the Pi.
# Copy to the Pi and run: bash scripts/pi-setup.sh

set -e

sudo apt-get update
sudo apt-get install -y python3-pip python3-full python3-venv python3-pil python3-numpy python3-spidev python3-smbus python3-rpi.gpio

# Optional: install Waveshare library into a venv if WAVESHARE_PY_DIR is set.
# Example:
#   export WAVESHARE_PY_DIR=~/e-Paper/RaspberryPi_JetsonNano/python
#   bash scripts/pi-setup.sh
if [ -n "$WAVESHARE_PY_DIR" ]; then
  python3 -m venv ~/venvs/waveshare
  source ~/venvs/waveshare/bin/activate
  pip install --upgrade pip
  pip install "$WAVESHARE_PY_DIR" --no-deps
fi