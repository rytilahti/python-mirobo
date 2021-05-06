from unittest import TestCase

import pytest

from miio import AirHumidifierMjjsq
from miio.airhumidifier_mjjsq import (
    MODEL_HUMIDIFIER_JSQ1,
    AirHumidifierException,
    AirHumidifierStatus,
    OperationMode,
)

from .dummies import DummyDevice


class DummyAirHumidifierMjjsq(DummyDevice, AirHumidifierMjjsq):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_HUMIDIFIER_JSQ1
        self.state = {
            "Humidifier_Gear": 1,
            "Humidity_Value": 44,
            "HumiSet_Value": 11,
            "Led_State": 0,
            "OnOff_State": 1,
            "TemperatureValue": 21,
            "TipSound_State": 0,
            "waterstatus": 1,
            "watertankstatus": 1,
            "wet_and_protect": 1,
        }
        self.return_values = {
            "get_prop": self._get_state,
            "Set_OnOff": lambda x: self._set_state("OnOff_State", x),
            "Set_HumidifierGears": lambda x: self._set_state("Humidifier_Gear", x),
            "SetLedState": lambda x: self._set_state("Led_State", x),
            "SetTipSound_Status": lambda x: self._set_state("TipSound_State", x),
            "Set_HumiValue": lambda x: self._set_state("HumiSet_Value", x),
            "Set_wet_and_protect": lambda x: self._set_state("wet_and_protect", x),
        }
        super().__init__(args, kwargs)


@pytest.fixture(scope="class")
def airhumidifiermjjsq(request):
    request.cls.device = DummyAirHumidifierMjjsq()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airhumidifiermjjsq")
class TestAirHumidifierMjjsq(TestCase):
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
        assert self.is_on() is True
        assert self.state().temperature == self.device.start_state["TemperatureValue"]
        assert self.state().humidity == self.device.start_state["Humidity_Value"]
        assert self.state().mode == OperationMode(
            self.device.start_state["Humidifier_Gear"]
        )
        assert self.state().led is (self.device.start_state["Led_State"] == 1)
        assert self.state().buzzer is (self.device.start_state["TipSound_State"] == 1)
        assert self.state().target_humidity == self.device.start_state["HumiSet_Value"]
        assert self.state().no_water is (self.device.start_state["waterstatus"] == 0)
        assert self.state().water_tank_detached is (
            self.device.start_state["watertankstatus"] == 0
        )

    def test_set_mode(self):
        def mode():
            return self.device.status().mode

        self.device.set_mode(OperationMode.Low)
        assert mode() == OperationMode.Low

        self.device.set_mode(OperationMode.Medium)
        assert mode() == OperationMode.Medium

        self.device.set_mode(OperationMode.High)
        assert mode() == OperationMode.High

        self.device.set_mode(OperationMode.Humidity)
        assert mode() == OperationMode.Humidity

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

    def test_set_target_humidity(self):
        def target_humidity():
            return self.device.status().target_humidity

        self.device.set_target_humidity(0)
        assert target_humidity() == 0
        self.device.set_target_humidity(50)
        assert target_humidity() == 50
        self.device.set_target_humidity(99)
        assert target_humidity() == 99

        with pytest.raises(AirHumidifierException):
            self.device.set_target_humidity(-1)

        with pytest.raises(AirHumidifierException):
            self.device.set_target_humidity(100)

        with pytest.raises(AirHumidifierException):
            self.device.set_target_humidity(101)

    def test_set_wet_protection(self):
        def wet_protection():
            return self.device.status().wet_protection

        self.device.set_wet_protection(True)
        assert wet_protection() is True

        self.device.set_wet_protection(False)
        assert wet_protection() is False
