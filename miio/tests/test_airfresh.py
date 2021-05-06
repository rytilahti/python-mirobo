from unittest import TestCase

import pytest

from miio import AirFresh
from miio.airfresh import (
    MODEL_AIRFRESH_VA2,
    MODEL_AIRFRESH_VA4,
    AirFreshException,
    AirFreshStatus,
    LedBrightness,
    OperationMode,
)

from .dummies import DummyDevice


class DummyAirFresh(DummyDevice, AirFresh):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_AIRFRESH_VA2
        self.state = {
            "power": "on",
            "ptc_state": None,
            "temp_dec": 186,
            "aqi": 10,
            "average_aqi": 8,
            "humidity": 62,
            "co2": 350,
            "buzzer": "off",
            "child_lock": "off",
            "led_level": 2,
            "mode": "auto",
            "motor1_speed": 354,
            "use_time": 2457000,
            "ntcT": None,
            "app_extra": 1,
            "f1_hour_used": 682,
            "filter_life": 80,
            "f_hour": 3500,
            "favorite_level": None,
            "led": "on",
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_mode": lambda x: self._set_state("mode", x),
            "set_buzzer": lambda x: self._set_state("buzzer", x),
            "set_child_lock": lambda x: self._set_state("child_lock", x),
            "set_led": lambda x: self._set_state("led", x),
            "set_led_level": lambda x: self._set_state("led_level", x),
            "reset_filter1": lambda x: (
                self._set_state("f1_hour_used", [0]),
                self._set_state("filter_life", [100]),
            ),
            "set_app_extra": lambda x: self._set_state("app_extra", x),
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def airfresh(request):
    request.cls.device = DummyAirFresh()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airfresh")
class TestAirFresh(TestCase):
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

        assert repr(self.state()) == repr(
            AirFreshStatus(self.device.start_state, MODEL_AIRFRESH_VA2)
        )

        assert self.is_on() is True
        assert self.state().ptc is None
        assert self.state().aqi == self.device.start_state["aqi"]
        assert self.state().average_aqi == self.device.start_state["average_aqi"]
        assert self.state().temperature == self.device.start_state["temp_dec"] / 10.0
        assert self.state().ntc_temperature is None
        assert self.state().humidity == self.device.start_state["humidity"]
        assert self.state().co2 == self.device.start_state["co2"]
        assert self.state().mode == OperationMode(self.device.start_state["mode"])
        assert (
            self.state().filter_life_remaining == self.device.start_state["filter_life"]
        )
        assert self.state().filter_hours_used == self.device.start_state["f1_hour_used"]
        assert self.state().use_time == self.device.start_state["use_time"]
        assert self.state().motor_speed == self.device.start_state["motor1_speed"]
        assert self.state().led == (self.device.start_state["led"] == "on")
        assert self.state().led_brightness == LedBrightness(
            self.device.start_state["led_level"]
        )
        assert self.state().buzzer == (self.device.start_state["buzzer"] == "on")
        assert self.state().child_lock == (
            self.device.start_state["child_lock"] == "on"
        )
        assert self.state().extra_features == self.device.start_state["app_extra"]

    def test_set_mode(self):
        def mode():
            return self.device.status().mode

        self.device.set_mode(OperationMode.Auto)
        assert mode() == OperationMode.Auto

        self.device.set_mode(OperationMode.Silent)
        assert mode() == OperationMode.Silent

        self.device.set_mode(OperationMode.Interval)
        assert mode() == OperationMode.Interval

        self.device.set_mode(OperationMode.Low)
        assert mode() == OperationMode.Low

        self.device.set_mode(OperationMode.Middle)
        assert mode() == OperationMode.Middle

        self.device.set_mode(OperationMode.Strong)
        assert mode() == OperationMode.Strong

    def test_set_led(self):
        def led():
            return self.device.status().led

        self.device.set_led(True)
        assert led() is True

        self.device.set_led(False)
        assert led() is False

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

    def test_set_extra_features(self):
        def extra_features():
            return self.device.status().extra_features

        self.device.set_extra_features(0)
        assert extra_features() == 0
        self.device.set_extra_features(1)
        assert extra_features() == 1
        self.device.set_extra_features(2)
        assert extra_features() == 2

        with pytest.raises(AirFreshException):
            self.device.set_extra_features(-1)

    def test_reset_filter(self):
        def filter_hours_used():
            return self.device.status().filter_hours_used

        def filter_life_remaining():
            return self.device.status().filter_life_remaining

        self.device._reset_state()
        assert filter_hours_used() != 0
        assert filter_life_remaining() != 100
        self.device.reset_filter()
        assert filter_hours_used() == 0
        assert filter_life_remaining() == 100


class DummyAirFreshVA4(DummyDevice, AirFresh):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_AIRFRESH_VA4
        self.state = {
            "power": "on",
            "ptc_state": "off",
            "temp_dec": 18.6,
            "aqi": 10,
            "average_aqi": 8,
            "humidity": 62,
            "co2": 350,
            "buzzer": "off",
            "child_lock": "off",
            "led_level": 2,
            "mode": "auto",
            "motor1_speed": 354,
            "use_time": 2457000,
            "ntcT": 33.53,
            "app_extra": 1,
            "f1_hour_used": 682,
            "filter_life": 80,
            "f_hour": 3500,
            "favorite_level": None,
            "led": "on",
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_ptc_state": lambda x: self._set_state("ptc_state", x),
            "set_mode": lambda x: self._set_state("mode", x),
            "set_buzzer": lambda x: self._set_state("buzzer", x),
            "set_child_lock": lambda x: self._set_state("child_lock", x),
            "set_led": lambda x: self._set_state("led", x),
            "set_led_level": lambda x: self._set_state("led_level", x),
            "reset_filter1": lambda x: (
                self._set_state("f1_hour_used", [0]),
                self._set_state("filter_life", [100]),
            ),
            "set_app_extra": lambda x: self._set_state("app_extra", x),
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def airfreshva4(request):
    request.cls.device = DummyAirFreshVA4()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airfreshva4")
class TestAirFreshVA4(TestAirFresh):
    def test_status(self):
        self.device._reset_state()

        assert repr(self.state()) == repr(
            AirFreshStatus(self.device.start_state, MODEL_AIRFRESH_VA4)
        )

        assert self.is_on() is True
        assert self.state().ptc == (self.device.start_state["ptc_state"] == "on")
        assert self.state().aqi == self.device.start_state["aqi"]
        assert self.state().average_aqi == self.device.start_state["average_aqi"]
        assert self.state().temperature == self.device.start_state["temp_dec"]
        assert self.state().ntc_temperature == self.device.start_state["ntcT"]
        assert self.state().humidity == self.device.start_state["humidity"]
        assert self.state().co2 == self.device.start_state["co2"]
        assert self.state().mode == OperationMode(self.device.start_state["mode"])
        assert (
            self.state().filter_life_remaining == self.device.start_state["filter_life"]
        )
        assert self.state().filter_hours_used == self.device.start_state["f1_hour_used"]
        assert self.state().use_time == self.device.start_state["use_time"]
        assert self.state().motor_speed == self.device.start_state["motor1_speed"]
        assert self.state().led == (self.device.start_state["led"] == "on")
        assert self.state().led_brightness == LedBrightness(
            self.device.start_state["led_level"]
        )
        assert self.state().buzzer == (self.device.start_state["buzzer"] == "on")
        assert self.state().child_lock == (
            self.device.start_state["child_lock"] == "on"
        )
        assert self.state().extra_features == self.device.start_state["app_extra"]

    def test_set_ptc(self):
        def ptc():
            return self.device.status().ptc

        self.device.set_ptc(True)
        assert ptc() is True

        self.device.set_ptc(False)
        assert ptc() is False
