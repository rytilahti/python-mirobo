from unittest import TestCase

import pytest

from miio import Huizuo, HuizuoLampFan, HuizuoLampHeater
from miio.huizuo import MODEL_HUIZUO_FANWY  # Fan model extended
from miio.huizuo import MODEL_HUIZUO_FANWY2  # Fan model basic
from miio.huizuo import MODEL_HUIZUO_PIS123  # Basic model
from miio.huizuo import MODEL_HUIZUO_WYHEAT  # Heater model
from miio.huizuo import HuizuoException

from .dummies import DummyMiotDevice

_INITIAL_STATE = {
    "power": True,
    "brightness": 60,
    "color_temp": 4000,
}

_INITIAL_STATE_FAN = {
    "power": True,
    "brightness": 60,
    "color_temp": 4000,
    "fan_power": False,
    "fan_level": 60,
    "fan_motor_reverse": True,
    "fan_mode": 1,
}

_INITIAL_STATE_HEATER = {
    "power": True,
    "brightness": 60,
    "color_temp": 4000,
    "heater_power": True,
    "heat_level": 2,
}


class DummyHuizuo(DummyMiotDevice, Huizuo):
    def __init__(self, *args, **kwargs):
        self.state = _INITIAL_STATE
        self._model = MODEL_HUIZUO_PIS123
        super().__init__(*args, **kwargs)


class DummyHuizuoFan(DummyMiotDevice, HuizuoLampFan):
    def __init__(self, *args, **kwargs):
        self.state = _INITIAL_STATE_FAN
        self._model = MODEL_HUIZUO_FANWY
        super().__init__(*args, **kwargs)


class DummyHuizuoFan2(DummyMiotDevice, HuizuoLampFan):
    def __init__(self, *args, **kwargs):
        self.state = _INITIAL_STATE_FAN
        self._model = MODEL_HUIZUO_FANWY2
        super().__init__(*args, **kwargs)


class DummyHuizuoHeater(DummyMiotDevice, HuizuoLampHeater):
    def __init__(self, *args, **kwargs):
        self.state = _INITIAL_STATE_HEATER
        self._model = MODEL_HUIZUO_WYHEAT
        super().__init__(*args, **kwargs)


@pytest.fixture(scope="function")
def huizuo(request):
    request.cls.device = DummyHuizuo()


@pytest.fixture(scope="function")
def huizuo_fan(request):
    request.cls.device = DummyHuizuoFan()


@pytest.fixture(scope="function")
def huizuo_fan2(request):
    request.cls.device = DummyHuizuoFan2()


@pytest.fixture(scope="function")
def huizuo_heater(request):
    request.cls.device = DummyHuizuoHeater()


@pytest.mark.usefixtures("huizuo")
class TestHuizuo(TestCase):
    def test_on(self):
        self.device.off()  # ensure off
        assert self.device.status().is_on is False

        self.device.on()
        assert self.device.status().is_on is True

    def test_off(self):
        self.device.on()  # ensure on
        assert self.device.status().is_on is True

        self.device.off()
        assert self.device.status().is_on is False

    def test_status(self):
        status = self.device.status()
        assert status.is_on is _INITIAL_STATE["power"]
        assert status.brightness is _INITIAL_STATE["brightness"]
        assert status.color_temp is _INITIAL_STATE["color_temp"]

    def test_brightness(self):
        def lamp_brightness():
            return self.device.status().brightness

        self.device.set_brightness(1)
        assert lamp_brightness() == 1
        self.device.set_brightness(64)
        assert lamp_brightness() == 64
        self.device.set_brightness(100)
        assert lamp_brightness() == 100

        with pytest.raises(HuizuoException):
            self.device.set_brightness(-1)

        with pytest.raises(HuizuoException):
            self.device.set_brightness(101)

    def test_color_temp(self):
        def lamp_color_temp():
            return self.device.status().color_temp

        self.device.set_color_temp(3000)
        assert lamp_color_temp() == 3000
        self.device.set_color_temp(4200)
        assert lamp_color_temp() == 4200
        self.device.set_color_temp(6400)
        assert lamp_color_temp() == 6400

        with pytest.raises(HuizuoException):
            self.device.set_color_temp(2999)

        with pytest.raises(HuizuoException):
            self.device.set_color_temp(6401)


@pytest.mark.usefixtures("huizuo_fan")
class TestHuizuoFan(TestCase):
    def test_fan_on(self):
        self.device.fan_off()  # ensure off
        assert self.device.status().is_fan_on is False

        self.device.fan_on()
        assert self.device.status().is_fan_on is True

    def test_fan_off(self):
        self.device.fan_on()  # ensure on
        assert self.device.status().is_fan_on is True

        self.device.fan_off()
        assert self.device.status().is_fan_on is False

    def test_fan_status(self):
        status = self.device.status()
        assert status.is_fan_on is _INITIAL_STATE_FAN["fan_power"]
        assert status.fan_speed_level is _INITIAL_STATE_FAN["fan_level"]
        assert status.is_fan_reverse is _INITIAL_STATE_FAN["fan_motor_reverse"]
        assert status.fan_mode is _INITIAL_STATE_FAN["fan_mode"]

    def test_fan_level(self):
        def fan_level():
            return self.device.status().fan_speed_level

        self.device.set_fan_level(0)
        assert fan_level() == 0
        self.device.set_fan_level(100)
        assert fan_level() == 100

        with pytest.raises(HuizuoException):
            self.device.set_fan_level(-1)

        with pytest.raises(HuizuoException):
            self.device.set_fan_level(101)

    def test_fan_motor_reverse(self):
        def fan_reverse():
            return self.device.status().is_fan_reverse

        self.device.fan_reverse_on()
        assert fan_reverse() is True
        self.device.fan_reverse_off()
        assert fan_reverse() is False

    def test_fan_mode(self):
        def fan_mode():
            return self.device.status().fan_mode

        self.device.set_basic_fan_mode()
        assert fan_mode() == 0
        self.device.set_natural_fan_mode()
        assert fan_mode() == 1


@pytest.mark.usefixtures("huizuo_fan2")
class TestHuizuoFan2(TestCase):
    # This device has no 'reverse' mode, so let's check this
    def test_fan_motor_reverse(self):
        with pytest.raises(HuizuoException):
            self.device.fan_reverse_on()

        with pytest.raises(HuizuoException):
            self.device.fan_reverse_off()


@pytest.mark.usefixtures("huizuo_heater")
class TestHuizuoHeater(TestCase):
    def test_heater_on(self):
        self.device.heater_off()  # ensure off
        assert self.device.status().is_heater_on is False

        self.device.heater_on()
        assert self.device.status().is_heater_on is True

    def test_heater_off(self):
        self.device.heater_on()  # ensure on
        assert self.device.status().is_heater_on is True

        self.device.heater_off()
        assert self.device.status().is_heater_on is False

    def test_heat_level(self):
        def heat_level():
            return self.device.status().heat_level

        self.device.set_heat_level(1)
        assert heat_level() == 1
        self.device.set_heat_level(3)
        assert heat_level() == 3

        with pytest.raises(HuizuoException):
            self.device.set_heat_level(0)
        with pytest.raises(HuizuoException):
            self.device.set_heat_level(4)
