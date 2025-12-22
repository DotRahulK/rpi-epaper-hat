# Raspberry Pi Zero 2 W + Waveshare 2.13" Touch e-Paper HAT

This project is a starter scaffold for driving a Waveshare 2.13" Touch e-Paper HAT from a Raspberry Pi Zero 2 W running Raspberry Pi OS (64-bit, desktop/full).

It includes a minimal Python app scaffold plus setup notes for the Waveshare e-Paper Python library.

## Hardware assumptions
- Raspberry Pi Zero 2 W
- Waveshare 2.13" Touch e-Paper HAT (SPI)

If your exact model differs (v2/v3, B/W vs tri-color, etc.), update the `EPD_MODEL` value in `src/config.py`.

## Raspberry Pi OS setup (on the Pi)
1) Enable SPI (and I2C if touch requires it):
   - `sudo raspi-config` -> Interface Options -> SPI -> Enable
2) Reboot the Pi.
3) Install system packages:
   - `sudo apt-get update`
   - `sudo apt-get install -y python3-pip python3-full python3-venv python3-pil python3-numpy python3-spidev python3-smbus python3-rpi.gpio`

## Waveshare e-Paper Python library
Waveshare distributes the Python drivers in their `e-Paper` repo. Clone it and install the Python module in a virtual environment (recommended for PEP 668 environments):

```
cd ~/Downloads
# from Waveshare GitHub: https://github.com/waveshare/e-Paper
# then:
cd e-Paper/RaspberryPi_JetsonNano/python

python3 -m venv ~/venvs/waveshare
source ~/venvs/waveshare/bin/activate
pip install --upgrade pip
pip install . --no-deps
```

Quick check:

```
python3 -c "from waveshare_epd import epd2in13; print('ok')"
```

If you must install system-wide, you can pass `--break-system-packages`, but it is not recommended.

## Run the sample
```
cd ~/path/to/rpi-epaper-hat
python3 src/main.py
```

## Notes
- Touch support may require additional configuration depending on your exact HAT revision.
- The sample uses a placeholder driver import and will prompt you if the Waveshare library is missing.

## Next steps
- Confirm your exact HAT model (e.g., 2.13inch Touch E-Paper HAT V2/V3) and update `src/config.py`.
- Replace the placeholder demo with your desired UI/content rendering logic.