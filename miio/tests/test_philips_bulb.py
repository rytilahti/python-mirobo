from unittest import TestCase

import pytest

from miio import PhilipsBulb, PhilipsWhiteBulb
from miio.philips_bulb import (
    MODEL_PHILIPS_LIGHT_BULB,
    MODEL_PHILIPS_LIGHT_HBULB,
    PhilipsBulbException,
    PhilipsBulbStatus,
)

from .dummies import DummyDevice


class DummyPhilipsBulb(DummyDevice, PhilipsBulb):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_PHILIPS_LIGHT_BULB
        self.state = {"power": "on", "bright": 100, "cct": 10, "snm": 0, "dv": 0}
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_bright": lambda x: self._set_state("bright", x),
            "set_cct": lambda x: self._set_state("cct", x),
            "delay_off": lambda x: self._set_state("dv", x),
            "apply_fixed_scene": lambda x: self._set_state("snm", x),
            "set_bricct": lambda x: (
                self._set_state("bright", [x[0]]),
                self._set_state("cct", [x[1]]),
            ),
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def philips_bulb(request):
    request.cls.device = DummyPhilipsBulb()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("philips_bulb")
class TestPhilipsBulb(TestCase):
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

        assert repr(self.state()) == repr(PhilipsBulbStatus(self.device.start_state))

        assert self.is_on() is True
        assert self.state().brightness == self.device.start_state["bright"]
        assert self.state().color_temperature == self.device.start_state["cct"]
        assert self.state().scene == self.device.start_state["snm"]
        assert self.state().delay_off_countdown == self.device.start_state["dv"]

    def test_set_brightness(self):
        def brightness():
            return self.device.status().brightness

        self.device.set_brightness(1)
        assert brightness() == 1
        self.device.set_brightness(50)
        assert brightness() == 50
        self.device.set_brightness(100)

        with pytest.raises(PhilipsBulbException):
            self.device.set_brightness(-1)

        with pytest.raises(PhilipsBulbException):
            self.device.set_brightness(0)

        with pytest.raises(PhilipsBulbException):
            self.device.set_brightness(101)

    def test_set_color_temperature(self):
        def color_temperature():
            return self.device.status().color_temperature

        self.device.set_color_temperature(20)
        assert color_temperature() == 20
        self.device.set_color_temperature(30)
        assert color_temperature() == 30
        self.device.set_color_temperature(10)

        with pytest.raises(PhilipsBulbException):
            self.device.set_color_temperature(-1)

        with pytest.raises(PhilipsBulbException):
            self.device.set_color_temperature(0)

        with pytest.raises(PhilipsBulbException):
            self.device.set_color_temperature(101)

    def test_set_brightness_and_color_temperature(self):
        def color_temperature():
            return self.device.status().color_temperature

        def brightness():
            return self.device.status().brightness

        self.device.set_brightness_and_color_temperature(20, 21)
        assert brightness() == 20
        assert color_temperature() == 21
        self.device.set_brightness_and_color_temperature(31, 30)
        assert brightness() == 31
        assert color_temperature() == 30
        self.device.set_brightness_and_color_temperature(10, 11)
        assert brightness() == 10
        assert color_temperature() == 11

        with pytest.raises(PhilipsBulbException):
            self.device.set_brightness_and_color_temperature(-1, 10)

        with pytest.raises(PhilipsBulbException):
            self.device.set_brightness_and_color_temperature(10, -1)

        with pytest.raises(PhilipsBulbException):
            self.device.set_brightness_and_color_temperature(0, 10)

        with pytest.raises(PhilipsBulbException):
            self.device.set_brightness_and_color_temperature(10, 0)

        with pytest.raises(PhilipsBulbException):
            self.device.set_brightness_and_color_temperature(101, 10)

        with pytest.raises(PhilipsBulbException):
            self.device.set_brightness_and_color_temperature(10, 101)

    def test_delay_off(self):
        def delay_off_countdown():
            return self.device.status().delay_off_countdown

        self.device.delay_off(100)
        assert delay_off_countdown() == 100
        self.device.delay_off(200)
        assert delay_off_countdown() == 200

        with pytest.raises(PhilipsBulbException):
            self.device.delay_off(-1)

        with pytest.raises(PhilipsBulbException):
            self.device.delay_off(0)

    def test_set_scene(self):
        def scene():
            return self.device.status().scene

        self.device.set_scene(1)
        assert scene() == 1
        self.device.set_scene(2)
        assert scene() == 2

        with pytest.raises(PhilipsBulbException):
            self.device.set_scene(-1)

        with pytest.raises(PhilipsBulbException):
            self.device.set_scene(0)

        with pytest.raises(PhilipsBulbException):
            self.device.set_scene(5)


class DummyPhilipsWhiteBulb(DummyDevice, PhilipsWhiteBulb):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_PHILIPS_LIGHT_HBULB
        self.state = {"power": "on", "bri": 100, "dv": 0}
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_bright": lambda x: self._set_state("bri", x),
            "delay_off": lambda x: self._set_state("dv", x),
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def philips_white_bulb(request):
    request.cls.device = DummyPhilipsWhiteBulb()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("philips_white_bulb")
class TestPhilipsWhiteBulb(TestCase):
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

        assert repr(self.state()) == repr(PhilipsBulbStatus(self.device.start_state))

        assert self.is_on() is True
        assert self.state().brightness == self.device.start_state["bri"]
        assert self.state().delay_off_countdown == self.device.start_state["dv"]
        assert self.state().color_temperature is None
        assert self.state().scene is None

    def test_set_brightness(self):
        def brightness():
            return self.device.status().brightness

        self.device.set_brightness(1)
        assert brightness() == 1
        self.device.set_brightness(50)
        assert brightness() == 50
        self.device.set_brightness(100)

        with pytest.raises(PhilipsBulbException):
            self.device.set_brightness(-1)

        with pytest.raises(PhilipsBulbException):
            self.device.set_brightness(0)

        with pytest.raises(PhilipsBulbException):
            self.device.set_brightness(101)

    def test_delay_off(self):
        def delay_off_countdown():
            return self.device.status().delay_off_countdown

        self.device.delay_off(100)
        assert delay_off_countdown() == 100
        self.device.delay_off(200)
        assert delay_off_countdown() == 200

        with pytest.raises(PhilipsBulbException):
            self.device.delay_off(-1)

        with pytest.raises(PhilipsBulbException):
            self.device.delay_off(0)
