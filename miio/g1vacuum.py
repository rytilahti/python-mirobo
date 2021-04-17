import logging
from typing import Any, Dict
from enum import Enum
import click
from .click_common import EnumType, command, format_output
from .miot_device import MiotDevice

_LOGGER = logging.getLogger(__name__)

_MAPPING = {
    # https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:vacuum:0000A006:mijia-v1:1
    "battery": {"siid": 3, "piid": 1},
    "charge_state": {"siid": 3, "piid": 2},
    "error": {"siid": 2, "piid": 2},
    "state": {"siid": 2, "piid": 1},
    "fan_speed": {"siid": 2, "piid": 6},
    "operating_mode": {"siid": 2, "piid": 4},
    "mop_state": {"siid": 16, "piid": 1},
    "water_level": {"siid": 2, "piid": 5},
    "brush_life_level": {"siid": 14, "piid": 1},
    #  "brush_life_time": {"siid": 14, "piid": 2},
    "brush_life_level2": {"siid": 15, "piid": 1},
    #  "brush_life_time2": {"siid": 15, "piid": 2},
    "filter_life_level": {"siid": 11, "piid": 1},
    #  "filter_life_time": {"siid": 11, "piid": 2},
    "clean_area": {"siid": 9, "piid": 1},
    "clean_time": {"siid": 18, "piid": 5},
    "total_clean_count": {"siid": 9, "piid": 5},
    #   "total_clean_area": {"siid": 9, "piid": 3},
    #  "dnd_enabled": {"siid": 12, "piid": 2},
    #  "audio_volume": {"siid": 4, "piid": 2},
    #  "direction_key": {"siid": 8, "piid": 1}
}

class ChargeState(Enum):
    Not_charging = 0
    Charging = 1
    Charging_competely = 2

class Error(Enum):
    Left_wheel_error = 1
    Right_wheel_error = 2
    Cliff_error = 3
    Low_battery_error = 4
    Bump_error = 5
    Main_brush_error = 6
    Side_brush_error = 7
    Fan_motor_error = 8
    Dustbin_error = 9
    Charging_error = 10
    No_water_error = 11
    Everything_is_ok = 0
    Pick_up_error = 12

class State(Enum):
    """Vacuum Status"""
    Idle = 1
    Sweeping = 2
    Paused = 3
    Error = 4
    Charging = 5
    Go_Charging = 6

class VacuumMode(Enum):
    """Vacuum Mode"""
    Global_clean = 1
    Spot_clean = 2
    Wiping = 3

class WaterLevel(Enum):
    """Water Flow Level"""
    Level1 = 1
    Level2 = 2
    Level3 = 3

class FanSpeed(Enum):
    """Fan speeds, same as for ViomiVacuum."""
    Mute = 0
    Standard = 1
    Medium = 2
    High = 3

class Languages(Enum):
    Chinese = 0
    English = 1

class MopState(Enum):
    Off = 0
    On = 1

class MovementDirection(Enum):
    Left = 0
    Right = 1
    Forward = 2
    Backward = 3
    Stop = 4

