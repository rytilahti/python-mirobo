from enum import Enum
from time import sleep
from typing import Any, Dict, List

import click

from .click_common import EnumType, command, format_output
from .exceptions import DeviceError
from .miot_device import DeviceStatus, MiotDevice

_MAPPING = {
    # Source
    # http://miot-spec.org/miot-spec-v2/instances?status=all
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:curtain:0000A00C:babai-190812:1:0000C805
    # Curtain
    "motor_control": {"siid": 2, "piid": 1},  # 0 - Pause, 1 - Open, 2 - Close
    "current_position": {"siid": 2, "piid": 2},  # Range: [0, 100, 1]
    "target_position": {"siid": 2, "piid": 3},  # Range: [0, 100, 1]
    "mode": {"siid": 2, "piid": 4},  # 0 - Normal,  1 - Reversal, 2 - Calibrate
}

# Model: "OnViz Curtain Controller (Wi-Fi)"
MODEL_CURTAIN_BABAI = "babai.curtain.190812"


class MotorControl(Enum):
    Pause = 0
    Open = 1
    Close = 2


class Mode(Enum):
    Normal = 0
    Reverse = 1
    Calibrate = 2


class CurtainStatus(DeviceStatus):
    def __init__(self, data: Dict[str, Any]) -> None:
        """Response from device.

        {'motor_control': 0}
        """
        self.data = data

    @property
    def status(self) -> MotorControl:
        """Device status."""
        return MotorControl(self.data["motor_control"])

    @property
    def motor_control(self) -> MotorControl:
        """Device status."""
        return MotorControl(self.data["motor_control"])

    @property
    def is_open(self) -> bool:
        """Device status."""
        return self.motor_control == MotorControl.Open

    @property
    def is_close(self) -> bool:
        """Device status."""
        return self.motor_control == MotorControl.Close

    @property
    def mode(self) -> Mode:
        """Motor rotation polarity."""
        return Mode(self.data["mode"])

    @property
    def current_position(self) -> int:
        """Run time of the motor."""
        return self.data["current_position"]

    @property
    def target_position(self) -> int:
        """Target curtain position."""
        return self.data["target_position"]


class CurtainBabai(MiotDevice):
    """Main class representing the babai.curtain.190812 curtain."""

    mapping = _MAPPING

    @command(
        default_output=format_output(
            "",
            "Motor control: {result.motor_control}\n"
            "Motor mode: {result.mode}\n"
            "Current position: {result.current_position}\n"
            "Target position: {result.target_position}\n",
        )
    )
    def status(self) -> CurtainStatus:
        """Retrieve properties."""
        # if use get_properties_for_mapping and max_len>1 then code -4004.
        data = []
        for k, v in self.mapping.items():
            if "aiid" not in v:
                data.extend(self.get_property(k))
                # data[k] = prop["value"] if prop["code"] == 0 else None
        return CurtainStatus(self._extract_property_value(data))

    def get_property(self, name: str) -> List[Dict[str, Any]]:
        if name not in self.mapping:
            raise ValueError("key %s not in MAPING", name)
        v = self.mapping[name]
        try:
            prop = self.get_property_by(siid=v["siid"], piid=v["piid"])
        except DeviceError as e:
            if e.code == -9999:
                sleep(5)
                prop = self.get_property_by(siid=v["siid"], piid=v["piid"])
            else:
                raise
        for p in prop:
            p["did"] = name
        return prop

    @staticmethod
    def _extract_property_value(prop: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {p["did"]: p["value"] if p["code"] == 0 else None for p in prop}

    def _get_property_value(self, name: str) -> Any:
        prop = self.get_property(name)
        return self._extract_property_value(prop).get(name)

    @property
    def motor_control(self) -> MotorControl:
        """Device status."""
        return MotorControl(self._get_property_value("motor_control"))

    @property
    def mode(self) -> Mode:
        """Motor rotation polarity."""
        return Mode(self._get_property_value("mode"))

    @property
    def current_position(self) -> int:
        """Run time of the motor."""
        return self._get_property_value("current_position")

    @property
    def target_position(self) -> int:
        """Target curtain position."""
        return self._get_property_value("target_position")

    @command(
        click.argument("motor_control", type=EnumType(MotorControl)),
        default_output=format_output("Set motor control to {motor_control}"),
    )
    def set_motor_control(self, motor_control: MotorControl):
        """Set motor control."""
        return self.set_property("motor_control", motor_control.value)

    @command(
        click.argument("open"),
        default_output=format_output("Open curtain"),
    )
    def set_open(self):
        """Set motor control."""
        return self.set_motor_control(MotorControl.Open)

    @command(
        click.argument("close"),
        default_output=format_output("Close curtain"),
    )
    def set_close(self):
        """Set motor control."""
        return self.set_motor_control(MotorControl.Close)

    @property
    def is_open(self) -> bool:
        """Device status."""
        return self.motor_control == MotorControl.Open

    @property
    def is_close(self) -> bool:
        """Device status."""
        return self.motor_control == MotorControl.Close

    @command(
        click.argument("target_position", type=int),
        default_output=format_output("Set target position to {target_position}"),
    )
    def set_target_position(self, target_position: int):
        """Set target position."""
        if target_position < 0 or target_position > 100:
            raise ValueError(
                "Value must be between [0, 100] value, was %s" % target_position
            )
        return self.set_property("target_position", target_position)

    @command(
        click.argument("mode", type=EnumType(Mode)),
        default_output=format_output("Set mode to {mode}"),
    )
    def set_mode(self, mode: Mode):
        """Set mode of the motor."""
        return self.set_property("mode", mode.value)
