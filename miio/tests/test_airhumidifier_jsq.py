from collections import OrderedDict
from unittest import TestCase

import pytest

from miio import AirHumidifierJsq
from miio.airhumidifier import AirHumidifierException
from miio.airhumidifier_jsq import (
    MODEL_HUMIDIFIER_JSQ001,
    AirHumidifierStatus,
    LedBrightness,
    OperationMode,
)

from .dummies import DummyDevice


class DummyAirHumidifierJsq(DummyDevice, AirHumidifierJsq):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_HUMIDIFIER_JSQ001

        self.dummy_device_info = {
            "life": 575661,
            "token": "68ffffffffffffffffffffffffffffff",
            "mac": "78:11:FF:FF:FF:FF",
            "fw_ver": "1.3.9",
            "hw_ver": "ESP8266",
            "uid": "1111111111",
            "model": self.model,
            "mcu_fw_ver": "0001",
            "wifi_fw_ver": "1.5.0-dev(7efd021)",
            "ap": {"rssi": -71, "ssid": "ap", "bssid": "FF:FF:FF:FF:FF:FF"},
            "netif": {
                "gw": "192.168.0.1",
                "localIp": "192.168.0.25",
                "mask": "255.255.255.0",
            },
            "mmfree": 228248,
        }

        self.device_info = None

        self.state = OrderedDict(
            (
                ("temperature", 24),
                ("humidity", 29),
                ("mode", 3),
                ("buzzer", 1),
                ("child_lock", 1),
                ("led_brightness", 2),
                ("power", 1),
                ("no_water", 1),
                ("lid_opened", 1),
            )
        )
        self.start_state = self.state.copy()

        self.return_values = {
            "get_props": self._get_state,
            "set_start": lambda x: self._set_state("power", x),
            "set_mode": lambda x: self._set_state("mode", x),
            "set_brightness": lambda x: self._set_state("led_brightness", x),
            "set_buzzer": lambda x: self._set_state("buzzer", x),
            "set_lock": lambda x: self._set_state("child_lock", x),
            "miIO.info": self._get_device_info,
        }

        super().__init__(args, kwargs)

    def _get_device_info(self, _):
        """Return dummy device info."""
        return self.dummy_device_info

    def _get_state(self, props):
        """Return wanted properties."""
        return list(self.state.values())


@pytest.fixture(scope="class")
def airhumidifier_jsq(request):
    request.cls.device = DummyAirHumidifierJsq()
    # TODO add ability to test on a real device


class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


