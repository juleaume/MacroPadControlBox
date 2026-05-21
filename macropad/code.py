import time
from math import cos, pi

import displayio
import terminalio
import usb_cdc
import usb_hid
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
from adafruit_macropad import MacroPad
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

WHITE = 0xFFFFFF
BLACK = 0x000000


keyboard = Keyboard(usb_hid.devices)
consumer = ConsumerControl(usb_hid.devices)


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
        self.key_commands = dict()
        self.ctrl_commands = dict()
        self._serial = usb_cdc.data
        if self._serial is None:
            raise RuntimeError("Failed to open serial connection")

    @property
    def serial(self) -> usb_cdc.Serial:
        assert self._serial is not None
        return self._serial

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
        if not payload.startswith(b"\x01"):
            return False
        payload = payload[1:]
        try:
            self.key_commands = dict()
            self.ctrl_commands = dict()
            title, payload = payload.decode().split("\x02")
            self.group[-1].text = title
            items = payload.split("\x17")
            for i, item in enumerate(items):
                if "\x11" in item:
                    command_title, *keys = item.split("\x11")
                    self.group[i].text = command_title
                    self.key_commands[i] = keys
                elif "\x12" in item:
                    command_title, key = item.split("\x12")
                    self.group[i].text = command_title
                    self.ctrl_commands[i] = key
                else:
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
            size = self.serial.in_waiting
            if size:
                return self.set_screen(self.serial.read(size))
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

    def run(self) -> bool:
        # tone = 440
        # for _ in range(3):
        #     self.play_tone(tone, 0.1)
        #     tone *= 2
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
                consumer.send(ConsumerControlCode.PLAY_PAUSE)
            last_encoder_switch = self.encoder_switch
            if encoder != last_encoder:
                if encoder - last_encoder > 0:
                    consumer.send(ConsumerControlCode.VOLUME_INCREMENT)
                else:
                    consumer.send(ConsumerControlCode.VOLUME_DECREMENT)
                last_encoder = encoder
            # KEYS
            events = self.keys.events.get()
            if events is not None:
                key_group = self.group[events.key_number]
                if not events.pressed:  # key release
                    if self.key_commands.get(events.key_number) is not None:
                        keyboard.send(*[getattr(Keycode, _k) for _k in self.key_commands[events.key_number]])
                    elif self.ctrl_commands.get(events.key_number) is not None:
                        consumer.send(getattr(ConsumerControlCode, self.ctrl_commands[events.key_number]))
                    else:
                        self.serial.write(events.key_number.to_bytes(1))
                    _down_key = None
                    key_group.background_color = BLACK
                    key_group.color = WHITE
                else:
                    key_group.background_color = WHITE
                    key_group.color = BLACK
            if self.serial.in_waiting:
                runtime_payload = self.serial.read(self.serial.in_waiting)
                print(f"incoming data: {runtime_payload}")
                if runtime_payload == b"\x18":
                    self._reset()
                    # self.jingle()
                    return True
                elif runtime_payload == b"\x04":
                    self._reset()
                    # self.jingle()
                    return False
                elif runtime_payload.startswith(b"\x01"):
                    # self.beep()
                    if not self.set_screen(runtime_payload):
                        self._reset()
                        # self.jingle()
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
