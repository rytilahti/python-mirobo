import json
import os
import string
from unittest import TestCase

import pytest

from miio import (
    AirConditioningCompanion,
    AirConditioningCompanionMcn02,
    AirConditioningCompanionV3,
)
from miio.airconditioningcompanion import (
    MODEL_ACPARTNER_V3,
    STORAGE_SLOT_ID,
    AirConditioningCompanionException,
    AirConditioningCompanionStatus,
    FanSpeed,
    Led,
    OperationMode,
    Power,
    SwingMode,
)
from miio.airconditioningcompanionMCN import MODEL_ACPARTNER_MCN02
from miio.airconditioningcompanionMCN import (
    AirConditioningCompanionStatus as AirConditioningCompanionStatusMcn02,
)
from miio.airconditioningcompanionMCN import FanSpeed as FanSpeedMcn02
from miio.airconditioningcompanionMCN import OperationMode as OperationModeMcn02
from miio.airconditioningcompanionMCN import SwingMode as SwingModeMcn02
from miio.tests.dummies import DummyDevice

STATE_ON = ["on"]
STATE_OFF = ["off"]

PUBLIC_ENUMS = {
    "OperationMode": OperationMode,
    "FanSpeed": FanSpeed,
    "Power": Power,
    "SwingMode": SwingMode,
    "Led": Led,
}


def as_enum(d):
    if "__enum__" in d:
        name, member = d["__enum__"].split(".")
        return getattr(PUBLIC_ENUMS[name], member)
    else:
        return d


with open(
    os.path.join(os.path.dirname(__file__), "test_airconditioningcompanion.json")
) as inp:
    test_data = json.load(inp, object_hook=as_enum)


class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj) in PUBLIC_ENUMS.values():
            return {"__enum__": str(obj)}
        return json.JSONEncoder.default(self, obj)


class DummyAirConditioningCompanion(DummyDevice, AirConditioningCompanion):
    def __init__(self, *args, **kwargs):
        self.state = ["010500978022222102", "01020119A280222221", "2"]
        self.last_ir_played = None

        self.return_values = {
            "get_model_and_state": self._get_state,
            "start_ir_learn": lambda x: True,
            "end_ir_learn": lambda x: True,
            "get_ir_learn_result": lambda x: True,
            "send_ir_code": lambda x: self._send_input_validation(x),
            "send_cmd": lambda x: self._send_input_validation(x),
            "set_power": lambda x: self._set_power(x),
        }
        self.start_state = self.state.copy()
        super().__init__(args, kwargs)

    def _reset_state(self):
        """Revert back to the original state."""
        self.state = self.start_state.copy()

    def _get_state(self, props):
        """Return the requested data."""
        return self.state

    def _set_power(self, value: str):
        """Set the requested power state."""
        if value == STATE_ON:
            self.state[1] = self.state[1][:2] + "1" + self.state[1][3:]

        if value == STATE_OFF:
            self.state[1] = self.state[1][:2] + "0" + self.state[1][3:]

    @staticmethod
    def _hex_input_validation(payload):
        return all(c in string.hexdigits for c in payload[0])

    def _send_input_validation(self, payload):
        if self._hex_input_validation(payload[0]):
            self.last_ir_played = payload[0]
            return True

        return False

    def get_last_ir_played(self):
        return self.last_ir_played


@pytest.fixture(scope="class")
def airconditioningcompanion(request):
    request.cls.device = DummyAirConditioningCompanion()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airconditioningcompanion")
class TestAirConditioningCompanion(TestCase):
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
            AirConditioningCompanionStatus(
                dict(model_and_state=self.device.start_state)
            )
        )

        assert self.is_on() is False
        assert self.state().power_socket is None
        assert self.state().load_power == 2
        assert self.state().air_condition_model == bytes.fromhex("010500978022222102")
        assert self.state().model_format == 1
        assert self.state().device_type == 5
        assert self.state().air_condition_brand == int("0097", 16)
        assert self.state().air_condition_remote == int("80222221", 16)
        assert self.state().state_format == 2
        assert self.state().air_condition_configuration == "020119A2"
        assert self.state().target_temperature == 25
        assert self.state().swing_mode == SwingMode.Off
        assert self.state().fan_speed == FanSpeed.Low
        assert self.state().mode == OperationMode.Auto
        assert self.state().led is False

    def test_status_without_target_temperature(self):
        self.device._reset_state()
        self.device.state[1] = None
        assert self.state().target_temperature is None

    def test_status_without_swing_mode(self):
        self.device._reset_state()
        self.device.state[1] = None
        assert self.state().swing_mode is None

    def test_status_without_mode(self):
        self.device._reset_state()
        self.device.state[1] = None
        assert self.state().mode is None

    def test_status_without_fan_speed(self):
        self.device._reset_state()
        self.device.state[1] = None
        assert self.state().fan_speed is None

    def test_learn(self):
        assert self.device.learn(STORAGE_SLOT_ID) is True
        assert self.device.learn() is True

    def test_learn_result(self):
        assert self.device.learn_result() is True

    def test_learn_stop(self):
        assert self.device.learn_stop(STORAGE_SLOT_ID) is True
        assert self.device.learn_stop() is True

    def test_send_ir_code(self):
        for args in test_data["test_send_ir_code_ok"]:
            with self.subTest():
                self.device._reset_state()
                self.assertTrue(self.device.send_ir_code(*args["in"]))
                self.assertSequenceEqual(self.device.get_last_ir_played(), args["out"])

        for args in test_data["test_send_ir_code_exception"]:
            with pytest.raises(AirConditioningCompanionException):
                self.device.send_ir_code(*args["in"])

    def test_send_command(self):
        assert self.device.send_command("0000000") is True

    def test_send_configuration(self):

        for args in test_data["test_send_configuration_ok"]:
            with self.subTest():
                self.device._reset_state()
                self.assertTrue(self.device.send_configuration(*args["in"]))
                self.assertSequenceEqual(self.device.get_last_ir_played(), args["out"])


