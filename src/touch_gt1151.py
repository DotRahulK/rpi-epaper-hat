from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import time

try:
    import RPi.GPIO as GPIO
except ImportError as exc:  # pragma: no cover - runs on the Pi.
    raise ImportError("RPi.GPIO is required for GT1151 touch") from exc

try:
    from smbus import SMBus
except ImportError as exc:  # pragma: no cover - runs on the Pi.
    raise ImportError("python3-smbus is required for GT1151 touch") from exc


@dataclass(frozen=True)
class TouchPoint:
    x: int
    y: int
    size: int
    track_id: int


class GT1151:
    def __init__(
        self,
        bus: int = 1,
        address: int = 0x14,
        reset_pin: int = 22,
        int_pin: int = 27,
        poll_ms: int = 20,
    ) -> None:
        self._bus = SMBus(bus)
        self._address = address
        self._reset_pin = reset_pin
        self._int_pin = int_pin
        self._poll_ms = poll_ms
        self._gpio_ready = False
        self._setup_gpio()

    def _setup_gpio(self) -> None:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._reset_pin, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(self._int_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._gpio_ready = True

    def close(self) -> None:
        self._bus.close()
        if self._gpio_ready:
            GPIO.cleanup((self._reset_pin, self._int_pin))
            self._gpio_ready = False

    def reset(self) -> None:
        GPIO.output(self._reset_pin, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(self._reset_pin, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(self._reset_pin, GPIO.HIGH)
        time.sleep(0.1)

    def _write_reg(self, reg: int, payload: bytes) -> None:
        data = [reg & 0xFF] + list(payload)
        self._bus.write_i2c_block_data(self._address, (reg >> 8) & 0xFF, data)

    def _read_reg(self, reg: int, length: int) -> List[int]:
        self._bus.write_i2c_block_data(self._address, (reg >> 8) & 0xFF, [reg & 0xFF])
        return [self._bus.read_byte(self._address) for _ in range(length)]

    def read_version(self) -> str:
        data = self._read_reg(0x8140, 4)
        return bytes(data).decode("ascii", errors="replace")

    def init(self) -> str:
        self.reset()
        return self.read_version()

    def read_points(self) -> Optional[List[TouchPoint]]:
        status = self._read_reg(0x814E, 1)[0]
        if (status & 0x80) == 0x00:
            self._write_reg(0x814E, b"\x00")
            time.sleep(self._poll_ms / 1000.0)
            return None

        count = status & 0x0F
        if count < 1 or count > 5:
            self._write_reg(0x814E, b"\x00")
            return None

        data = self._read_reg(0x814F, count * 8)
        self._write_reg(0x814E, b"\x00")

        points: List[TouchPoint] = []
        for i in range(count):
            base = i * 8
            track_id = data[base]
            x = (data[base + 2] << 8) | data[base + 1]
            y = (data[base + 4] << 8) | data[base + 3]
            size = (data[base + 6] << 8) | data[base + 5]
            points.append(TouchPoint(x=x, y=y, size=size, track_id=track_id))
        return points
