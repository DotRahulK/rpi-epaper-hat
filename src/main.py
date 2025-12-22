"""Simple demo entrypoint for the e-Paper HAT."""

from __future__ import annotations

from time import sleep

from config import EPD_MODEL
from epd_driver import load_epd_driver


def main() -> None:
    epd = load_epd_driver(EPD_MODEL)
    try:
        epd.init()
    except TypeError:
        # Some Waveshare drivers require a LUT argument for init().
        if hasattr(epd, "lut_full_update"):
            epd.init(epd.lut_full_update)
        elif hasattr(epd, "LUT_FULL_UPDATE"):
            epd.init(epd.LUT_FULL_UPDATE)
        else:
            raise
    epd.Clear(0xFF)
    # Placeholder: show nothing, then sleep so you can see it initialized.
    sleep(2)
    epd.sleep()


if __name__ == "__main__":
    main()