class G1Status:
    """Container for status reports from the Mijia Vacuum G1."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data = data

    @property
    def battery(self) -> int:
        """Battery Level."""
        return self.data["battery"]

    @property
    def charge_state(self) -> ChargeState:
        """Charging State."""
        return ChargeState[ChargeState(self.data["charge_state"]).name]

    @property
    def error(self) -> Error:
        """Error Message."""
        return Error[Error(self.data["error"]).name]

    @property
    def state(self) -> State:
        """Vacuum Status."""
        return State[State(self.data["state"]).name]

    @property
    def fan_speed(self) -> FanSpeed:
        """Fan Speed."""
        return FanSpeed[FanSpeed(self.data["fan_speed"]).name]

    @property
    def operating_mode(self) -> VacuumMode:
        """Operating Mode."""
        return VacuumMode[VacuumMode(self.data["operating_mode"]).name]

    @property
    def mop_state(self) -> MopState:
        """Mop State."""
        return MopState[MopState(self.data["mop_state"]).name]

    @property
    def water_level(self) -> WaterLevel:
        """Mop State."""
        return WaterLevel[WaterLevel(self.data["water_level"]).name]

    @property
    def brush_life_level(self) -> int:
        """Brush Life Level."""
        return self.data["brush_life_level"]

    @property
    def brush_life_level2(self) -> int:
        """Side Brush Life Level."""
        return self.data["brush_life_level2"]

    @property
    def filter_life_level(self) -> int:
        """Filter Life Level."""
        return self.data["filter_life_level"]

    @property
    def clean_area(self) -> int:
        """Clean Area."""
        return self.data["clean_area"]

    @property
    def clean_time(self) -> int:
        """Clean Time."""
        return self.data["clean_time"]

    @property
    def total_clean_count(self) -> int:
        """Total Clean Count."""
        return self.data["total_clean_count"]

    # @property
    # def total_clean_area(self) -> int:
        # """Total Clean Area."""
        # return self.data["total_clean_area"]

    def __repr__(self) -> str:
        ret = (
            "<VacuumStatus battery=%s, "
            "state=%s, "
            "error=%s, "
            "charge_state=%s, "
            "fanspeed=%s, "
            "mode=%s, "
            "mopstate=%s, "
            "waterlevel=%s, "
            "brushlevel=%s, "
            "sidebrushlevel=%s, "
            "filterlife=%s, "
            "cleanarea=%s, "
            "cleantime=%s, "
            "totalcleancount=%s, "
            % (
                self.battery,
                self.state,
                self.error,
                self.charge_state,
                self.fan_speed,
                self.operating_mode,
                self.mop_state,
                self.water_level,
                self.brush_life_level,
                self.brush_life_level2,
                self.filter_life_level,
                self.clean_area,
                self.clean_time,
                self.total_clean_count,
            )
        )
        return ret

class G1Vacuum(MiotDevice):
    """Support for G1 vacuum (G1, mijia.vacuum.v2)."""

    def __init__(
            self,
            ip: str = None,
            token: str = None,
            start_id: int = 0,
            debug: int = 0,
            lazy_discover: bool = True,
    ) -> None:
        super().__init__(_MAPPING, ip, token, start_id, debug, lazy_discover)

    @command(
        default_output=format_output(
            "",
            "State: {result.state}\n"
            "Error: {result.error}\n"
            "Battery: {result.battery}%\n"
            "Mode: {result.operating_mode}\n"
            "Mop State: {result.mop_state}\n"
            "Charge Status: {result.charge_state}\n"
            "Fan speed: {result.fan_speed}\n"
            "Water level: {result.water_level}\n"
            "Filter Life Level: {result.filter_life_level}%\n"
            "Brush Life Level: {result.brush_life_level}%\n"
            "Side Brush Life Level: {result.brush_life_level2}%\n"
            "Clean Area: {result.clean_area}\n"
            "Clean Time: {result.clean_time}\n"
            #  "Total Clean Area: {result.total_clean_area}\n"
            "Total Clean Count: {result.total_clean_count}\n",
        )
    )

    def status(self) -> G1Status:
        """Retrieve properties."""

        return G1Status(
            {
                prop["did"]: prop["value"] if prop["code"] == 0 else None
                for prop in self.get_properties_for_mapping()
            }
        )

    def call_action(self, siid, aiid, params=None):
        """Call Action"""
        # {"did":"<mydeviceID>","siid":18,"aiid":1,"in":[{"piid":1,"value":2}]
        if params is None:
            params = []
        payload = {
            "did": f"call-{siid}-{aiid}",
            "siid": siid,
            "aiid": aiid,
            "in": params,
        }
        return self.send("action", payload)

    @command()
    def return_home(self) -> None:
        """Return Home."""
        return self.call_action(2, 3)

    @command()
    def start(self) -> None:
        """Start Cleaning"""
        return self.call_action(2, 1)

    @command()
    def stop(self) -> None:
        """Stop Cleaning"""
        return self.call_action(2, 2)

    @command()
    def find(self) -> None:
        """Find the robot."""
        return self.call_action(6, 1)

    @command()
    def reset_brush_life(self) -> None:
        """Reset Brush Life."""
        return self.call_action(14, 1)

    @command()
    def reset_filter_life(self) -> None:
        """Reset Filter Life."""
        return self.call_action(11, 1)

    @command()
    def reset_brush_life2(self) -> None:
        """Reset Brush Life"""
        return self.call_action(15, 1)

    @command(
        click.argument("fan_speed", type=EnumType(FanSpeed)),
        default_output=format_output("Setting fan speed to {fan_speed}"),
    )
    def set_fan_speed(self, fan_speed: FanSpeed):
        """Set fan speed."""
        return self.set_property("fan_speed", fan_speed.value)
