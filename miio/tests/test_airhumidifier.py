from unittest import TestCase

import pytest

from miio import AirHumidifier
from miio.airhumidifier import (
    MODEL_HUMIDIFIER_CA1,
    MODEL_HUMIDIFIER_CB1,
    MODEL_HUMIDIFIER_V1,
    AirHumidifierException,
    AirHumidifierStatus,
    LedBrightness,
    OperationMode,
)
from miio.device import DeviceInfo

from .dummies import DummyDevice


class DummyAirHumidifierV1(DummyDevice, AirHumidifier):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_HUMIDIFIER_V1
        self.dummy_device_info = {
            "fw_ver": "1.2.9_5033",
            "token": "68ffffffffffffffffffffffffffffff",
            "otu_stat": [101, 74, 5343, 0, 5327, 407],
            "mmfree": 228248,
            "netif": {
                "gw": "192.168.0.1",
                "localIp": "192.168.0.25",
                "mask": "255.255.255.0",
            },
            "ott_stat": [0, 0, 0, 0],
            "model": "zhimi.humidifier.v1",
            "cfg_time": 0,
            "life": 575661,
            "ap": {"rssi": -35, "ssid": "ap", "bssid": "FF:FF:FF:FF:FF:FF"},
            "wifi_fw_ver": "SD878x-14.76.36.p84-702.1.0-WM",
            "hw_ver": "MW300",
            "ot": "otu",
            "mac": "78:11:FF:FF:FF:FF",
        }
        self.device_info = None

        self.state = {
            "power": "on",
            "mode": "medium",
            "temp_dec": 294,
            "humidity": 33,
            "buzzer": "off",
            "led_b": 2,
            "child_lock": "on",
            "limit_hum": 40,
            "trans_level": 85,
            "use_time": 941100,
            "button_pressed": "led",
            "hw_version": 0,
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_mode": lambda x: self._set_state("mode", x),
            "set_led_b": lambda x: self._set_state("led_b", x),
            "set_buzzer": lambda x: self._set_state("buzzer", x),
            "set_child_lock": lambda x: self._set_state("child_lock", x),
            "set_limit_hum": lambda x: self._set_state("limit_hum", x),
            "miIO.info": self._get_device_info,
        }
        super().__init__(args, kwargs)

    def _get_device_info(self, _):
        """Return dummy device info."""
        return self.dummy_device_info


@pytest.fixture(scope="class")
def airhumidifierv1(request):
    request.cls.device = DummyAirHumidifierV1()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airhumidifierv1")
class TestAirHumidifierV1(TestCase):
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
            AirHumidifierStatus(self.device.start_state, device_info)
        )

        assert self.is_on() is True
        assert self.state().temperature == self.device.start_state["temp_dec"] / 10.0
        assert self.state().humidity == self.device.start_state["humidity"]
        assert self.state().mode == OperationMode(self.device.start_state["mode"])
        assert self.state().led_brightness == LedBrightness(
            self.device.start_state["led_b"]
        )
        assert self.state().buzzer == (self.device.start_state["buzzer"] == "on")
        assert self.state().child_lock == (
            self.device.start_state["child_lock"] == "on"
        )
        assert self.state().target_humidity == self.device.start_state["limit_hum"]
        assert self.state().trans_level == self.device.start_state["trans_level"]
        assert self.state().motor_speed is None
        assert self.state().depth is None
        assert self.state().dry is None
        assert self.state().use_time == self.device.start_state["use_time"]
        assert self.state().hardware_version == self.device.start_state["hw_version"]
        assert self.state().button_pressed == self.device.start_state["button_pressed"]

        assert self.state().firmware_version == device_info.firmware_version
        assert (
            self.state().firmware_version_major
            == device_info.firmware_version.rsplit("_", 1)[0]
        )
        assert self.state().firmware_version_minor == int(
            device_info.firmware_version.rsplit("_", 1)[1]
        )
        assert self.state().strong_mode_enabled is False

    def test_set_mode(self):
        def mode():
            return self.device.status().mode

        self.device.set_mode(OperationMode.Silent)
        assert mode() == OperationMode.Silent

        self.device.set_mode(OperationMode.Medium)
        assert mode() == OperationMode.Medium

        self.device.set_mode(OperationMode.High)
        assert mode() == OperationMode.High

    def test_set_led_brightness(self):
        def led_brightness():
            return self.device.status().led_brightness

        self.device.set_led_brightness(LedBrightness.Bright)
        assert led_brightness() == LedBrightness.Bright

        self.device.set_led_brightness(LedBrightness.Dim)
        assert led_brightness() == LedBrightness.Dim

        self.device.set_led_brightness(LedBrightness.Off)
        assert led_brightness() == LedBrightness.Off

    def test_set_led(self):
        def led_brightness():
            return self.device.status().led_brightness

        self.device.set_led(True)
        assert led_brightness() == LedBrightness.Bright

        self.device.set_led(False)
        assert led_brightness() == LedBrightness.Off

    def test_set_buzzer(self):
        def buzzer():
            return self.device.status().buzzer

        self.device.set_buzzer(True)
        assert buzzer() is True

        self.device.set_buzzer(False)
        assert buzzer() is False

    def test_status_without_temperature(self):
        self.device._reset_state()
        self.device.state["temp_dec"] = None

        assert self.state().temperature is None

    def test_status_without_led_brightness(self):
        self.device._reset_state()
        self.device.state["led_b"] = None

        assert self.state().led_brightness is None

    def test_set_target_humidity(self):
        def target_humidity():
            return self.device.status().target_humidity

        self.device.set_target_humidity(30)
        assert target_humidity() == 30
        self.device.set_target_humidity(60)
        assert target_humidity() == 60
        self.device.set_target_humidity(80)
        assert target_humidity() == 80

        with pytest.raises(AirHumidifierException):
            self.device.set_target_humidity(-1)

        with pytest.raises(AirHumidifierException):
            self.device.set_target_humidity(20)

        with pytest.raises(AirHumidifierException):
            self.device.set_target_humidity(90)

        with pytest.raises(AirHumidifierException):
            self.device.set_target_humidity(110)

    def test_set_child_lock(self):
        def child_lock():
            return self.device.status().child_lock

        self.device.set_child_lock(True)
        assert child_lock() is True

        self.device.set_child_lock(False)
        assert child_lock() is False


