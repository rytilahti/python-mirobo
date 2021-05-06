from unittest import TestCase

import pytest

from miio import AirFreshA1, AirFreshT2017
from miio.airfresh_t2017 import (
    MODEL_AIRFRESH_A1,
    MODEL_AIRFRESH_T2017,
    AirFreshException,
    AirFreshStatus,
    DisplayOrientation,
    OperationMode,
    PtcLevel,
)

from .dummies import DummyDevice


class DummyAirFreshA1(DummyDevice, AirFreshA1):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_AIRFRESH_A1
        self.state = {
            "power": True,
            "mode": "auto",
            "pm25": 2,
            "co2": 554,
            "temperature_outside": 12,
            "favourite_speed": 150,
            "control_speed": 45,
            "filter_rate": 45,
            "filter_day": 81,
            "ptc_on": False,
            "ptc_status": False,
            "child_lock": False,
            "sound": True,
            "display": False,
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_mode": lambda x: self._set_state("mode", x),
            "set_sound": lambda x: self._set_state("sound", x),
            "set_child_lock": lambda x: self._set_state("child_lock", x),
            "set_display": lambda x: self._set_state("display", x),
            "set_ptc_on": lambda x: self._set_state("ptc_on", x),
            "set_favourite_speed": lambda x: self._set_state("favourite_speed", x),
            "set_filter_rate": lambda x: self._set_filter_rate(x),
        }
        super().__init__(args, kwargs)

    def _set_filter_rate(self, value: str):
        if value[0] == 100:
            self._set_state("filter_rate", [100])
            self._set_state("filter_day", [180])


@pytest.fixture(scope="class")
def airfresha1(request):
    request.cls.device = DummyAirFreshA1()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airfresha1")
class TestAirFreshA1(TestCase):
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

        assert repr(self.state()) == repr(AirFreshStatus(self.device.start_state))

        assert self.is_on() is True
        assert (
            self.state().temperature == self.device.start_state["temperature_outside"]
        )
        assert self.state().co2 == self.device.start_state["co2"]
        assert self.state().pm25 == self.device.start_state["pm25"]
        assert self.state().mode == OperationMode(self.device.start_state["mode"])
        assert self.state().buzzer == self.device.start_state["sound"]
        assert self.state().child_lock == self.device.start_state["child_lock"]

    def test_set_mode(self):
        def mode():
            return self.device.status().mode

        self.device.set_mode(OperationMode.Off)
        assert mode() == OperationMode.Off

        self.device.set_mode(OperationMode.Auto)
        assert mode() == OperationMode.Auto

        self.device.set_mode(OperationMode.Sleep)
        assert mode() == OperationMode.Sleep

        self.device.set_mode(OperationMode.Favorite)
        assert mode() == OperationMode.Favorite

    def test_set_display(self):
        def display():
            return self.device.status().display

        self.device.set_display(True)
        assert display() is True

        self.device.set_display(False)
        assert display() is False

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

    def test_reset_dust_filter(self):
        def dust_filter_life_remaining():
            return self.device.status().dust_filter_life_remaining

        def dust_filter_life_remaining_days():
            return self.device.status().dust_filter_life_remaining_days

        self.device._reset_state()
        assert dust_filter_life_remaining() != 100
        assert dust_filter_life_remaining_days() != 180
        self.device.reset_dust_filter()
        assert dust_filter_life_remaining() == 100
        assert dust_filter_life_remaining_days() == 180

    def test_set_favorite_speed(self):
        def favorite_speed():
            return self.device.status().favorite_speed

        self.device.set_favorite_speed(0)
        assert favorite_speed() == 0
        self.device.set_favorite_speed(150)
        assert favorite_speed() == 150

        with pytest.raises(AirFreshException):
            self.device.set_favorite_speed(-1)

        with pytest.raises(AirFreshException):
            self.device.set_favorite_speed(151)

    def test_set_ptc(self):
        def ptc():
            return self.device.status().ptc

        self.device.set_ptc(True)
        assert ptc() is True

        self.device.set_ptc(False)
        assert ptc() is False


class DummyAirFreshT2017(DummyDevice, AirFreshT2017):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_AIRFRESH_T2017
        self.state = {
            "power": True,
            "mode": "favourite",
            "pm25": 1,
            "co2": 550,
            "temperature_outside": 24,
            "favourite_speed": 241,
            "control_speed": 241,
            "filter_intermediate": 99,
            "filter_inter_day": 89,
            "filter_efficient": 99,
            "filter_effi_day": 179,
            "ptc_on": False,
            "ptc_level": "low",
            "ptc_status": False,
            "child_lock": False,
            "sound": True,
            "display": False,
            "screen_direction": "forward",
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_mode": lambda x: self._set_state("mode", x),
            "set_sound": lambda x: self._set_state("sound", x),
            "set_child_lock": lambda x: self._set_state("child_lock", x),
            "set_display": lambda x: self._set_state("display", x),
            "set_screen_direction": lambda x: self._set_state("screen_direction", x),
            "set_ptc_level": lambda x: self._set_state("ptc_level", x),
            "set_ptc_on": lambda x: self._set_state("ptc_on", x),
            "set_favourite_speed": lambda x: self._set_state("favourite_speed", x),
            "set_filter_reset": lambda x: self._set_filter_reset(x),
        }
        super().__init__(args, kwargs)

    def _set_filter_reset(self, value: str):
        if value[0] == "efficient":
            self._set_state("filter_efficient", [100])
            self._set_state("filter_effi_day", [180])

        if value[0] == "intermediate":
            self._set_state("filter_intermediate", [100])
            self._set_state("filter_inter_day", [90])


