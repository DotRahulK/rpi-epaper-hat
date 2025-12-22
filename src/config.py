# Project config
EPD_MODEL = "2in13"  # SKU 20716 appears to match the 2.13" B/W 250x122 panel

# Fallbacks to try if the display stays blank or init fails.
EPD_MODEL_CANDIDATES = [
    EPD_MODEL,
    "2in13_V2",
    "2in13_V3",
    "2in13_V4",
]
