"""Simple demo entrypoint for the e-Paper HAT."""

from __future__ import annotations

from time import sleep

from config import EPD_MODEL
from epd_driver import load_epd_driver


def main() -> None:
    epd = load_epd_driver(EPD_MODEL)
    epd.init()
    epd.Clear(0xFF)
    # Placeholder: show nothing, then sleep so you can see it initialized.
    sleep(2)
    epd.sleep()


if __name__ == "__main__":
    main()