"""Simple demo entrypoint for the e-Paper HAT."""

from __future__ import annotations

from dataclasses import dataclass
from time import sleep
import os
from typing import Iterable, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from config import (
    EPD_MODEL_CANDIDATES,
    TOUCH_BACKEND,
    TOUCH_I2C_ADDRESS,
    TOUCH_I2C_BUS,
    TOUCH_INT_PIN,
    TOUCH_POLL_MS,
    TOUCH_RESET_PIN,
    TOUCH_X_MAX,
    TOUCH_X_MIN,
    TOUCH_Y_MAX,
    TOUCH_Y_MIN,
)
from epd_driver import _load_epd_driver_candidates


@dataclass(frozen=True)
class Component:
    name: str
    box: Tuple[int, int, int, int]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size
        )
    except OSError:
        return ImageFont.load_default()


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text
    ellipsis = "..."
    trimmed = text
    while trimmed:
        trimmed = trimmed[:-1]
        candidate = f"{trimmed}{ellipsis}"
        if draw.textlength(candidate, font=font) <= max_width:
            return candidate
    return ellipsis


def _landscape_image(epd) -> Tuple[Image.Image, int, int, bool]:
    if epd.width >= epd.height:
        return Image.new("1", (epd.width, epd.height), 255), epd.width, epd.height, False
    return Image.new("1", (epd.height, epd.width), 255), epd.height, epd.width, True


def _render_layout(epd, is_playing: bool) -> Tuple[Image.Image, Iterable[Component], bool]:
    image, width, height, needs_rotate = _landscape_image(epd)
    draw = ImageDraw.Draw(image)

    margin = 4
    image_size = height - 2 * margin
    left_x0 = margin
    left_y0 = margin
    left_x1 = left_x0 + image_size
    left_y1 = left_y0 + image_size

    # Placeholder square image.
    draw.rectangle((left_x0, left_y0, left_x1, left_y1), outline=0, width=1)
    draw.line((left_x0, left_y0, left_x1, left_y1), fill=0, width=1)
    draw.line((left_x0, left_y1, left_x1, left_y0), fill=0, width=1)

    right_x0 = left_x1 + margin
    right_x1 = width - margin
    right_width = right_x1 - right_x0

    title_font = _load_font(18)
    artist_font = _load_font(12)
    title = _fit_text(draw, "Your Song Title Goes Here", title_font, right_width)
    artist = _fit_text(draw, "Artist Name", artist_font, right_width)

    draw.text((right_x0, margin), title, font=title_font, fill=0)
    draw.text((right_x0, margin + 22), artist, font=artist_font, fill=0)

    button_gap = 6
    buttons_top = margin + 44
    buttons_bottom = height - margin
    button_height = max(1, buttons_bottom - buttons_top)
    button_width = int((right_width - 2 * button_gap) / 3)

    play_box = (
        right_x0,
        buttons_top,
        right_x0 + button_width,
        buttons_top + button_height,
    )
    next_box = (
        right_x0 + button_width + button_gap,
        buttons_top,
        right_x0 + 2 * button_width + button_gap,
        buttons_top + button_height,
    )
    like_box = (
        right_x0 + 2 * (button_width + button_gap),
        buttons_top,
        right_x0 + 3 * button_width + 2 * button_gap,
        buttons_top + button_height,
    )

    symbol_font = _load_font(max(12, int(button_height * 0.7)))
    play_label = "||" if is_playing else ">"
    for label, box in [(play_label, play_box), (">>", next_box), ("O+", like_box)]:
        text = _fit_text(draw, label, symbol_font, button_width)
        text_width = draw.textlength(text, font=symbol_font)
        text_height = symbol_font.getbbox(text)[3]
        text_x = box[0] + (button_width - text_width) / 2
        text_y = box[1] + (button_height - text_height) / 2
        draw.text((text_x, text_y), text, font=symbol_font, fill=0)

    components = [
        Component("Art", (left_x0, left_y0, left_x1, left_y1)),
        Component("Title", (right_x0, margin, right_x1, margin + 20)),
        Component("Artist", (right_x0, margin + 22, right_x1, margin + 38)),
        Component("Play/Pause", play_box),
        Component("Next", next_box),
        Component("Like", like_box),
    ]

    return image, components, needs_rotate


def _find_touch_device() -> Optional[str]:
    import glob
    env_path = os.environ.get("TOUCH_DEVICE")
    if env_path:
        return env_path
    matches = glob.glob("/dev/input/by-path/*-event-touchscreen")
    if matches:
        return matches[0]
    matches = glob.glob("/dev/input/by-path/*i2c*-event")
    if matches:
        return matches[0]
    matches = glob.glob("/dev/input/event*")
    return matches[0] if matches else None


def _map_axis(value: int, min_value: Optional[int], max_value: Optional[int], size: int) -> int:
    if min_value is None or max_value is None or max_value <= min_value:
        return value
    value = max(min_value, min(max_value, value))
    return int((value - min_value) * (size - 1) / (max_value - min_value))


