"""Simple demo entrypoint for the e-Paper HAT."""

from __future__ import annotations

from time import sleep

from PIL import Image, ImageDraw, ImageFont

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

    image = Image.new("1", (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.rectangle((0, 0, epd.width - 1, epd.height - 1), outline=0)
    draw.text((10, 10), "Hello, Waveshare!", font=font, fill=0)

    epd.display(epd.getbuffer(image))
    sleep(2)
    epd.sleep()


if __name__ == "__main__":
    main()