class DummyAirHumidifierCA1(DummyDevice, AirHumidifier):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_HUMIDIFIER_CA1
        self.dummy_device_info = {
            "fw_ver": "1.6.6",
            "token": "68ffffffffffffffffffffffffffffff",
            "otu_stat": [101, 74, 5343, 0, 5327, 407],
            "mmfree": 228248,
            "netif": {
                "gw": "192.168.0.1",
                "localIp": "192.168.0.25",
                "mask": "255.255.255.0",
            },
            "ott_stat": [0, 0, 0, 0],
            "model": "zhimi.humidifier.v1",
            "cfg_time": 0,
            "life": 575661,
            "ap": {"rssi": -35, "ssid": "ap", "bssid": "FF:FF:FF:FF:FF:FF"},
            "wifi_fw_ver": "SD878x-14.76.36.p84-702.1.0-WM",
            "hw_ver": "MW300",
            "ot": "otu",
            "mac": "78:11:FF:FF:FF:FF",
        }
        self.device_info = None

        self.state = {
            "power": "on",
            "mode": "medium",
            "temp_dec": 294,
            "humidity": 33,
            "buzzer": "off",
            "led_b": 2,
            "child_lock": "on",
            "limit_hum": 40,
            "use_time": 941100,
            "hw_version": 0,
            # Additional attributes of the zhimi.humidifier.ca1
            "speed": 100,
            "depth": 1,
            "dry": "off",
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_mode": lambda x: self._set_state("mode", x),
            "set_led_b": lambda x: self._set_state("led_b", [int(x[0])]),
            "set_buzzer": lambda x: self._set_state("buzzer", x),
            "set_child_lock": lambda x: self._set_state("child_lock", x),
            "set_limit_hum": lambda x: self._set_state("limit_hum", x),
            "set_dry": lambda x: self._set_state("dry", x),
            "miIO.info": self._get_device_info,
        }
        super().__init__(args, kwargs)

    def _get_device_info(self, _):
        """Return dummy device info."""
        return self.dummy_device_info


@pytest.fixture(scope="class")
def airhumidifierca1(request):
    request.cls.device = DummyAirHumidifierCA1()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airhumidifierca1")
