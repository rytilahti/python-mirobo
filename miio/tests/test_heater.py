from unittest import TestCase

import pytest

from miio import Heater
from miio.heater import MODEL_HEATER_ZA1, Brightness, HeaterException, HeaterStatus

from .dummies import DummyDevice


class DummyHeater(DummyDevice, Heater):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_HEATER_ZA1
        # This example response is just a guess. Please update!
        self.state = {
            "target_temperature": 24,
            "temperature": 22.1,
            "relative_humidity": 46,
            "poweroff_time": 0,
            "power": "on",
            "child_lock": "off",
            "buzzer": "on",
            "brightness": 1,
            "use_time": 0,
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_target_temperature": lambda x: self._set_state(
                "target_temperature", x
            ),
            "set_brightness": lambda x: self._set_state("brightness", x),
            "set_buzzer": lambda x: self._set_state("buzzer", x),
            "set_child_lock": lambda x: self._set_state("child_lock", x),
            "set_poweroff_time": lambda x: self._set_state("poweroff_time", x),
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def heater(request):
    request.cls.device = DummyHeater()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("heater")
class TestHeater(TestCase):
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

        assert repr(self.state()) == repr(HeaterStatus(self.device.start_state))

        assert self.is_on() is True
        assert (
            self.state().target_temperature
            == self.device.start_state["target_temperature"]
        )
        assert self.state().temperature == self.device.start_state["temperature"]
        assert self.state().humidity == self.device.start_state["relative_humidity"]
        assert (
            self.state().delay_off_countdown == self.device.start_state["poweroff_time"]
        )
        assert self.state().child_lock is (
            self.device.start_state["child_lock"] == "on"
        )
        assert self.state().buzzer is (self.device.start_state["buzzer"] == "on")
        assert self.state().brightness == Brightness(
            self.device.start_state["brightness"]
        )
        assert self.state().use_time == self.device.start_state["use_time"]

    def test_set_target_temperature(self):
        def target_temperature():
            return self.device.status().target_temperature

        self.device.set_target_temperature(16)
        assert target_temperature() == 16
        self.device.set_target_temperature(24)
        assert target_temperature() == 24
        self.device.set_target_temperature(32)
        assert target_temperature() == 32

        with pytest.raises(HeaterException):
            self.device.set_target_temperature(15)

        with pytest.raises(HeaterException):
            self.device.set_target_temperature(33)

    def test_set_brightness(self):
        def brightness():
            return self.device.status().brightness

        self.device.set_brightness(Brightness.Bright)
        assert brightness() == Brightness.Bright

        self.device.set_brightness(Brightness.Dim)
        assert brightness() == Brightness.Dim

        self.device.set_brightness(Brightness.Off)
        assert brightness() == Brightness.Off

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

        self.device.delay_off(0)
        assert delay_off_countdown() == 0
        self.device.delay_off(9)
        assert delay_off_countdown() == 9

        with pytest.raises(HeaterException):
            self.device.delay_off(-1)

        with pytest.raises(HeaterException):
            self.device.delay_off(9 * 3600 + 1)
