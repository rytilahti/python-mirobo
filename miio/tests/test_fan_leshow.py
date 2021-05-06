from unittest import TestCase

import pytest

from miio import FanLeshow
from miio.fan_leshow import (
    MODEL_FAN_LESHOW_SS4,
    FanLeshowException,
    FanLeshowStatus,
    OperationMode,
)

from .dummies import DummyDevice


class DummyFanLeshow(DummyDevice, FanLeshow):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_FAN_LESHOW_SS4
        self.state = {
            "power": 1,
            "mode": 2,
            "blow": 100,
            "timer": 0,
            "sound": 1,
            "yaw": 0,
            "fault": 0,
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_mode": lambda x: self._set_state("mode", x),
            "set_blow": lambda x: self._set_state("blow", x),
            "set_timer": lambda x: self._set_state("timer", x),
            "set_sound": lambda x: self._set_state("sound", x),
            "set_yaw": lambda x: self._set_state("yaw", x),
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def fanleshow(request):
    request.cls.device = DummyFanLeshow()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("fanleshow")
class TestFanLeshow(TestCase):
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

        assert repr(self.state()) == repr(FanLeshowStatus(self.device.start_state))

        assert self.is_on() is True
        assert self.state().mode == OperationMode(self.device.start_state["mode"])
        assert self.state().speed == self.device.start_state["blow"]
        assert self.state().buzzer is (self.device.start_state["sound"] == 1)
        assert self.state().oscillate is (self.device.start_state["yaw"] == 1)
        assert self.state().delay_off_countdown == self.device.start_state["timer"]
        assert self.state().error_detected is (self.device.start_state["fault"] == 1)

    def test_set_speed(self):
        def speed():
            return self.device.status().speed

        self.device.set_speed(0)
        assert speed() == 0
        self.device.set_speed(1)
        assert speed() == 1
        self.device.set_speed(100)
        assert speed() == 100

        with pytest.raises(FanLeshowException):
            self.device.set_speed(-1)

        with pytest.raises(FanLeshowException):
            self.device.set_speed(101)

    def test_set_oscillate(self):
        def oscillate():
            return self.device.status().oscillate

        self.device.set_oscillate(True)
        assert oscillate() is True

        self.device.set_oscillate(False)
        assert oscillate() is False

    def test_set_buzzer(self):
        def buzzer():
            return self.device.status().buzzer

        self.device.set_buzzer(True)
        assert buzzer() is True

        self.device.set_buzzer(False)
        assert buzzer() is False

    def test_delay_off(self):
        def delay_off_countdown():
            return self.device.status().delay_off_countdown

        self.device.delay_off(100)
        assert delay_off_countdown() == 100
        self.device.delay_off(200)
        assert delay_off_countdown() == 200
        self.device.delay_off(0)
        assert delay_off_countdown() == 0

        with pytest.raises(FanLeshowException):
            self.device.delay_off(-1)

        with pytest.raises(FanLeshowException):
            self.device.delay_off(541)
