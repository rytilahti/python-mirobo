from enum import Enum

import click

from .click_common import EnumType, command, format_output
from .miot_device import MiotDevice

_MAPPING = {
    # Source
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:curtain:0000A00C:babai-190812:1:0000C805
    # Curtain
    # "motor_control": {"siid": 2, "piid": 1},  # 0 - Pause, 1 - Open, 2 - Close
    "current_position": {"siid": 2, "piid": 2},  # Range: [0, 100, 1]
    "target_position": {"siid": 2, "piid": 4},  # Range: [0, 100, 1]
    "mode": {"siid": 2, 'piid': 4},  # 0 - Normal,  1 - Reversal, 2 - Calibrate
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


class BabaiCurtainMiot(MiotDevice):
    """Main class representing the babai.curtain.190812 curtain."""

    mapping = _MAPPING

    @command(
        click.argument("motor_control", type=EnumType(MotorControl)),
        default_output=format_output("Set motor control to {motor_control}"),
    )
    def set_motor_control(self, motor_control: MotorControl):
        """Set motor control."""
        return self.set_property("motor_control", motor_control.value)

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
