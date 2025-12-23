# Project config
EPD_MODEL = "2in13_V4"  # V4/V3 drivers are correct for the Touch HAT revisions.

# Fallbacks to try if the display stays blank or init fails.
EPD_MODEL_CANDIDATES = [
    EPD_MODEL,
    "2in13_V3",
    "2in13_V2",
    "2in13",
]

# Touch config
TOUCH_BACKEND = "gt1151"  # Use "evdev" to read from /dev/input instead.
TOUCH_I2C_BUS = 1
TOUCH_I2C_ADDRESS = 0x14
TOUCH_RESET_PIN = 22
TOUCH_INT_PIN = 27
TOUCH_POLL_MS = 20
# Set ranges if raw coords don't match the display size.
TOUCH_X_MIN = None
TOUCH_X_MAX = None
TOUCH_Y_MIN = None
TOUCH_Y_MAX = None

