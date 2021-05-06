from unittest import TestCase

import pytest

from miio import AirDehumidifier
from miio.airdehumidifier import (
    MODEL_DEHUMIDIFIER_V1,
    AirDehumidifierException,
    AirDehumidifierStatus,
    FanSpeed,
    OperationMode,
)
from miio.device import DeviceInfo

from .dummies import DummyDevice


class DummyAirDehumidifierV1(DummyDevice, AirDehumidifier):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_DEHUMIDIFIER_V1
        self.dummy_device_info = {
            "life": 348202,
            "uid": 1759530000,
            "model": "nwt.derh.wdh318efw1",
            "token": "68ffffffffffffffffffffffffffffff",
            "fw_ver": "2.0.5",
            "mcu_fw_ver": "0018",
            "miio_ver": "0.0.5",
            "hw_ver": "esp32",
            "mmfree": 65476,
            "mac": "78:11:FF:FF:FF:FF",
            "wifi_fw_ver": "v3.1.4-56-g8ffb04960",
            "netif": {
                "gw": "192.168.0.1",
                "localIp": "192.168.0.25",
                "mask": "255.255.255.0",
            },
        }

        self.device_info = None

        self.state = {
            "on_off": "on",
            "mode": "auto",
            "fan_st": 2,
            "buzzer": "off",
            "led": "on",
            "child_lock": "off",
            "humidity": 48,
            "temp": 34,
            "compressor_status": "off",
            "fan_speed": 0,
            "tank_full": "off",
            "defrost_status": "off",
            "alarm": "ok",
            "auto": 50,
        }

        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("on_off", x),
            "set_mode": lambda x: self._set_state("mode", x),
            "set_led": lambda x: self._set_state("led", x),
            "set_buzzer": lambda x: self._set_state("buzzer", x),
            "set_child_lock": lambda x: self._set_state("child_lock", x),
            "set_fan_speed": lambda x: self._set_state("fan_st", x),
            "set_auto": lambda x: self._set_state("auto", x),
            "miIO.info": self._get_device_info,
        }
        super().__init__(args, kwargs)

    def _get_device_info(self, _):
        """Return dummy device info."""
        return self.dummy_device_info


@pytest.fixture(scope="class")
def airdehumidifierv1(request):
    request.cls.device = DummyAirDehumidifierV1()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airdehumidifierv1")
class TestAirDehumidifierV1(TestCase):
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

        device_info = DeviceInfo(self.device.dummy_device_info)

        assert repr(self.state()) == repr(
            AirDehumidifierStatus(self.device.start_state, device_info)
        )

        assert self.is_on() is True
        assert self.state().temperature == self.device.start_state["temp"]
        assert self.state().humidity == self.device.start_state["humidity"]
        assert self.state().mode == OperationMode(self.device.start_state["mode"])
        assert self.state().led == (self.device.start_state["led"] == "on")
        assert self.state().buzzer == (self.device.start_state["buzzer"] == "on")
        assert self.state().child_lock == (
            self.device.start_state["child_lock"] == "on"
        )
        assert self.state().target_humidity == self.device.start_state["auto"]
        assert self.state().fan_speed == FanSpeed(self.device.start_state["fan_speed"])
        assert self.state().tank_full == (self.device.start_state["tank_full"] == "on")
        assert self.state().compressor_status == (
            self.device.start_state["compressor_status"] == "on"
        )
        assert self.state().defrost_status == (
            self.device.start_state["defrost_status"] == "on"
        )
        assert self.state().fan_st == self.device.start_state["fan_st"]
        assert self.state().alarm == self.device.start_state["alarm"]

    def test_set_mode(self):
        def mode():
            return self.device.status().mode

        self.device.set_mode(OperationMode.On)
        assert mode() == OperationMode.On

        self.device.set_mode(OperationMode.Auto)
        assert mode() == OperationMode.Auto

        self.device.set_mode(OperationMode.DryCloth)
        assert mode() == OperationMode.DryCloth

    def test_set_led(self):
        def led():
            return self.device.status().led

        self.device.set_led(True)
        assert led() is True

        self.device.set_led(False)
        assert led() is False

    def test_set_buzzer(self):
        def buzzer():
            return self.device.status().buzzer

        self.device.set_buzzer(True)
        assert buzzer() is True

        self.device.set_buzzer(False)
        assert buzzer() is False

    def test_status_without_temperature(self):
        self.device._reset_state()
        self.device.state["temp"] = None

        assert self.state().temperature is None

    def test_set_target_humidity(self):
        def target_humidity():
            return self.device.status().target_humidity

        self.device.set_target_humidity(40)
        assert target_humidity() == 40
        self.device.set_target_humidity(50)
        assert target_humidity() == 50
        self.device.set_target_humidity(60)
        assert target_humidity() == 60

        with pytest.raises(AirDehumidifierException):
            self.device.set_target_humidity(-1)

        with pytest.raises(AirDehumidifierException):
            self.device.set_target_humidity(30)

        with pytest.raises(AirDehumidifierException):
            self.device.set_target_humidity(70)

        with pytest.raises(AirDehumidifierException):
            self.device.set_target_humidity(110)

    def test_set_child_lock(self):
        def child_lock():
            return self.device.status().child_lock

        self.device.set_child_lock(True)
        assert child_lock() is True

        self.device.set_child_lock(False)
        assert child_lock() is False