def _touch_loop_evdev(
    components: Iterable[Component], width: int, height: int, needs_rotate: bool
) -> None:
    try:
        from evdev import InputDevice, ecodes
    except ImportError:
        print("Touch input disabled: install python3-evdev.")
        return

    device_path = _find_touch_device()
    if device_path is None:
        print("Touch input disabled: no /dev/input device found.")
        return

    dev = InputDevice(device_path)
    abs_caps = dev.capabilities().get(ecodes.EV_ABS)
    abs_x = dev.absinfo(ecodes.ABS_X) if abs_caps else None
    abs_y = dev.absinfo(ecodes.ABS_Y) if abs_caps else None
    abs_mx = dev.absinfo(ecodes.ABS_MT_POSITION_X) if abs_caps else None
    abs_my = dev.absinfo(ecodes.ABS_MT_POSITION_Y) if abs_caps else None

    x = 0
    y = 0
    touching = False
    debug_raw = os.environ.get("DEBUG_TOUCH") == "1"
    print(f"Listening for touches on {device_path} ...")
    for event in dev.read_loop():
        if debug_raw:
            print(event)
        if event.type == ecodes.EV_ABS:
            if event.code == ecodes.ABS_MT_POSITION_X and abs_mx:
                x = _map_axis(event.value, abs_mx.min, abs_mx.max, width)
            elif event.code == ecodes.ABS_MT_POSITION_Y and abs_my:
                y = _map_axis(event.value, abs_my.min, abs_my.max, height)
            elif event.code == ecodes.ABS_X and abs_x:
                x = _map_axis(event.value, abs_x.min, abs_x.max, width)
            elif event.code == ecodes.ABS_Y and abs_y:
                y = _map_axis(event.value, abs_y.min, abs_y.max, height)
            elif event.code == ecodes.ABS_MT_TRACKING_ID:
                touching = event.value >= 0
        elif event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH:
            touching = event.value == 1
        elif event.type == ecodes.EV_SYN and event.code == ecodes.SYN_REPORT:
            if not touching:
                continue
            touch_x, touch_y = x, y
            if needs_rotate and (abs_x or abs_mx) and (abs_y or abs_my):
                # Rotate raw portrait touch coords into landscape coordinates.
                touch_x, touch_y = y, (width - 1 - x)
            for component in components:
                x0, y0, x1, y1 = component.box
                if x0 <= touch_x <= x1 and y0 <= touch_y <= y1:
                    print(f"Touched: {component.name} ({touch_x}, {touch_y})")
                    break
            else:
                print(f"Touched: background ({touch_x}, {touch_y})")



def _touch_loop_gt1151(
    components: Iterable[Component], width: int, height: int, needs_rotate: bool
) -> None:
    try:
        from touch_gt1151 import GT1151
    except ImportError as exc:
        print(f"Touch input disabled: {exc}")
        return

    gt = GT1151(
        bus=TOUCH_I2C_BUS,
        address=TOUCH_I2C_ADDRESS,
        reset_pin=TOUCH_RESET_PIN,
        int_pin=TOUCH_INT_PIN,
        poll_ms=TOUCH_POLL_MS,
    )
    try:
        version = gt.init()
        print(f"GT1151 init ok: {version}")
    except Exception as exc:
        gt.close()
        print(f"Touch input disabled: GT1151 init failed: {exc}")
        return

    try:
        while True:
            points = gt.read_points()
            if not points:
                continue
            touch_x = _map_axis(points[0].x, TOUCH_X_MIN, TOUCH_X_MAX, width)
            touch_y = _map_axis(points[0].y, TOUCH_Y_MIN, TOUCH_Y_MAX, height)
            if needs_rotate:
                touch_x, touch_y = touch_y, (width - 1 - touch_x)
            for component in components:
                x0, y0, x1, y1 = component.box
                if x0 <= touch_x <= x1 and y0 <= touch_y <= y1:
                    print(f"Touched: {component.name} ({touch_x}, {touch_y})")
                    break
            else:
                print(f"Touched: background ({touch_x}, {touch_y})")
    except KeyboardInterrupt:
        pass
    finally:
        gt.close()


def _run_touch_loop(
    components: Iterable[Component], width: int, height: int, needs_rotate: bool
) -> None:
    if TOUCH_BACKEND.lower() == "gt1151":
        _touch_loop_gt1151(components, width, height, needs_rotate)
    else:
        _touch_loop_evdev(components, width, height, needs_rotate)


def main() -> None:
    epd = _load_epd_driver_candidates(EPD_MODEL_CANDIDATES)
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

    image, components, needs_rotate = _render_layout(epd, is_playing=False)
    if needs_rotate:
        image = image.rotate(90, expand=True)
    epd.display(epd.getbuffer(image))
    try:
        _run_touch_loop(components, image.width, image.height, needs_rotate)
    except KeyboardInterrupt:
        pass
    finally:
        sleep(1)
        epd.sleep()


if __name__ == "__main__":
    main()