class TestAirHumidifierCA1(TestCase):
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
            AirHumidifierStatus(self.device.start_state, device_info)
        )

        assert self.is_on() is True
        assert self.state().temperature == self.device.start_state["temp_dec"] / 10.0
        assert self.state().humidity == self.device.start_state["humidity"]
        assert self.state().mode == OperationMode(self.device.start_state["mode"])
        assert self.state().led_brightness == LedBrightness(
            self.device.start_state["led_b"]
        )
        assert self.state().buzzer == (self.device.start_state["buzzer"] == "on")
        assert self.state().child_lock == (
            self.device.start_state["child_lock"] == "on"
        )
        assert self.state().target_humidity == self.device.start_state["limit_hum"]
        assert self.state().trans_level is None
        assert self.state().motor_speed == self.device.start_state["speed"]
        assert self.state().depth == self.device.start_state["depth"]
        assert self.state().dry == (self.device.start_state["dry"] == "on")
        assert self.state().use_time == self.device.start_state["use_time"]
        assert self.state().hardware_version == self.device.start_state["hw_version"]
        assert self.state().button_pressed is None

        assert self.state().firmware_version == device_info.firmware_version
        assert (
            self.state().firmware_version_major
            == device_info.firmware_version.rsplit("_", 1)[0]
        )

        try:
            version_minor = int(device_info.firmware_version.rsplit("_", 1)[1])
        except IndexError:
            version_minor = 0

        assert self.state().firmware_version_minor == version_minor
        assert self.state().strong_mode_enabled is False

    def test_set_mode(self):
        def mode():
            return self.device.status().mode

        self.device.set_mode(OperationMode.Silent)
        assert mode() == OperationMode.Silent

        self.device.set_mode(OperationMode.Medium)
        assert mode() == OperationMode.Medium

        self.device.set_mode(OperationMode.High)
        assert mode() == OperationMode.High

    def test_set_led_brightness(self):
        def led_brightness():
            return self.device.status().led_brightness

        self.device.set_led_brightness(LedBrightness.Bright)
        assert led_brightness() == LedBrightness.Bright

        self.device.set_led_brightness(LedBrightness.Dim)
        assert led_brightness() == LedBrightness.Dim

        self.device.set_led_brightness(LedBrightness.Off)
        assert led_brightness() == LedBrightness.Off

    def test_set_led(self):
        def led_brightness():
            return self.device.status().led_brightness

        self.device.set_led(True)
        assert led_brightness() == LedBrightness.Bright

        self.device.set_led(False)
        assert led_brightness() == LedBrightness.Off

    def test_set_buzzer(self):
        def buzzer():
            return self.device.status().buzzer

        self.device.set_buzzer(True)
        assert buzzer() is True

        self.device.set_buzzer(False)
        assert buzzer() is False

    def test_status_without_temperature(self):
        self.device._reset_state()
        self.device.state["temp_dec"] = None

        assert self.state().temperature is None

    def test_status_without_led_brightness(self):
        self.device._reset_state()
        self.device.state["led_b"] = None

        assert self.state().led_brightness is None

    def test_set_target_humidity(self):
        def target_humidity():
            return self.device.status().target_humidity

        self.device.set_target_humidity(30)
        assert target_humidity() == 30
        self.device.set_target_humidity(60)
        assert target_humidity() == 60
        self.device.set_target_humidity(80)
        assert target_humidity() == 80

        with pytest.raises(AirHumidifierException):
            self.device.set_target_humidity(-1)

        with pytest.raises(AirHumidifierException):
            self.device.set_target_humidity(20)

        with pytest.raises(AirHumidifierException):
            self.device.set_target_humidity(90)

        with pytest.raises(AirHumidifierException):
            self.device.set_target_humidity(110)

    def test_set_child_lock(self):
        def child_lock():
            return self.device.status().child_lock

        self.device.set_child_lock(True)
        assert child_lock() is True

        self.device.set_child_lock(False)
        assert child_lock() is False

    def test_set_dry(self):
        def dry():
            return self.device.status().dry

        self.device.set_dry(True)
        assert dry() is True

        self.device.set_dry(False)
        assert dry() is False


class DummyAirHumidifierCB1(DummyDevice, AirHumidifier):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_HUMIDIFIER_CB1
        self.dummy_device_info = {
            "fw_ver": "1.2.9_5033",
            "token": "68ffffffffffffffffffffffffffffff",
            "otu_stat": [101, 74, 5343, 0, 5327, 407],
            "mmfree": 228248,
            "netif": {
                "gw": "192.168.0.1",
                "localIp": "192.168.0.25",
                "mask": "255.255.255.0",
            },
            "ott_stat": [0, 0, 0, 0],
            "model": "zhimi.humidifier.v1",
            "cfg_time": 0,
            "life": 575661,
            "ap": {"rssi": -35, "ssid": "ap", "bssid": "FF:FF:FF:FF:FF:FF"},
            "wifi_fw_ver": "SD878x-14.76.36.p84-702.1.0-WM",
            "hw_ver": "MW300",
            "ot": "otu",
            "mac": "78:11:FF:FF:FF:FF",
        }
        self.device_info = None

        self.state = {
            "power": "on",
            "mode": "medium",
            "humidity": 33,
            "buzzer": "off",
            "led_b": 2,
            "child_lock": "on",
            "limit_hum": 40,
            "use_time": 941100,
            "hw_version": 0,
            # Additional attributes of the zhimi.humidifier.cb1
            "temperature": 29.4,
            "speed": 100,
            "depth": 1,
            "dry": "off",
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_mode": lambda x: self._set_state("mode", x),
            "set_led_b": lambda x: self._set_state("led_b", [int(x[0])]),
            "set_buzzer": lambda x: self._set_state("buzzer", x),
            "set_child_lock": lambda x: self._set_state("child_lock", x),
            "set_limit_hum": lambda x: self._set_state("limit_hum", x),
            "set_dry": lambda x: self._set_state("dry", x),
            "miIO.info": self._get_device_info,
        }
        super().__init__(args, kwargs)

    def _get_device_info(self, _):
        """Return dummy device info."""
        return self.dummy_device_info