@pytest.fixture(scope="class")
def airfresht2017(request):
    request.cls.device = DummyAirFreshT2017()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airfresht2017")
class TestAirFreshT2017(TestCase):
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

        assert repr(self.state()) == repr(AirFreshStatus(self.device.start_state))

        assert self.is_on() is True
        assert (
            self.state().temperature == self.device.start_state["temperature_outside"]
        )
        assert self.state().co2 == self.device.start_state["co2"]
        assert self.state().pm25 == self.device.start_state["pm25"]
        assert self.state().mode == OperationMode(self.device.start_state["mode"])
        assert self.state().buzzer == self.device.start_state["sound"]
        assert self.state().child_lock == self.device.start_state["child_lock"]

    def test_set_mode(self):
        def mode():
            return self.device.status().mode

        self.device.set_mode(OperationMode.Off)
        assert mode() == OperationMode.Off

        self.device.set_mode(OperationMode.Auto)
        assert mode() == OperationMode.Auto

        self.device.set_mode(OperationMode.Sleep)
        assert mode() == OperationMode.Sleep

        self.device.set_mode(OperationMode.Favorite)
        assert mode() == OperationMode.Favorite

    def test_set_display(self):
        def display():
            return self.device.status().display

        self.device.set_display(True)
        assert display() is True

        self.device.set_display(False)
        assert display() is False

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

    def test_reset_dust_filter(self):
        def dust_filter_life_remaining():
            return self.device.status().dust_filter_life_remaining

        def dust_filter_life_remaining_days():
            return self.device.status().dust_filter_life_remaining_days

        self.device._reset_state()
        assert dust_filter_life_remaining() != 100
        assert dust_filter_life_remaining_days() != 90
        self.device.reset_dust_filter()
        assert dust_filter_life_remaining() == 100
        assert dust_filter_life_remaining_days() == 90

    def test_reset_upper_filter(self):
        def upper_filter_life_remaining():
            return self.device.status().upper_filter_life_remaining

        def upper_filter_life_remaining_days():
            return self.device.status().upper_filter_life_remaining_days

        self.device._reset_state()
        assert upper_filter_life_remaining() != 100
        assert upper_filter_life_remaining_days() != 180
        self.device.reset_upper_filter()
        assert upper_filter_life_remaining() == 100
        assert upper_filter_life_remaining_days() == 180

    def test_set_favorite_speed(self):
        def favorite_speed():
            return self.device.status().favorite_speed

        self.device.set_favorite_speed(60)
        assert favorite_speed() == 60
        self.device.set_favorite_speed(120)
        assert favorite_speed() == 120
        self.device.set_favorite_speed(240)
        assert favorite_speed() == 240
        self.device.set_favorite_speed(300)
        assert favorite_speed() == 300

        with pytest.raises(AirFreshException):
            self.device.set_favorite_speed(-1)

        with pytest.raises(AirFreshException):
            self.device.set_favorite_speed(59)

        with pytest.raises(AirFreshException):
            self.device.set_favorite_speed(301)

    def test_set_ptc(self):
        def ptc():
            return self.device.status().ptc

        self.device.set_ptc(True)
        assert ptc() is True

        self.device.set_ptc(False)
        assert ptc() is False

    def test_set_ptc_level(self):
        def ptc_level():
            return self.device.status().ptc_level

        self.device.set_ptc_level(PtcLevel.Low)
        assert ptc_level() == PtcLevel.Low
        self.device.set_ptc_level(PtcLevel.Medium)
        assert ptc_level() == PtcLevel.Medium
        self.device.set_ptc_level(PtcLevel.High)
        assert ptc_level() == PtcLevel.High

    def test_set_display_orientation(self):
        def display_orientation():
            return self.device.status().display_orientation

        self.device.set_display_orientation(DisplayOrientation.Portrait)
        assert display_orientation() == DisplayOrientation.Portrait
        self.device.set_display_orientation(DisplayOrientation.LandscapeLeft)
        assert display_orientation() == DisplayOrientation.LandscapeLeft
        self.device.set_display_orientation(DisplayOrientation.LandscapeRight)
        assert display_orientation() == DisplayOrientation.LandscapeRight
