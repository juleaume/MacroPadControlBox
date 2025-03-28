import os
import time
from math import cos, pi

import displayio
import terminalio
import usb_cdc
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from adafruit_macropad import MacroPad
from adafruit_hid.consumer_control_code import ConsumerControlCode

WHITE = 0xFFFFFF
BLACK = 0x000000


def angle_to_smooth_rgb(angle: float) -> int:
    phi = 2 * pi / 3
    red = int(0xFF * (cos(angle) + 1) / 2)
    green = int(0xFF * (cos(angle + phi) + 1) / 2)
    blue = int(0xFF * (cos(angle - phi) + 1) / 2)
    return (red << 16) + (green << 8) + blue


def angle_to_sharp_rgb(angle: float) -> int:
    red = max(int(0xFF * cos(angle)), 0)
    green = max(int(0xFF * cos(angle + 2 * pi / 3)), 0)
    blue = max(int(0xFF * cos(angle - 2 * pi / 3)), 0)
    return (red << 16) + (green << 8) + blue


class Console(MacroPad):  # type: ignore
    def __init__(self) -> None:
        super().__init__()
        self.pixels.brightness = 255
        self.angle_to_rgb = angle_to_smooth_rgb
        self.actions = [None] * 12
        self.title = "RUN PROGRAM"
        self.group = displayio.Group()
        for key_index in range(12):
            x = key_index % 3
            y = key_index // 3
            self.group.append(
                label.Label(
                    terminalio.FONT,
                    text="",
                    color=WHITE,
                    anchored_position=(
                        (self.display.width - 1) * x / 2,
                        self.display.height - 1 - (3 - y) * 12,
                    ),
                    anchor_point=(x / 2, 1.0),
                )
            )
        self.group.append(Rect(0, 0, self.display.width, 12, fill=WHITE))
        self.group.append(
            label.Label(
                terminalio.FONT,
                text=self.title,
                color=BLACK,
                anchored_position=(self.display.width // 2, -2),
                anchor_point=(0.5, -0.2),
            )
        )
        self.display.root_group = self.group

    def _reset(self) -> None:
        for i, _ in enumerate(self.group):
            self.group[i].text = ""
        self.group[-1].text = self.title
        for i, _ in enumerate(self.pixels):
            self.pixels[i] = 0

    def jingle(self):
        tone = 1760
        for _ in range(3):
            self.play_tone(tone, 0.1)
            tone /= 2

    def set_screen(self, payload: bytes) -> bool:
        print(f"Received {payload}")
        if not payload.startswith(b"\x05"):
            return False
        payload = payload[1:]
        try:
            items = payload.decode().split(",")
            title, *items = items
            self.group[-1].text = title
            for i, item in enumerate(items):
                self.group[i].text = item
            return True
        except Exception as e:
            print(f"Something went wrong: {e}")
            return False

    def init_connection(self) -> bool:
        print("init connection...")
        dots = ""
        indicator = "+"
        while True:
            size = usb_cdc.data.in_waiting
            if size:
                return self.set_screen(usb_cdc.data.read(size))
            else:
                self.group[3].text = f"connecting{dots}"
                if dots != "...":
                    dots += "."
                else:
                    dots = ""
                self.group[5].text = indicator
                if indicator == "+":
                    indicator = "x"
                else:
                    indicator = "+"
            time.sleep(0.5)

    def run(self) -> None:
        tone = 440
        for _ in range(3):
            self.play_tone(tone, 0.1)
            tone *= 2
        color_angle = 0.0
        _down_key = None
        last_encoder = self.encoder
        last_encoder_switch = self.encoder_switch
        while True:
            encoder = self.encoder
            # COLORS
            for i, _ in enumerate(self.pixels):
                if _down_key == i:
                    self.pixels[i] = self.angle_to_rgb((color_angle + pi + (i // 3)) % (2 * pi))
                else:
                    self.pixels[i] = self.angle_to_rgb((color_angle + (i // 3)) % (2 * pi))
            if color_angle > 2 * pi:
                color_angle = 0.0
            else:
                color_angle += pi / 36
            # ENCODER
            if self.encoder_switch and not last_encoder_switch:
                usb_cdc.data.write(b".")
            last_encoder_switch = self.encoder_switch
            if encoder != last_encoder:
                if encoder - last_encoder > 0:
                    usb_cdc.data.write(b">")
                else:
                    usb_cdc.data.write(b"<")
                last_encoder = encoder
            # KEYS
            events = self.keys.events.get()
            if events is not None:
                if not events.pressed:  # key release
                    usb_cdc.data.write(events.key_number.to_bytes(1))
                    _down_key = None
                    self.group[events.key_number].background_color = BLACK
                    self.group[events.key_number].color = WHITE
                else:
                    self.group[events.key_number].background_color = WHITE
                    self.group[events.key_number].color = BLACK
            if usb_cdc.data.in_waiting:
                runtime_payload = usb_cdc.data.read(usb_cdc.data.in_waiting)
                print(f"incoming data: {runtime_payload}")
                if runtime_payload == b"\x18":
                    self._reset()
                    self.jingle()
                    return True
                elif runtime_payload == b"\x04":
                    self._reset()
                    self.jingle()
                    return False
                elif runtime_payload.startswith(b"\x05"):
                    self.beep()
                    if not self.set_screen(runtime_payload):
                        self._reset()
                        self.jingle()
                        return True
                elif runtime_payload == b"\x07":
                    self.beep()
            time.sleep(0.01)

    def beep(self) -> None:
        self.play_tone(440, 0.1)


if __name__ == "__main__":
    _c = Console()
    while True:
        while not _c.init_connection():
            time.sleep(0.1)
        if _c.run():
            continue
        else:
            break
    print("bye-bye")
