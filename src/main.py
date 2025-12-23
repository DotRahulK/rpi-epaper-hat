"""Simple demo entrypoint for the e-Paper HAT."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from time import sleep
import os
import queue
import threading
import time
from typing import Iterable, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps

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


def _fit_album_art(art: Image.Image, size: int) -> Image.Image:
    art = art.convert("L")
    art = ImageOps.fit(art, (size, size), method=Image.LANCZOS)
    return art.convert("1")


def _render_layout(
    epd,
    title: str,
    artist: str,
    art: Optional[Image.Image],
    is_playing: bool,
) -> Tuple[Image.Image, Iterable[Component], bool]:
    image, width, height, needs_rotate = _landscape_image(epd)
    draw = ImageDraw.Draw(image)

    margin = 4
    image_size = height - 2 * margin
    left_x0 = margin
    left_y0 = margin
    left_x1 = left_x0 + image_size
    left_y1 = left_y0 + image_size

    if art:
        art = _fit_album_art(art, image_size)
        image.paste(art, (left_x0, left_y0))
    else:
        # Placeholder square image.
        draw.rectangle((left_x0, left_y0, left_x1, left_y1), outline=0, width=1)
        draw.line((left_x0, left_y0, left_x1, left_y1), fill=0, width=1)
        draw.line((left_x0, left_y1, left_x1, left_y0), fill=0, width=1)

    right_x0 = left_x1 + margin
    right_x1 = width - margin
    right_width = right_x1 - right_x0

    title_font = _load_font(18)
    artist_font = _load_font(12)
    title = _fit_text(draw, title, title_font, right_width)
    artist = _fit_text(draw, artist, artist_font, right_width)

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

    def _draw_play_symbol(box: Tuple[int, int, int, int]) -> None:
        x0, y0, x1, y1 = box
        pad_x = int((x1 - x0) * 0.22)
        pad_y = int((y1 - y0) * 0.2)
        points = [
            (x0 + pad_x, y0 + pad_y),
            (x1 - pad_x, (y0 + y1) // 2),
            (x0 + pad_x, y1 - pad_y),
        ]
        draw.polygon(points, fill=0)

    def _draw_pause_symbol(box: Tuple[int, int, int, int]) -> None:
        x0, y0, x1, y1 = box
        pad_x = int((x1 - x0) * 0.22)
        pad_y = int((y1 - y0) * 0.2)
        bar_width = max(1, int((x1 - x0) * 0.12))
        gap = max(1, int((x1 - x0) * 0.08))
        left_x0 = (x0 + x1 - (2 * bar_width + gap)) // 2
        right_x0 = left_x0 + bar_width + gap
        draw.rectangle(
            (left_x0, y0 + pad_y, left_x0 + bar_width, y1 - pad_y), fill=0
        )
        draw.rectangle(
            (right_x0, y0 + pad_y, right_x0 + bar_width, y1 - pad_y), fill=0
        )

    def _draw_next_symbol(box: Tuple[int, int, int, int]) -> None:
        x0, y0, x1, y1 = box
        pad_x = int((x1 - x0) * 0.18)
        pad_y = int((y1 - y0) * 0.2)
        mid_x = (x0 + x1) // 2
        left_triangle = [
            (x0 + pad_x, y0 + pad_y),
            (mid_x, (y0 + y1) // 2),
            (x0 + pad_x, y1 - pad_y),
        ]
        right_triangle = [
            (mid_x, y0 + pad_y),
            (x1 - pad_x, (y0 + y1) // 2),
            (mid_x, y1 - pad_y),
        ]
        draw.polygon(left_triangle, fill=0)
        draw.polygon(right_triangle, fill=0)

    def _draw_like_symbol(box: Tuple[int, int, int, int]) -> None:
        x0, y0, x1, y1 = box
        size = min(x1 - x0, y1 - y0)
        radius = int(size * 0.28)
        center_x = (x0 + x1) // 2
        center_y = (y0 + y1) // 2
        circle_box = (
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
        )
        draw.ellipse(circle_box, outline=0, width=max(1, int(size * 0.05)))
        plus_len = int(radius * 0.9)
        draw.line(
            (center_x - plus_len, center_y, center_x + plus_len, center_y),
            fill=0,
            width=max(1, int(size * 0.05)),
        )
        draw.line(
            (center_x, center_y - plus_len, center_x, center_y + plus_len),
            fill=0,
            width=max(1, int(size * 0.05)),
        )

    if is_playing:
        _draw_pause_symbol(play_box)
    else:
        _draw_play_symbol(play_box)
    _draw_next_symbol(next_box)
    _draw_like_symbol(like_box)

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
    components: Iterable[Component],
    width: int,
    height: int,
    needs_rotate: bool,
    event_queue: "queue.Queue[str]",
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
                    event_queue.put(component.name)
                    break
            else:
                pass



def _touch_loop_gt1151(
    components: Iterable[Component],
    width: int,
    height: int,
    needs_rotate: bool,
    event_queue: "queue.Queue[str]",
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
                    event_queue.put(component.name)
                    break
            else:
                pass
    except KeyboardInterrupt:
        pass
    finally:
        gt.close()


def _run_touch_loop(
    components: Iterable[Component],
    width: int,
    height: int,
    needs_rotate: bool,
    event_queue: "queue.Queue[str]",
) -> None:
    if TOUCH_BACKEND.lower() == "gt1151":
        _touch_loop_gt1151(components, width, height, needs_rotate, event_queue)
    else:
        _touch_loop_evdev(components, width, height, needs_rotate, event_queue)


def _start_touch_loop(
    components: Iterable[Component], width: int, height: int, needs_rotate: bool
) -> "queue.Queue[str]":
    event_queue: "queue.Queue[str]" = queue.Queue()
    thread = threading.Thread(
        target=_run_touch_loop,
        args=(components, width, height, needs_rotate, event_queue),
        daemon=True,
    )
    thread.start()
    return event_queue


def main() -> None:
    try:
        from spotify_client import SpotifyController
    except ImportError as exc:
        print(f"Spotify disabled: {exc}")
        return

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

    try:
        spotify = SpotifyController()
    except Exception as exc:
        print(f"Spotify disabled: {exc}")
        return

    title = "Waiting for Spotify..."
    artist = "Open Spotify on a device"
    image, components, needs_rotate = _render_layout(
        epd, title, artist, art=None, is_playing=False
    )
    if needs_rotate:
        image = image.rotate(90, expand=True)
    epd.display(epd.getbuffer(image))
    try:
        event_queue = _start_touch_loop(components, image.width, image.height, needs_rotate)
        poll_sec = float(os.environ.get("SPOTIFY_POLL_SEC", "5"))
        debounce_sec = float(os.environ.get("TOUCH_DEBOUNCE_SEC", "0.35"))
        last_action: dict[str, float] = {}
        last_render_key: Optional[Tuple[str, bool, str, str]] = None
        current_track_id: Optional[str] = None
        current_art: Optional[Image.Image] = None
        next_poll = 0.0

        while True:
            now = time.monotonic()
            while True:
                try:
                    action = event_queue.get_nowait()
                except queue.Empty:
                    break
                last_time = last_action.get(action, 0.0)
                if now - last_time < debounce_sec:
                    continue
                last_action[action] = now
                if action == "Play/Pause":
                    spotify.toggle_play_pause()
                elif action == "Next":
                    spotify.next_track()
                elif action == "Like":
                    spotify.like_current()
                last_render_key = None

            if now >= next_poll:
                next_poll = now + poll_sec
                track = spotify.current_track()
                if track:
                    if track.track_id != current_track_id:
                        art_bytes = spotify.get_album_art(track.track_id, track.art_url)
                        if art_bytes:
                            try:
                                current_art = Image.open(BytesIO(art_bytes))
                            except OSError:
                                current_art = None
                        else:
                            current_art = None
                        current_track_id = track.track_id
                    title = track.title or "Unknown title"
                    artist = track.artist or "Unknown artist"
                    render_key = (track.track_id, track.is_playing, title, artist)
                    is_playing = track.is_playing
                else:
                    current_track_id = None
                    current_art = None
                    title = "No active device"
                    artist = "Open Spotify on a device"
                    render_key = ("none", False, title, artist)
                    is_playing = False

                if render_key != last_render_key:
                    image, _, _ = _render_layout(
                        epd, title, artist, current_art, is_playing
                    )
                    if needs_rotate:
                        image = image.rotate(90, expand=True)
                    epd.display(epd.getbuffer(image))
                    last_render_key = render_key

            sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        sleep(1)
        epd.sleep()


if __name__ == "__main__":
    main()





