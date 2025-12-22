# Project config
EPD_MODEL = "2in13_V4"  # V4/V3 drivers are correct for the Touch HAT revisions.

# Fallbacks to try if the display stays blank or init fails.
EPD_MODEL_CANDIDATES = [
    EPD_MODEL,
    "2in13_V3",
    "2in13_V2",
    "2in13",
]
