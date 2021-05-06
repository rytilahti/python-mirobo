from unittest import TestCase

import pytest

from miio import AirQualityMonitor
from miio.airqualitymonitor import (
    MODEL_AIRQUALITYMONITOR_B1,
    MODEL_AIRQUALITYMONITOR_S1,
    MODEL_AIRQUALITYMONITOR_V1,
    AirQualityMonitorStatus,
)

from .dummies import DummyDevice


class DummyAirQualityMonitorV1(DummyDevice, AirQualityMonitor):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_AIRQUALITYMONITOR_V1
        self.state = {
            "power": "on",
            "aqi": 34,
            "battery": 100,
            "usb_state": "off",
            "time_state": "on",
            "night_state": "on",
            "night_beg_time": "format unknown",
            "night_end_time": "format unknown",
            "sensor_state": "format unknown",
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_time_state": lambda x: self._set_state("time_state", x),
            "set_night_state": lambda x: self._set_state("night_state", x),
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def airqualitymonitorv1(request):
    request.cls.device = DummyAirQualityMonitorV1()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airqualitymonitorv1")
class TestAirQualityMonitorV1(TestCase):
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
            AirQualityMonitorStatus(self.device.start_state)
        )

        assert self.is_on() is True
        assert self.state().aqi == self.device.start_state["aqi"]
        assert self.state().battery == self.device.start_state["battery"]
        assert self.state().usb_power is (self.device.start_state["usb_state"] == "on")
        assert self.state().display_clock is (
            self.device.start_state["time_state"] == "on"
        )
        assert self.state().night_mode is (
            self.device.start_state["night_state"] == "on"
        )


class DummyAirQualityMonitorS1(DummyDevice, AirQualityMonitor):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_AIRQUALITYMONITOR_S1
        self.state = {
            "battery": 100,
            "co2": 695,
            "humidity": 62.1,
            "pm25": 19.4,
            "temperature": 27.4,
            "tvoc": 254,
        }
        self.return_values = {"get_prop": self._get_state}
        super().__init__(args, kwargs)

    def _get_state(self, props):
        """Return wanted properties."""
        return self.state


@pytest.fixture(scope="class")
def airqualitymonitors1(request):
    request.cls.device = DummyAirQualityMonitorS1()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airqualitymonitors1")
class TestAirQualityMonitorS1(TestCase):
    def state(self):
        return self.device.status()

    def test_status(self):
        self.device._reset_state()

        assert repr(self.state()) == repr(
            AirQualityMonitorStatus(self.device.start_state)
        )

        assert self.state().battery == self.device.start_state["battery"]
        assert self.state().co2 == self.device.start_state["co2"]
        assert self.state().humidity == self.device.start_state["humidity"]
        assert self.state().pm25 == self.device.start_state["pm25"]
        assert self.state().temperature == self.device.start_state["temperature"]
        assert self.state().tvoc == self.device.start_state["tvoc"]
        assert self.state().aqi is None
        assert self.state().usb_power is None
        assert self.state().display_clock is None
        assert self.state().night_mode is None


class DummyAirQualityMonitorB1(DummyDevice, AirQualityMonitor):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_AIRQUALITYMONITOR_B1
        self.state = {
            "co2e": 1466,
            "humidity": 59.79999923706055,
            "pm25": 2,
            "temperature": 19.799999237060547,
            "temperature_unit": "c",
            "tvoc": 1.3948699235916138,
            "tvoc_unit": "mg_m3",
        }
        self.return_values = {"get_air_data": self._get_state}
        super().__init__(args, kwargs)

    def _get_state(self, props):
        """Return wanted properties."""
        return self.state


@pytest.fixture(scope="class")
def airqualitymonitorb1(request):
    request.cls.device = DummyAirQualityMonitorB1()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airqualitymonitorb1")
class TestAirQualityMonitorB1(TestCase):
    def state(self):
        return self.device.status()

    def test_status(self):
        self.device._reset_state()

        assert repr(self.state()) == repr(
            AirQualityMonitorStatus(self.device.start_state)
        )

        assert self.state().power is None
        assert self.state().usb_power is None
        assert self.state().battery is None
        assert self.state().aqi is None
        assert self.state().temperature == self.device.start_state["temperature"]
        assert self.state().humidity == self.device.start_state["humidity"]
        assert self.state().co2 is None
        assert self.state().co2e == self.device.start_state["co2e"]
        assert self.state().pm25 == self.device.start_state["pm25"]
        assert self.state().tvoc == self.device.start_state["tvoc"]
        assert self.state().display_clock is None
        assert self.state().night_mode is None