@pytest.fixture(scope="class")
def airhumidifiercb1(request):
    request.cls.device = DummyAirHumidifierCB1()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airhumidifiercb1")
class TestAirHumidifierCB1(TestCase):
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
            AirHumidifierStatus(self.device.start_state, device_info)
        )

        assert self.is_on() is True
        assert self.state().temperature == self.device.start_state["temperature"]
        assert self.state().humidity == self.device.start_state["humidity"]
        assert self.state().mode == OperationMode(self.device.start_state["mode"])
        assert self.state().led_brightness == LedBrightness(
            self.device.start_state["led_b"]
        )
        assert self.state().buzzer == (self.device.start_state["buzzer"] == "on")
        assert self.state().child_lock == (
            self.device.start_state["child_lock"] == "on"
        )
        assert self.state().target_humidity == self.device.start_state["limit_hum"]
        assert self.state().trans_level is None
        assert self.state().motor_speed == self.device.start_state["speed"]
        assert self.state().depth == self.device.start_state["depth"]
        assert self.state().dry == (self.device.start_state["dry"] == "on")
        assert self.state().use_time == self.device.start_state["use_time"]
        assert self.state().hardware_version == self.device.start_state["hw_version"]
        assert self.state().button_pressed is None

        assert self.state().firmware_version == device_info.firmware_version
        assert (
            self.state().firmware_version_major
            == device_info.firmware_version.rsplit("_", 1)[0]
        )
        assert self.state().firmware_version_minor == int(
            device_info.firmware_version.rsplit("_", 1)[1]
        )
        assert self.state().strong_mode_enabled is False

    def test_set_mode(self):
        def mode():
            return self.device.status().mode

        self.device.set_mode(OperationMode.Silent)
        assert mode() == OperationMode.Silent

        self.device.set_mode(OperationMode.Medium)
        assert mode() == OperationMode.Medium

        self.device.set_mode(OperationMode.High)
        assert mode() == OperationMode.High

    def test_set_led_brightness(self):
        def led_brightness():
            return self.device.status().led_brightness

        self.device.set_led_brightness(LedBrightness.Bright)
        assert led_brightness() == LedBrightness.Bright

        self.device.set_led_brightness(LedBrightness.Dim)
        assert led_brightness() == LedBrightness.Dim

        self.device.set_led_brightness(LedBrightness.Off)
        assert led_brightness() == LedBrightness.Off

    def test_set_led(self):
        def led_brightness():
            return self.device.status().led_brightness

        self.device.set_led(True)
        assert led_brightness() == LedBrightness.Bright

        self.device.set_led(False)
        assert led_brightness() == LedBrightness.Off

    def test_set_buzzer(self):
        def buzzer():
            return self.device.status().buzzer

        self.device.set_buzzer(True)
        assert buzzer() is True

        self.device.set_buzzer(False)
        assert buzzer() is False

    def test_status_without_temperature(self):
        self.device._reset_state()
        self.device.state["temperature"] = None

        assert self.state().temperature is None

    def test_status_without_led_brightness(self):
        self.device._reset_state()
        self.device.state["led_b"] = None

        assert self.state().led_brightness is None

    def test_set_target_humidity(self):
        def target_humidity():
            return self.device.status().target_humidity

        self.device.set_target_humidity(30)
        assert target_humidity() == 30
        self.device.set_target_humidity(60)
        assert target_humidity() == 60
        self.device.set_target_humidity(80)
        assert target_humidity() == 80

        with pytest.raises(AirHumidifierException):
            self.device.set_target_humidity(-1)

        with pytest.raises(AirHumidifierException):
            self.device.set_target_humidity(20)

        with pytest.raises(AirHumidifierException):
            self.device.set_target_humidity(90)

        with pytest.raises(AirHumidifierException):
            self.device.set_target_humidity(110)

    def test_set_child_lock(self):
        def child_lock():
            return self.device.status().child_lock

        self.device.set_child_lock(True)
        assert child_lock() is True

        self.device.set_child_lock(False)
        assert child_lock() is False

    def test_set_dry(self):
        def dry():
            return self.device.status().dry

        self.device.set_dry(True)
        assert dry() is True

        self.device.set_dry(False)
        assert dry() is False
