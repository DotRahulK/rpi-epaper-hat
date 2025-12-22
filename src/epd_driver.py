"""Minimal wrapper for Waveshare e-Paper drivers.

This file keeps the import contained so we can print a clear message when
the Waveshare Python library is not installed on the Pi.
"""

from __future__ import annotations

from typing import Any


def load_epd_driver(model: str) -> Any:
    try:
        # Waveshare e-Paper library uses a module naming scheme like:
        # from waveshare_epd import epd2in13
        module_name = f"waveshare_epd.epd{model}"
        module = __import__(module_name, fromlist=["EPD"])
        return module.EPD()
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Waveshare e-Paper Python library not found. "
            "Install it from the Waveshare e-Paper repo before running."
        ) from exc