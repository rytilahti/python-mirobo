from unittest import TestCase

import pytest

from miio import AirDogX3, AirDogX5, AirDogX7SM
from miio.airpurifier_airdog import (
    MODEL_AIRDOG_X3,
    MODEL_AIRDOG_X5,
    MODEL_AIRDOG_X7SM,
    AirDogException,
    AirDogStatus,
    OperationMode,
    OperationModeMapping,
)

from .dummies import DummyDevice


class DummyAirDogX3(DummyDevice, AirDogX3):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_AIRDOG_X3
        self.state = {
            "power": "on",
            "mode": "manual",
            "speed": 2,
            "lock": "unlock",
            "clean": "y",
            "pm": 11,
            "hcho": None,
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state(
                "power", ["on" if x[0] == 1 else "off"]
            ),
            "set_lock": lambda x: self._set_state(
                "lock", ["lock" if x[0] == 1 else "unlock"]
            ),
            "set_clean": lambda x: self._set_state("clean", ["n"]),
            "set_wind": lambda x: (
                self._set_state(
                    "mode", [OperationMode[OperationModeMapping(x[0]).name].value]
                ),
                self._set_state("speed", [x[1]]),
            ),
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def airdogx3(request):
    request.cls.device = DummyAirDogX3()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airdogx3")
class TestAirDogX3(TestCase):
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

        assert repr(self.state()) == repr(AirDogStatus(self.device.start_state))
        assert self.is_on() is True
        assert self.state().mode == OperationMode(self.device.start_state["mode"])
        assert self.state().speed == self.device.start_state["speed"]
        assert self.state().child_lock is (self.device.start_state["lock"] == "lock")
        assert self.state().clean_filters is (self.device.start_state["clean"] == "y")
        assert self.state().pm25 == self.device.start_state["pm"]
        assert self.state().hcho == self.device.start_state["hcho"]

    def test_set_mode_and_speed(self):
        def mode():
            return self.device.status().mode

        def speed():
            return self.device.status().speed

        self.device.set_mode_and_speed(OperationMode.Auto)
        assert mode() == OperationMode.Auto

        self.device.set_mode_and_speed(OperationMode.Auto, 2)
        assert mode() == OperationMode.Auto
        assert speed() == 1

        self.device.set_mode_and_speed(OperationMode.Manual)
        assert mode() == OperationMode.Manual
        assert speed() == 1

        self.device.set_mode_and_speed(OperationMode.Manual, 2)
        assert mode() == OperationMode.Manual
        assert speed() == 2

        self.device.set_mode_and_speed(OperationMode.Manual, 4)
        assert mode() == OperationMode.Manual
        assert speed() == 4

        with pytest.raises(AirDogException):
            self.device.set_mode_and_speed(OperationMode.Manual, 0)

        with pytest.raises(AirDogException):
            self.device.set_mode_and_speed(OperationMode.Manual, 5)

        self.device.set_mode_and_speed(OperationMode.Idle)
        assert mode() == OperationMode.Idle

        self.device.set_mode_and_speed(OperationMode.Idle, 2)
        assert mode() == OperationMode.Idle
        assert speed() == 1

    def test_set_child_lock(self):
        def child_lock():
            return self.device.status().child_lock

        self.device.set_child_lock(True)
        assert child_lock() is True

        self.device.set_child_lock(False)
        assert child_lock() is False

    def test_set_filters_cleaned(self):
        def clean_filters():
            return self.device.status().clean_filters

        assert clean_filters() is True

        self.device.set_filters_cleaned()
        assert clean_filters() is False


class DummyAirDogX5(DummyAirDogX3, AirDogX5):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self._model = MODEL_AIRDOG_X5
        self.state = {
            "power": "on",
            "mode": "manual",
            "speed": 2,
            "lock": "unlock",
            "clean": "y",
            "pm": 11,
            "hcho": None,
        }


@pytest.fixture(scope="class")
def airdogx5(request):
    request.cls.device = DummyAirDogX5()
    # TODO add ability to test on a real device


class DummyAirDogX7SM(DummyAirDogX5, AirDogX7SM):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self._model = MODEL_AIRDOG_X7SM
        self.state["hcho"] = 2


@pytest.fixture(scope="class")
def airdogx7sm(request):
    request.cls.device = DummyAirDogX7SM()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airdogx5")
@pytest.mark.usefixtures("airdogx7sm")
class TestAirDogX5AndX7SM(TestCase):
    def test_set_mode_and_speed(self):
        def mode():
            return self.device.status().mode

        def speed():
            return self.device.status().speed

        self.device.set_mode_and_speed(OperationMode.Manual, 5)
        assert mode() == OperationMode.Manual
        assert speed() == 5

        with pytest.raises(AirDogException):
            self.device.set_mode_and_speed(OperationMode.Manual, 6)
