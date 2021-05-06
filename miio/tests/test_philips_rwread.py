from unittest import TestCase

import pytest

from miio import PhilipsRwread
from miio.philips_rwread import (
    MODEL_PHILIPS_LIGHT_RWREAD,
    MotionDetectionSensitivity,
    PhilipsRwreadException,
    PhilipsRwreadStatus,
)

from .dummies import DummyDevice


class DummyPhilipsRwread(DummyDevice, PhilipsRwread):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_PHILIPS_LIGHT_RWREAD
        self.state = {
            "power": "on",
            "bright": 53,
            "dv": 0,
            "snm": 1,
            "flm": 0,
            "flmv": 2,
            "chl": 0,
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_bright": lambda x: self._set_state("bright", x),
            "apply_fixed_scene": lambda x: self._set_state("snm", x),
            "delay_off": lambda x: self._set_state("dv", x),
            "enable_flm": lambda x: self._set_state("flm", x),
            "set_flmvalue": lambda x: self._set_state("flmv", x),
            "enable_chl": lambda x: self._set_state("chl", x),
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def philips_eyecare(request):
    request.cls.device = DummyPhilipsRwread()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("philips_eyecare")
class TestPhilipsRwread(TestCase):
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

        assert repr(self.state()) == repr(PhilipsRwreadStatus(self.device.start_state))

        assert self.is_on() is True
        assert self.state().brightness == self.device.start_state["bright"]
        assert self.state().delay_off_countdown == self.device.start_state["dv"]
        assert self.state().scene == self.device.start_state["snm"]
        assert self.state().motion_detection is (self.device.start_state["flm"] == 1)
        assert self.state().motion_detection_sensitivity == MotionDetectionSensitivity(
            self.device.start_state["flmv"]
        )

        assert self.state().child_lock is (self.device.start_state["chl"] == 1)

    def test_set_brightness(self):
        def brightness():
            return self.device.status().brightness

        self.device.set_brightness(1)
        assert brightness() == 1
        self.device.set_brightness(50)
        assert brightness() == 50
        self.device.set_brightness(100)

        with pytest.raises(PhilipsRwreadException):
            self.device.set_brightness(-1)

        with pytest.raises(PhilipsRwreadException):
            self.device.set_brightness(0)

        with pytest.raises(PhilipsRwreadException):
            self.device.set_brightness(101)

    def test_set_scene(self):
        def scene():
            return self.device.status().scene

        self.device.set_scene(1)
        assert scene() == 1
        self.device.set_scene(2)
        assert scene() == 2

        with pytest.raises(PhilipsRwreadException):
            self.device.set_scene(-1)

        with pytest.raises(PhilipsRwreadException):
            self.device.set_scene(0)

        with pytest.raises(PhilipsRwreadException):
            self.device.set_scene(5)

    def test_delay_off(self):
        def delay_off_countdown():
            return self.device.status().delay_off_countdown

        self.device.delay_off(1)
        assert delay_off_countdown() == 1
        self.device.delay_off(100)
        assert delay_off_countdown() == 100
        self.device.delay_off(200)
        assert delay_off_countdown() == 200

        with pytest.raises(PhilipsRwreadException):
            self.device.delay_off(-1)

    def test_set_motion_detection(self):
        def motion_detection():
            return self.device.status().motion_detection

        self.device.set_motion_detection(True)
        assert motion_detection() is True

        self.device.set_motion_detection(False)
        assert motion_detection() is False

    def test_set_motion_detection_sensitivity(self):
        def motion_detection_sensitivity():
            return self.device.status().motion_detection_sensitivity

        self.device.set_motion_detection_sensitivity(MotionDetectionSensitivity.Low)
        assert motion_detection_sensitivity() == MotionDetectionSensitivity.Low

        self.device.set_motion_detection_sensitivity(MotionDetectionSensitivity.Medium)
        assert motion_detection_sensitivity() == MotionDetectionSensitivity.Medium

        self.device.set_motion_detection_sensitivity(MotionDetectionSensitivity.High)
        assert motion_detection_sensitivity() == MotionDetectionSensitivity.High

    def test_set_child_lock(self):
        def child_lock():
            return self.device.status().child_lock

        self.device.set_child_lock(True)
        assert child_lock() is True

        self.device.set_child_lock(False)
        assert child_lock() is False
