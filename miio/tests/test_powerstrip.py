from unittest import TestCase

import pytest

from miio import PowerStrip
from miio.powerstrip import (
    MODEL_POWER_STRIP_V1,
    MODEL_POWER_STRIP_V2,
    PowerMode,
    PowerStripException,
    PowerStripStatus,
)

from .dummies import DummyDevice


class DummyPowerStripV1(DummyDevice, PowerStrip):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_POWER_STRIP_V1
        self.state = {
            "power": "on",
            "mode": "normal",
            "temperature": 32.5,
            "current": 25.5,
            "power_consume_rate": 12.5,
            "voltage": 23057,
            "power_factor": 12,
            "elec_leakage": 8,
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_power_mode": lambda x: self._set_state("mode", x),
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def powerstripv1(request):
    request.cls.device = DummyPowerStripV1()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("powerstripv1")
class TestPowerStripV1(TestCase):
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

        assert repr(self.state()) == repr(PowerStripStatus(self.device.start_state))

        assert self.is_on() is True
        assert self.state().mode == PowerMode(self.device.start_state["mode"])
        assert self.state().temperature == self.device.start_state["temperature"]
        assert self.state().current == self.device.start_state["current"]
        assert self.state().load_power == self.device.start_state["power_consume_rate"]
        assert self.state().voltage == self.device.start_state["voltage"] / 100.0
        assert self.state().power_factor == self.device.start_state["power_factor"]
        assert self.state().leakage_current == self.device.start_state["elec_leakage"]

    def test_status_without_power_consume_rate(self):
        self.device._reset_state()

        self.device.state["power_consume_rate"] = None
        assert self.state().load_power is None

    def test_status_without_current(self):
        self.device._reset_state()

        self.device.state["current"] = None
        assert self.state().current is None

    def test_status_without_mode(self):
        self.device._reset_state()

        # The Power Strip  2 doesn't support power modes
        self.device.state["mode"] = None
        assert self.state().mode is None

    def test_set_power_mode(self):
        def mode():
            return self.device.status().mode

        self.device.set_power_mode(PowerMode.Eco)
        assert mode() == PowerMode.Eco
        self.device.set_power_mode(PowerMode.Normal)
        assert mode() == PowerMode.Normal


class DummyPowerStripV2(DummyDevice, PowerStrip):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_POWER_STRIP_V2
        self.state = {
            "power": "on",
            "mode": "normal",
            "temperature": 32.5,
            "current": 25.5,
            "power_consume_rate": 12.5,
            "wifi_led": "off",
            "power_price": 49,
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_power_mode": lambda x: self._set_state("mode", x),
            "set_wifi_led": lambda x: self._set_state("wifi_led", x),
            "set_power_price": lambda x: self._set_state("power_price", x),
            "set_rt_power": lambda x: True,
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def powerstripv2(request):
    request.cls.device = DummyPowerStripV2()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("powerstripv2")
class TestPowerStripV2(TestCase):
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

        assert repr(self.state()) == repr(PowerStripStatus(self.device.start_state))

        assert self.is_on() is True
        assert self.state().mode == PowerMode(self.device.start_state["mode"])
        assert self.state().temperature == self.device.start_state["temperature"]
        assert self.state().current == self.device.start_state["current"]
        assert self.state().load_power == self.device.start_state["power_consume_rate"]
        assert self.state().voltage is None
        assert self.state().power_factor is None
        assert self.state().leakage_current is None

    def test_status_without_power_consume_rate(self):
        self.device._reset_state()

        self.device.state["power_consume_rate"] = None
        assert self.state().load_power is None

    def test_status_without_current(self):
        self.device._reset_state()

        self.device.state["current"] = None
        assert self.state().current is None

    def test_status_without_mode(self):
        self.device._reset_state()

        # The Power Strip  2 doesn't support power modes
        self.device.state["mode"] = None
        assert self.state().mode is None

    def test_set_power_mode(self):
        def mode():
            return self.device.status().mode

        self.device.set_power_mode(PowerMode.Eco)
        assert mode() == PowerMode.Eco
        self.device.set_power_mode(PowerMode.Normal)
        assert mode() == PowerMode.Normal

    def test_set_wifi_led(self):
        def wifi_led():
            return self.device.status().wifi_led

        self.device.set_wifi_led(True)
        assert wifi_led() is True

        self.device.set_wifi_led(False)
        assert wifi_led() is False

    def test_set_power_price(self):
        def power_price():
            return self.device.status().power_price

        self.device.set_power_price(0)
        assert power_price() == 0
        self.device.set_power_price(1)
        assert power_price() == 1
        self.device.set_power_price(2)
        assert power_price() == 2

        with pytest.raises(PowerStripException):
            self.device.set_power_price(-1)

        with pytest.raises(PowerStripException):
            self.device.set_power_price(1000)

    def test_status_without_power_price(self):
        self.device._reset_state()

        self.device.state["power_price"] = None
        assert self.state().power_price is None

    def test_set_realtime_power(self):
        """The method is open-loop.

        The new state cannot be retrieved.
        """
        self.device.set_realtime_power(True)
        self.device.set_realtime_power(False)