class DummyAirConditioningCompanionV3(DummyDevice, AirConditioningCompanionV3):
    def __init__(self, *args, **kwargs):
        self.state = ["010507950000257301", "011001160100002573", "807"]
        self.device_prop = {"lumi.0": {"plug_state": ["on"]}}
        self._model = MODEL_ACPARTNER_V3
        self.last_ir_played = None

        self.return_values = {
            "get_model_and_state": self._get_state,
            "get_device_prop": self._get_device_prop,
            "toggle_plug": self._toggle_plug,
        }
        self.start_state = self.state.copy()
        self.start_device_prop = self.device_prop.copy()
        super().__init__(args, kwargs)

    def _reset_state(self):
        """Revert back to the original state."""
        self.state = self.start_state.copy()

    def _get_state(self, props):
        """Return the requested data."""
        return self.state

    def _get_device_prop(self, props):
        """Return the requested data."""
        return self.device_prop[props[0]][props[1]]

    def _toggle_plug(self, props):
        """Toggle the lumi.0 plug state."""
        self.device_prop["lumi.0"]["plug_state"] = [props.pop()]


@pytest.fixture(scope="class")
def airconditioningcompanionv3(request):
    request.cls.device = DummyAirConditioningCompanionV3()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airconditioningcompanionv3")
class TestAirConditioningCompanionV3(TestCase):
    def state(self):
        return self.device.status()

    def is_on(self):
        return self.device.status().is_on

    def test_socket_on(self):
        self.device.socket_off()  # ensure off
        assert self.state().power_socket == "off"

        self.device.socket_on()
        assert self.state().power_socket == "on"

    def test_socket_off(self):
        self.device.socket_on()  # ensure on
        assert self.state().power_socket == "on"

        self.device.socket_off()
        assert self.state().power_socket == "off"

    def test_status(self):
        self.device._reset_state()

        assert repr(self.state()) == repr(
            AirConditioningCompanionStatus(
                dict(
                    model_and_state=self.device.start_state,
                    power_socket=self.device.start_device_prop["lumi.0"]["plug_state"][
                        0
                    ],
                )
            )
        )

        assert self.is_on() is True
        assert self.state().power_socket == "on"
        assert self.state().load_power == 807
        assert self.state().air_condition_model == bytes.fromhex("010507950000257301")
        assert self.state().model_format == 1
        assert self.state().device_type == 5
        assert self.state().air_condition_brand == int("0795", 16)
        assert self.state().air_condition_remote == int("00002573", 16)
        assert self.state().state_format == 1
        assert self.state().air_condition_configuration == "10011601"
        assert self.state().target_temperature == 22
        assert self.state().swing_mode == SwingMode.Off
        assert self.state().fan_speed == FanSpeed.Low
        assert self.state().mode == OperationMode.Heat
        assert self.state().led is True


class DummyAirConditioningCompanionMcn02(DummyDevice, AirConditioningCompanionMcn02):
    def __init__(self, *args, **kwargs):
        self.state = ["on", "cool", 28, "small_fan", "on", 441.0]
        self._model = MODEL_ACPARTNER_MCN02

        self.return_values = {"get_prop": self._get_state}
        self.start_state = self.state.copy()
        super().__init__(args, kwargs)

    def _reset_state(self):
        """Revert back to the original state."""
        self.state = self.start_state.copy()

    def _get_state(self, props):
        """Return the requested data."""
        return self.state


@pytest.fixture(scope="class")
def airconditioningcompanionMcn02(request):
    request.cls.device = DummyAirConditioningCompanionMcn02()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("airconditioningcompanionMcn02")
class TestAirConditioningCompanionMcn02(TestCase):
    def state(self):
        return self.device.status()

    def is_on(self):
        return self.device.status().is_on

    def test_status(self):
        self.device._reset_state()

        assert repr(self.state()) == repr(
            AirConditioningCompanionStatusMcn02(self.device.start_state)
        )

        assert self.is_on() is True
        assert self.state().target_temperature == 28
        assert self.state().swing_mode == SwingModeMcn02.On
        assert self.state().fan_speed == FanSpeedMcn02.Low
        assert self.state().mode == OperationModeMcn02.Cool