@pytest.mark.usefixtures("airhumidifier_jsq")
class TestAirHumidifierJsq(TestCase):
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

        assert repr(self.state()) == repr(AirHumidifierStatus(self.device.start_state))

        assert self.state().temperature == self.device.start_state["temperature"]
        assert self.state().humidity == self.device.start_state["humidity"]
        assert self.state().mode == OperationMode(self.device.start_state["mode"])
        assert self.state().buzzer == (self.device.start_state["buzzer"] == 1)
        assert self.state().child_lock == (self.device.start_state["child_lock"] == 1)
        assert self.state().led_brightness == LedBrightness(
            self.device.start_state["led_brightness"]
        )
        assert self.is_on() is True
        assert self.state().no_water == (self.device.start_state["no_water"] == 1)
        assert self.state().lid_opened == (self.device.start_state["lid_opened"] == 1)

    def test_status_wrong_input(self):
        def mode():
            return self.device.status().mode

        def led_brightness():
            return self.device.status().led_brightness

        self.device._reset_state()

        self.device.state["mode"] = 10
        assert mode() == OperationMode.Intelligent

        self.device.state["mode"] = "smth"
        assert mode() == OperationMode.Intelligent

        self.device.state["led_brightness"] = 10
        assert led_brightness() == LedBrightness.Off

        self.device.state["led_brightness"] = "smth"
        assert led_brightness() == LedBrightness.Off

    def test_set_mode(self):
        def mode():
            return self.device.status().mode

        self.device.set_mode(OperationMode.Intelligent)
        assert mode() == OperationMode.Intelligent

        self.device.set_mode(OperationMode.Level1)
        assert mode() == OperationMode.Level1

        self.device.set_mode(OperationMode.Level4)
        assert mode() == OperationMode.Level4

    def test_set_mode_wrong_input(self):
        def mode():
            return self.device.status().mode

        self.device.set_mode(OperationMode.Level3)
        assert mode() == OperationMode.Level3

        with pytest.raises(AirHumidifierException) as excinfo:
            self.device.set_mode(Bunch(value=10))
        assert str(excinfo.value) == "10 is not a valid OperationMode value"
        assert mode() == OperationMode.Level3

        with pytest.raises(AirHumidifierException) as excinfo:
            self.device.set_mode(Bunch(value=-1))
        assert str(excinfo.value) == "-1 is not a valid OperationMode value"
        assert mode() == OperationMode.Level3

        with pytest.raises(AirHumidifierException) as excinfo:
            self.device.set_mode(Bunch(value="smth"))
        assert str(excinfo.value) == "smth is not a valid OperationMode value"
        assert mode() == OperationMode.Level3

    def test_set_led_brightness(self):
        def led_brightness():
            return self.device.status().led_brightness

        self.device.set_led_brightness(LedBrightness.Off)
        assert led_brightness() == LedBrightness.Off

        self.device.set_led_brightness(LedBrightness.Low)
        assert led_brightness() == LedBrightness.Low

        self.device.set_led_brightness(LedBrightness.High)
        assert led_brightness() == LedBrightness.High

    def test_set_led_brightness_wrong_input(self):
        def led_brightness():
            return self.device.status().led_brightness

        self.device.set_led_brightness(LedBrightness.Low)
        assert led_brightness() == LedBrightness.Low

        with pytest.raises(AirHumidifierException) as excinfo:
            self.device.set_led_brightness(Bunch(value=10))
        assert str(excinfo.value) == "10 is not a valid LedBrightness value"
        assert led_brightness() == LedBrightness.Low

        with pytest.raises(AirHumidifierException) as excinfo:
            self.device.set_led_brightness(Bunch(value=-10))
        assert str(excinfo.value) == "-10 is not a valid LedBrightness value"
        assert led_brightness() == LedBrightness.Low

        with pytest.raises(AirHumidifierException) as excinfo:
            self.device.set_led_brightness(Bunch(value="smth"))
        assert str(excinfo.value) == "smth is not a valid LedBrightness value"
        assert led_brightness() == LedBrightness.Low

    def test_set_led(self):
        def led_brightness():
            return self.device.status().led_brightness

        self.device.set_led(True)
        assert led_brightness() == LedBrightness.High

        self.device.set_led(False)
        assert led_brightness() == LedBrightness.Off

    def test_set_buzzer(self):
        def buzzer():
            return self.device.status().buzzer

        self.device.set_buzzer(True)
        assert buzzer() is True

        self.device.set_buzzer(False)
        assert buzzer() is False

        # if user uses wrong type for buzzer value
        self.device.set_buzzer(1)
        assert buzzer() is True

        self.device.set_buzzer(0)
        assert buzzer() is False

        self.device.set_buzzer("not_empty_str")
        assert buzzer() is True

        self.device.set_buzzer("on")
        assert buzzer() is True

        # all string values are considered to by True, even "off"
        self.device.set_buzzer("off")
        assert buzzer() is True

        self.device.set_buzzer("")
        assert buzzer() is False

    def test_status_without_temperature(self):
        self.device._reset_state()
        self.device.state["temperature"] = None

        assert self.state().temperature is None

    def test_status_without_led_brightness(self):
        self.device._reset_state()
        self.device.state["led_brightness"] = None

        assert self.state().led_brightness is LedBrightness.Off

    def test_status_without_mode(self):
        self.device._reset_state()
        self.device.state["mode"] = None

        assert self.state().mode is OperationMode.Intelligent

    def test_set_child_lock(self):
        def child_lock():
            return self.device.status().child_lock

        self.device.set_child_lock(True)
        assert child_lock() is True

        self.device.set_child_lock(False)
        assert child_lock() is False

        # if user uses wrong type for buzzer value
        self.device.set_child_lock(1)
        assert child_lock() is True

        self.device.set_child_lock(0)
        assert child_lock() is False

        self.device.set_child_lock("not_empty_str")
        assert child_lock() is True

        self.device.set_child_lock("on")
        assert child_lock() is True

        # all string values are considered to by True, even "off"
        self.device.set_child_lock("off")
        assert child_lock() is True

        self.device.set_child_lock("")
        assert child_lock() is False
