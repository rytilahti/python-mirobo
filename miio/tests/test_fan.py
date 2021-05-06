from unittest import TestCase

import pytest

from miio import Fan, FanP5
from miio.fan import (
    MODEL_FAN_P5,
    MODEL_FAN_SA1,
    MODEL_FAN_V2,
    MODEL_FAN_V3,
    FanException,
    FanStatus,
    FanStatusP5,
    LedBrightness,
    MoveDirection,
    OperationMode,
)

from .dummies import DummyDevice


class DummyFanV2(DummyDevice, Fan):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_FAN_V2
        # This example response is just a guess. Please update!
        self.state = {
            "temp_dec": 232,
            "humidity": 46,
            "angle": 118,
            "speed": 298,
            "poweroff_time": 0,
            "power": "on",
            "ac_power": "off",
            "battery": 98,
            "angle_enable": "off",
            "speed_level": 1,
            "natural_level": 0,
            "child_lock": "off",
            "buzzer": "on",
            "led_b": 1,
            "led": "on",
            "natural_enable": None,
            "use_time": 0,
            "bat_charge": "complete",
            "bat_state": None,
            "button_pressed": "speed",
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_speed_level": lambda x: self._set_state("speed_level", x),
            "set_natural_level": lambda x: self._set_state("natural_level", x),
            "set_move": lambda x: True,
            "set_angle": lambda x: self._set_state("angle", x),
            "set_angle_enable": lambda x: self._set_state("angle_enable", x),
            "set_led_b": lambda x: self._set_state("led_b", x),
            "set_led": lambda x: self._set_state("led", x),
            "set_buzzer": lambda x: self._set_state("buzzer", x),
            "set_child_lock": lambda x: self._set_state("child_lock", x),
            "set_poweroff_time": lambda x: self._set_state("poweroff_time", x),
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def fanv2(request):
    request.cls.device = DummyFanV2()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("fanv2")
class TestFanV2(TestCase):
    def is_on(self):
        return self.device.status().is_on

    def state(self):
        return self.device.status()

    def test_on(self):
        self.device.off()  # ensure off
        assert self.is_on() is False

        self.device.on()
        assert self.is_on() is True

    def test_off(self):
        self.device.on()  # ensure on
        assert self.is_on() is True

        self.device.off()
        assert self.is_on() is False

    def test_status(self):
        self.device._reset_state()

        assert repr(self.state()) == repr(FanStatus(self.device.start_state))

        assert self.is_on() is True
        assert self.state().temperature == self.device.start_state["temp_dec"] / 10.0
        assert self.state().humidity == self.device.start_state["humidity"]
        assert self.state().angle == self.device.start_state["angle"]
        assert self.state().speed == self.device.start_state["speed"]
        assert (
            self.state().delay_off_countdown == self.device.start_state["poweroff_time"]
        )
        assert self.state().ac_power is (self.device.start_state["ac_power"] == "on")
        assert self.state().battery == self.device.start_state["battery"]
        assert self.state().oscillate is (
            self.device.start_state["angle_enable"] == "on"
        )
        assert self.state().direct_speed == self.device.start_state["speed_level"]
        assert self.state().natural_speed == self.device.start_state["natural_level"]
        assert self.state().child_lock is (
            self.device.start_state["child_lock"] == "on"
        )
        assert self.state().buzzer is (self.device.start_state["buzzer"] == "on")
        assert self.state().led_brightness == LedBrightness(
            self.device.start_state["led_b"]
        )
        assert self.state().led is (self.device.start_state["led"] == "on")
        assert self.state().use_time == self.device.start_state["use_time"]
        assert self.state().battery_charge == self.device.start_state["bat_charge"]
        assert self.state().battery_state == self.device.start_state["bat_state"]
        assert self.state().button_pressed == self.device.start_state["button_pressed"]

    def test_status_without_led_brightness(self):
        self.device._reset_state()

        self.device.state["led_b"] = None
        assert self.state().led_brightness is None

    def test_status_without_battery_charge(self):
        self.device._reset_state()

        self.device.state["bat_charge"] = None
        assert self.state().battery_charge is None

    def test_status_without_battery_state(self):
        self.device._reset_state()

        self.device.state["bat_state"] = None
        assert self.state().battery_state is None

    def test_status_without_button_pressed(self):
        self.device._reset_state()

        self.device.state["button_pressed"] = None
        assert self.state().button_pressed is None

    def test_set_led(self):
        def led():
            return self.device.status().led

        self.device.set_led(True)
        assert led() is True

        self.device.set_led(False)
        assert led() is False

    def test_set_direct_speed(self):
        def direct_speed():
            return self.device.status().direct_speed

        self.device.set_direct_speed(0)
        assert direct_speed() == 0
        self.device.set_direct_speed(1)
        assert direct_speed() == 1
        self.device.set_direct_speed(100)
        assert direct_speed() == 100

        with pytest.raises(FanException):
            self.device.set_direct_speed(-1)

        with pytest.raises(FanException):
            self.device.set_direct_speed(101)

    def test_set_rotate(self):
        """The method is open-loop.

        The new state cannot be retrieved.
        """
        self.device.set_rotate(MoveDirection.Left)
        self.device.set_rotate(MoveDirection.Right)

    def test_set_angle(self):
        """This test doesn't implement the real behaviour of the device may be.

        The property "angle" doesn't provide the current setting. It's a measurement of
        the current position probably.
        """

        def angle():
            return self.device.status().angle

        self.device.set_angle(0)  # TODO: Is this value allowed?
        assert angle() == 0
        self.device.set_angle(1)  # TODO: Is this value allowed?
        assert angle() == 1
        self.device.set_angle(30)
        assert angle() == 30
        self.device.set_angle(60)
        assert angle() == 60
        self.device.set_angle(90)
        assert angle() == 90
        self.device.set_angle(120)
        assert angle() == 120

        with pytest.raises(FanException):
            self.device.set_angle(-1)

        with pytest.raises(FanException):
            self.device.set_angle(121)

    def test_set_oscillate(self):
        def oscillate():
            return self.device.status().oscillate

        self.device.set_oscillate(True)
        assert oscillate() is True

        self.device.set_oscillate(False)
        assert oscillate() is False

    def test_set_led_brightness(self):
        def led_brightness():
            return self.device.status().led_brightness

        self.device.set_led_brightness(LedBrightness.Bright)
        assert led_brightness() == LedBrightness.Bright

        self.device.set_led_brightness(LedBrightness.Dim)
        assert led_brightness() == LedBrightness.Dim

        self.device.set_led_brightness(LedBrightness.Off)
        assert led_brightness() == LedBrightness.Off

    def test_set_buzzer(self):
        def buzzer():
            return self.device.status().buzzer

        self.device.set_buzzer(True)
        assert buzzer() is True

        self.device.set_buzzer(False)
        assert buzzer() is False

    def test_set_child_lock(self):
        def child_lock():
            return self.device.status().child_lock

        self.device.set_child_lock(True)
        assert child_lock() is True

        self.device.set_child_lock(False)
        assert child_lock() is False

    def test_delay_off(self):
        def delay_off_countdown():
            return self.device.status().delay_off_countdown

        self.device.delay_off(100)
        assert delay_off_countdown() == 100
        self.device.delay_off(200)
        assert delay_off_countdown() == 200
        self.device.delay_off(0)
        assert delay_off_countdown() == 0

        with pytest.raises(FanException):
            self.device.delay_off(-1)


class DummyFanV3(DummyDevice, Fan):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_FAN_V3
        self.state = {
            "temp_dec": 232,
            "humidity": 46,
            "angle": 118,
            "speed": 298,
            "poweroff_time": 0,
            "power": "on",
            "ac_power": "off",
            "battery": 98,
            "angle_enable": "off",
            "speed_level": 1,
            "natural_level": 0,
            "child_lock": "off",
            "buzzer": "on",
            "led_b": 1,
            "led": None,
            "natural_enable": None,
            "use_time": 0,
            "bat_charge": "complete",
            "bat_state": None,
            "button_pressed": "speed",
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_speed_level": lambda x: self._set_state("speed_level", x),
            "set_natural_level": lambda x: self._set_state("natural_level", x),
            "set_move": lambda x: True,
            "set_angle": lambda x: self._set_state("angle", x),
            "set_angle_enable": lambda x: self._set_state("angle_enable", x),
            "set_led_b": lambda x: self._set_state("led_b", x),
            "set_led": lambda x: self._set_state("led", x),
            "set_buzzer": lambda x: self._set_state("buzzer", x),
            "set_child_lock": lambda x: self._set_state("child_lock", x),
            "set_poweroff_time": lambda x: self._set_state("poweroff_time", x),
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def fanv3(request):
    request.cls.device = DummyFanV3()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("fanv3")
class TestFanV3(TestCase):
    def is_on(self):
        return self.device.status().is_on

    def state(self):
        return self.device.status()

    def test_on(self):
        self.device.off()  # ensure off
        assert self.is_on() is False

        self.device.on()
        assert self.is_on() is True

    def test_off(self):
        self.device.on()  # ensure on
        assert self.is_on() is True

        self.device.off()
        assert self.is_on() is False

    def test_status(self):
        self.device._reset_state()

        assert repr(self.state()) == repr(FanStatus(self.device.start_state))

        assert self.is_on() is True
        assert self.state().temperature == self.device.start_state["temp_dec"] / 10.0
        assert self.state().humidity == self.device.start_state["humidity"]
        assert self.state().angle == self.device.start_state["angle"]
        assert self.state().speed == self.device.start_state["speed"]
        assert (
            self.state().delay_off_countdown == self.device.start_state["poweroff_time"]
        )
        assert self.state().ac_power is (self.device.start_state["ac_power"] == "on")
        assert self.state().battery == self.device.start_state["battery"]
        assert self.state().oscillate is (
            self.device.start_state["angle_enable"] == "on"
        )
        assert self.state().direct_speed == self.device.start_state["speed_level"]
        assert self.state().natural_speed == self.device.start_state["natural_level"]
        assert self.state().child_lock is (
            self.device.start_state["child_lock"] == "on"
        )
        assert self.state().buzzer is (self.device.start_state["buzzer"] == "on")
        assert self.state().led_brightness == LedBrightness(
            self.device.start_state["led_b"]
        )
        assert self.state().led is None
        assert self.state().use_time == self.device.start_state["use_time"]
        assert self.state().battery_charge == self.device.start_state["bat_charge"]
        assert self.state().battery_state == self.device.start_state["bat_state"]
        assert self.state().button_pressed == self.device.start_state["button_pressed"]

    def test_status_without_led_brightness(self):
        self.device._reset_state()

        self.device.state["led_b"] = None
        assert self.state().led_brightness is None

    def test_status_without_battery_charge(self):
        self.device._reset_state()

        self.device.state["bat_charge"] = None
        assert self.state().battery_charge is None

    def test_status_without_battery_state(self):
        self.device._reset_state()

        self.device.state["bat_state"] = None
        assert self.state().battery_state is None

    def test_status_without_button_pressed(self):
        self.device._reset_state()

        self.device.state["button_pressed"] = None
        assert self.state().button_pressed is None

    def test_set_direct_speed(self):
        def direct_speed():
            return self.device.status().direct_speed

        self.device.set_direct_speed(0)
        assert direct_speed() == 0
        self.device.set_direct_speed(1)
        assert direct_speed() == 1
        self.device.set_direct_speed(100)
        assert direct_speed() == 100

        with pytest.raises(FanException):
            self.device.set_direct_speed(-1)

        with pytest.raises(FanException):
            self.device.set_direct_speed(101)

    def test_set_natural_speed(self):
        def natural_speed():
            return self.device.status().natural_speed

        self.device.set_natural_speed(0)
        assert natural_speed() == 0
        self.device.set_natural_speed(1)
        assert natural_speed() == 1
        self.device.set_natural_speed(100)
        assert natural_speed() == 100

        with pytest.raises(FanException):
            self.device.set_natural_speed(-1)

        with pytest.raises(FanException):
            self.device.set_natural_speed(101)

    def test_set_rotate(self):
        """The method is open-loop.

        The new state cannot be retrieved.
        """
        self.device.set_rotate(MoveDirection.Left)
        self.device.set_rotate(MoveDirection.Right)

    def test_set_angle(self):
        """This test doesn't implement the real behaviour of the device may be.

        The property "angle" doesn't provide the current setting. It's a measurement of
        the current position probably.
        """

        def angle():
            return self.device.status().angle

        self.device.set_angle(0)  # TODO: Is this value allowed?
        assert angle() == 0
        self.device.set_angle(1)  # TODO: Is this value allowed?
        assert angle() == 1
        self.device.set_angle(30)
        assert angle() == 30
        self.device.set_angle(60)
        assert angle() == 60
        self.device.set_angle(90)
        assert angle() == 90
        self.device.set_angle(120)
        assert angle() == 120

        with pytest.raises(FanException):
            self.device.set_angle(-1)

        with pytest.raises(FanException):
            self.device.set_angle(121)

    def test_set_oscillate(self):
        def oscillate():
            return self.device.status().oscillate

        self.device.set_oscillate(True)
        assert oscillate() is True

        self.device.set_oscillate(False)
        assert oscillate() is False

    def test_set_led_brightness(self):
        def led_brightness():
            return self.device.status().led_brightness

        self.device.set_led_brightness(LedBrightness.Bright)
        assert led_brightness() == LedBrightness.Bright

        self.device.set_led_brightness(LedBrightness.Dim)
        assert led_brightness() == LedBrightness.Dim

        self.device.set_led_brightness(LedBrightness.Off)
        assert led_brightness() == LedBrightness.Off

    def test_set_buzzer(self):
        def buzzer():
            return self.device.status().buzzer

        self.device.set_buzzer(True)
        assert buzzer() is True

        self.device.set_buzzer(False)
        assert buzzer() is False

    def test_set_child_lock(self):
        def child_lock():
            return self.device.status().child_lock

        self.device.set_child_lock(True)
        assert child_lock() is True

        self.device.set_child_lock(False)
        assert child_lock() is False

    def test_delay_off(self):
        def delay_off_countdown():
            return self.device.status().delay_off_countdown

        self.device.delay_off(100)
        assert delay_off_countdown() == 100
        self.device.delay_off(200)
        assert delay_off_countdown() == 200
        self.device.delay_off(0)
        assert delay_off_countdown() == 0

        with pytest.raises(FanException):
            self.device.delay_off(-1)


class DummyFanSA1(DummyDevice, Fan):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_FAN_SA1
        self.state = {
            "angle": 120,
            "speed": 277,
            "poweroff_time": 0,
            "power": "on",
            "ac_power": "on",
            "angle_enable": "off",
            "speed_level": 1,
            "natural_level": 2,
            "child_lock": "off",
            "buzzer": 0,
            "led_b": 0,
            "use_time": 2318,
        }

        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_speed_level": lambda x: self._set_state("speed_level", x),
            "set_natural_level": lambda x: self._set_state("natural_level", x),
            "set_move": lambda x: True,
            "set_angle": lambda x: self._set_state("angle", x),
            "set_angle_enable": lambda x: self._set_state("angle_enable", x),
            "set_led_b": lambda x: self._set_state("led_b", x),
            "set_buzzer": lambda x: self._set_state("buzzer", x),
            "set_child_lock": lambda x: self._set_state("child_lock", x),
            "set_poweroff_time": lambda x: self._set_state("poweroff_time", x),
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def fansa1(request):
    request.cls.device = DummyFanSA1()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("fansa1")
class TestFanSA1(TestCase):
    def is_on(self):
        return self.device.status().is_on

    def state(self):
        return self.device.status()

    def test_on(self):
        self.device.off()  # ensure off
        assert self.is_on() is False

        self.device.on()
        assert self.is_on() is True

    def test_off(self):
        self.device.on()  # ensure on
        assert self.is_on() is True

        self.device.off()
        assert self.is_on() is False

    def test_status(self):
        self.device._reset_state()

        assert repr(self.state()) == repr(FanStatus(self.device.start_state))

        assert self.is_on() is True
        assert self.state().angle == self.device.start_state["angle"]
        assert self.state().speed == self.device.start_state["speed"]
        assert (
            self.state().delay_off_countdown == self.device.start_state["poweroff_time"]
        )
        assert self.state().ac_power is (self.device.start_state["ac_power"] == "on")
        assert self.state().oscillate is (
            self.device.start_state["angle_enable"] == "on"
        )
        assert self.state().direct_speed == self.device.start_state["speed_level"]
        assert self.state().natural_speed == self.device.start_state["natural_level"]
        assert self.state().child_lock is (
            self.device.start_state["child_lock"] == "on"
        )
        assert self.state().buzzer is (self.device.start_state["buzzer"] == "on")
        assert self.state().led_brightness == LedBrightness(
            self.device.start_state["led_b"]
        )
        assert self.state().led is None
        assert self.state().use_time == self.device.start_state["use_time"]

    def test_set_direct_speed(self):
        def direct_speed():
            return self.device.status().direct_speed

        self.device.set_direct_speed(0)
        assert direct_speed() == 0
        self.device.set_direct_speed(1)
        assert direct_speed() == 1
        self.device.set_direct_speed(100)
        assert direct_speed() == 100

        with pytest.raises(FanException):
            self.device.set_direct_speed(-1)

        with pytest.raises(FanException):
            self.device.set_direct_speed(101)

    def test_set_natural_speed(self):
        def natural_speed():
            return self.device.status().natural_speed

        self.device.set_natural_speed(0)
        assert natural_speed() == 0
        self.device.set_natural_speed(1)
        assert natural_speed() == 1
        self.device.set_natural_speed(100)
        assert natural_speed() == 100

        with pytest.raises(FanException):
            self.device.set_natural_speed(-1)

        with pytest.raises(FanException):
            self.device.set_natural_speed(101)

    def test_set_rotate(self):
        """The method is open-loop.

        The new state cannot be retrieved.
        """
        self.device.set_rotate(MoveDirection.Left)
        self.device.set_rotate(MoveDirection.Right)

    def test_set_angle(self):
        """This test doesn't implement the real behaviour of the device may be.

        The property "angle" doesn't provide the current setting. It's a measurement of
        the current position probably.
        """

        def angle():
            return self.device.status().angle

        self.device.set_angle(0)  # TODO: Is this value allowed?
        assert angle() == 0
        self.device.set_angle(1)  # TODO: Is this value allowed?
        assert angle() == 1
        self.device.set_angle(30)
        assert angle() == 30
        self.device.set_angle(60)
        assert angle() == 60
        self.device.set_angle(90)
        assert angle() == 90
        self.device.set_angle(120)
        assert angle() == 120

        with pytest.raises(FanException):
            self.device.set_angle(-1)

        with pytest.raises(FanException):
            self.device.set_angle(121)

    def test_set_oscillate(self):
        def oscillate():
            return self.device.status().oscillate

        self.device.set_oscillate(True)
        assert oscillate() is True

        self.device.set_oscillate(False)
        assert oscillate() is False

    def test_set_led_brightness(self):
        def led_brightness():
            return self.device.status().led_brightness

        self.device.set_led_brightness(LedBrightness.Bright)
        assert led_brightness() == LedBrightness.Bright

        self.device.set_led_brightness(LedBrightness.Dim)
        assert led_brightness() == LedBrightness.Dim

        self.device.set_led_brightness(LedBrightness.Off)
        assert led_brightness() == LedBrightness.Off

    def test_set_buzzer(self):
        def buzzer():
            return self.device.status().buzzer

        self.device.set_buzzer(True)
        assert buzzer() is True

        self.device.set_buzzer(False)
        assert buzzer() is False

    def test_set_child_lock(self):
        def child_lock():
            return self.device.status().child_lock

        self.device.set_child_lock(True)
        assert child_lock() is True

        self.device.set_child_lock(False)
        assert child_lock() is False

    def test_delay_off(self):
        def delay_off_countdown():
            return self.device.status().delay_off_countdown

        self.device.delay_off(100)
        assert delay_off_countdown() == 100
        self.device.delay_off(200)
        assert delay_off_countdown() == 200
        self.device.delay_off(0)
        assert delay_off_countdown() == 0

        with pytest.raises(FanException):
            self.device.delay_off(-1)


class DummyFanP5(DummyDevice, FanP5):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_FAN_P5
        self.state = {
            "power": True,
            "mode": "normal",
            "speed": 35,
            "roll_enable": False,
            "roll_angle": 140,
            "time_off": 0,
            "light": True,
            "beep_sound": False,
            "child_lock": False,
        }

        self.return_values = {
            "get_prop": self._get_state,
            "s_power": lambda x: self._set_state("power", x),
            "s_mode": lambda x: self._set_state("mode", x),
            "s_speed": lambda x: self._set_state("speed", x),
            "s_roll": lambda x: self._set_state("roll_enable", x),
            "s_angle": lambda x: self._set_state("roll_angle", x),
            "s_t_off": lambda x: self._set_state("time_off", x),
            "s_light": lambda x: self._set_state("light", x),
            "s_sound": lambda x: self._set_state("beep_sound", x),
            "s_lock": lambda x: self._set_state("child_lock", x),
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def fanp5(request):
    request.cls.device = DummyFanP5()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("fanp5")
class TestFanP5(TestCase):
    def is_on(self):
        return self.device.status().is_on

    def state(self):
        return self.device.status()

    def test_on(self):
        self.device.off()  # ensure off
        assert self.is_on() is False

        self.device.on()
        assert self.is_on() is True

    def test_off(self):
        self.device.on()  # ensure on
        assert self.is_on() is True

        self.device.off()
        assert self.is_on() is False

    def test_status(self):
        self.device._reset_state()

        assert repr(self.state()) == repr(FanStatusP5(self.device.start_state))

        assert self.is_on() is True
        assert self.state().mode == OperationMode(self.device.start_state["mode"])
        assert self.state().speed == self.device.start_state["speed"]
        assert self.state().oscillate is self.device.start_state["roll_enable"]
        assert self.state().angle == self.device.start_state["roll_angle"]
        assert self.state().delay_off_countdown == self.device.start_state["time_off"]
        assert self.state().led is self.device.start_state["light"]
        assert self.state().buzzer is self.device.start_state["beep_sound"]
        assert self.state().child_lock is self.device.start_state["child_lock"]

    def test_set_mode(self):
        def mode():
            return self.device.status().mode

        self.device.set_mode(OperationMode.Normal)
        assert mode() == OperationMode.Normal

        self.device.set_mode(OperationMode.Nature)
        assert mode() == OperationMode.Nature

    def test_set_speed(self):
        def speed():
            return self.device.status().speed

        self.device.set_speed(0)
        assert speed() == 0
        self.device.set_speed(1)
        assert speed() == 1
        self.device.set_speed(100)
        assert speed() == 100

        with pytest.raises(FanException):
            self.device.set_speed(-1)

        with pytest.raises(FanException):
            self.device.set_speed(101)

    def test_set_angle(self):
        def angle():
            return self.device.status().angle

        self.device.set_angle(30)
        assert angle() == 30
        self.device.set_angle(60)
        assert angle() == 60
        self.device.set_angle(90)
        assert angle() == 90
        self.device.set_angle(120)
        assert angle() == 120
        self.device.set_angle(140)
        assert angle() == 140

        with pytest.raises(FanException):
            self.device.set_angle(-1)

        with pytest.raises(FanException):
            self.device.set_angle(1)

        with pytest.raises(FanException):
            self.device.set_angle(31)

        with pytest.raises(FanException):
            self.device.set_angle(141)

    def test_set_oscillate(self):
        def oscillate():
            return self.device.status().oscillate

        self.device.set_oscillate(True)
        assert oscillate() is True

        self.device.set_oscillate(False)
        assert oscillate() is False

    def test_set_led(self):
        def led():
            return self.device.status().led

        self.device.set_led(True)
        assert led() is True

        self.device.set_led(False)
        assert led() is False

    def test_set_buzzer(self):
        def buzzer():
            return self.device.status().buzzer

        self.device.set_buzzer(True)
        assert buzzer() is True

        self.device.set_buzzer(False)
        assert buzzer() is False

    def test_set_child_lock(self):
        def child_lock():
            return self.device.status().child_lock

        self.device.set_child_lock(True)
        assert child_lock() is True

        self.device.set_child_lock(False)
        assert child_lock() is False

    def test_delay_off(self):
        def delay_off_countdown():
            return self.device.status().delay_off_countdown

        self.device.delay_off(100)
        assert delay_off_countdown() == 100
        self.device.delay_off(200)
        assert delay_off_countdown() == 200
        self.device.delay_off(0)
        assert delay_off_countdown() == 0

        with pytest.raises(FanException):
            self.device.delay_off(-1)
