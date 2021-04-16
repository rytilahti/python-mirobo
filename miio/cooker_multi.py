import enum
import logging
import math
from collections import defaultdict
from typing import List, Optional

import click
import crcmod

from .click_common import command, format_output
from .device import Device, DeviceStatus
from .exceptions import DeviceException

_LOGGER = logging.getLogger(__name__)

MODEL_MULTI = "chunmi.cooker.eh1"

COOKING_STAGES = {
    1: {
        "name": "Quickly preheat",
        "description": "Increase temperature in a controlled manner to soften rice",
    },
    2: {
        "name": "Absorb water at moderate temp.",
        "description": "Increase temperature steadily and let rice absorb enough water to provide full grains and a taste of fragrance and sweetness.",
    },
    3: {
        "name": "Operate at full load to boil rice",
        "description": "Keep heating at high temperature. Let rice to receive thermal energy uniformly.",
    },
    4: {
        "name": "Operate at full load to boil rice",
        "description": "Keep heating at high temperature. Let rice to receive thermal energy uniformly.",
    },
    5: {
        "name": "Operate at full load to boil rice",
        "description": "Keep heating at high temperature. Let rice to receive thermal energy uniformly.",
    },
    6: {
        "name": "Operate at full load to boil rice",
        "description": "Keep heating at high temperature. Let rice to receive thermal energy uniformly.",
    },
    7: {
        "name": "Ultra high",
        "description": "High-temperature steam generates crystal clear rice grains and saves its original sweet taste.",
    },
    9: {
        "name": "Cook rice over a slow fire",
        "description": "Keep rice warm uniformly to lock lateral heat inside. So the rice will get gelatinized sufficiently.",
    },
    10: {
        "name": "Cook rice over a slow fire",
        "description": "Keep rice warm uniformly to lock lateral heat inside. So the rice will get gelatinized sufficiently.",
    },
}

COOKING_MENUS = {
    "0000000000000000000000000000000000000001": "Fine Rice",
    "0101000000000000000000000000000000000002": "Quick Rice",
    "0202000000000000000000000000000000000003": "Congee",
    "0303000000000000000000000000000000000004": "Keep warm",
}


class CookerException(DeviceException):
    pass


class OperationMode(enum.Enum):
    Waiting = 1
    Running = 2
    AutoKeepWarm = 3
    PreCook = 4

    Unknown = "unknown"

    @classmethod
    def _missing_(cls, value):
        return OperationMode.Unknown


class TemperatureHistory(DeviceStatus):
    def __init__(self, data: str):
        """Container of temperatures recorded every 10-15 seconds while cooking.

        Example values:

        Status waiting:
        0

        2 minutes:
        161515161c242a3031302f2eaa2f2f2e2f

        12 minutes:
        161515161c242a3031302f2eaa2f2f2e2f2e302f2e2d302f2f2e2f2f2f2f343a3f3f3d3e3c3d3c3f3d3d3d3f3d3d3d3d3e3d3e3c3f3f3d3e3d3e3e3d3f3d3c3e3d3d3e3d3f3e3d3f3e3d3c

        32 minutes:
        161515161c242a3031302f2eaa2f2f2e2f2e302f2e2d302f2f2e2f2f2f2f343a3f3f3d3e3c3d3c3f3d3d3d3f3d3d3d3d3e3d3e3c3f3f3d3e3d3e3e3d3f3d3c3e3d3d3e3d3f3e3d3f3e3d3c3f3e3d3c3f3e3d3c3f3f3d3d3e3d3d3f3f3d3d3f3f3e3d3d3d3e3e3d3daa3f3f3f3f3f414446474a4e53575e5c5c5b59585755555353545454555554555555565656575757575858585859595b5b5c5c5c5c5d5daa5d5e5f5f606061

        55 minutes:
        161515161c242a3031302f2eaa2f2f2e2f2e302f2e2d302f2f2e2f2f2f2f343a3f3f3d3e3c3d3c3f3d3d3d3f3d3d3d3d3e3d3e3c3f3f3d3e3d3e3e3d3f3d3c3e3d3d3e3d3f3e3d3f3e3d3c3f3e3d3c3f3e3d3c3f3f3d3d3e3d3d3f3f3d3d3f3f3e3d3d3d3e3e3d3daa3f3f3f3f3f414446474a4e53575e5c5c5b59585755555353545454555554555555565656575757575858585859595b5b5c5c5c5c5d5daa5d5e5f5f60606161616162626263636363646464646464646464646464646464646464646364646464646464646464646464646464646464646464646464646464aa5a59585756555554545453535352525252525151515151

        Data structure:

        Octet 1 (16): First temperature measurement in hex (22 °C)
        Octet 2 (15): Second temperature measurement in hex (21 °C)
        Octet 3 (15): Third temperature measurement in hex (21 °C)
        ...
        """
        if not len(data) % 2:
            self.data = [int(data[i : i + 2], 16) for i in range(0, len(data), 2)]
        else:
            self.data = []

    @property
    def temperatures(self) -> List[int]:
        return self.data

    @property
    def raw(self) -> str:
        return "".join(["{:02x}".format(value) for value in self.data])

    def __str__(self) -> str:
        return str(self.data)


class MultiCookerProfile:
    """This class can be used to modify and validate an existing cooking profile."""

    def __init__(self, profile_hex: str, duration: int, schedule: int, akw: bool):
        if len(profile_hex) < 5:
            raise CookerException("Invalid profile")
        else:
            self.checksum = bytearray.fromhex(profile_hex)[-2:]
            self.profile_bytes = bytearray.fromhex(profile_hex)[:-2]

            if not self.is_valid():
                raise CookerException("Profile checksum error")

            if duration is not None:
                self.set_duration(duration)
            if schedule is not None:
                self.set_schedule_enabled(True)
                self.set_schedule_duration(schedule)
            if akw is not None:
                self.set_akw_enabled(akw)

    def is_set_duration_allowed(self):
        return (
            self.profile_bytes[10] != self.profile_bytes[12]
            or self.profile_bytes[11] != self.profile_bytes[13]
        )

    def get_duration(self):
        """Get the duration in minutes."""
        return (self.profile_bytes[8] * 60) + self.profile_bytes[9]

    def set_duration(self, minutes):
        """Set the duration in minutes if the profile allows it."""
        if not self.is_set_duration_allowed():
            return

        max_minutes = (self.profile_bytes[10] * 60) + self.profile_bytes[11]
        min_minutes = (self.profile_bytes[12] * 60) + self.profile_bytes[13]

        if minutes < min_minutes or minutes > max_minutes:
            return

        self.profile_bytes[8] = math.floor(minutes / 60)
        self.profile_bytes[9] = minutes % 60

        self.update_checksum()

    def is_schedule_enabled(self):
        return (self.profile_bytes[14] & 0x80) == 0x80

    def set_schedule_enabled(self, enabled):
        if enabled:
            self.profile_bytes[14] |= 0x80
        else:
            self.profile_bytes[14] &= 0x7F

        self.update_checksum()

    def set_schedule_duration(self, duration):
        """Set the schedule time (delay before cooking) in minutes."""
        if duration > 1440:
            return

        schedule_flag = self.profile_bytes[14] & 0x80
        self.profile_bytes[14] = math.floor(duration / 60) & 0xFF
        self.profile_bytes[14] |= schedule_flag
        self.profile_bytes[15] = (duration % 60 | self.profile_bytes[15] & 0x80) & 0xFF

        self.update_checksum()

    def is_akw_enabled(self):
        return (self.profile_bytes[15] & 0x80) == 0x80

    def set_akw_enabled(self, enabled):
        if enabled:
            self.profile_bytes[15] |= 0x80
        else:
            self.profile_bytes[15] &= 0x7F

        self.update_checksum()

    def calc_checksum(self):
        crc = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0x0, xorOut=0x0)(
            self.profile_bytes
        )
        checksum = bytearray(2)
        checksum[0] = (crc >> 8) & 0xFF
        checksum[1] = crc & 0xFF
        return checksum

    def update_checksum(self):
        self.checksum = self.calc_checksum()

    def is_valid(self):
        return len(self.profile_bytes) == 174 and self.checksum == self.calc_checksum()

    def get_profile_hex(self):
        return (self.profile_bytes + self.checksum).hex()


class CookerStatus(DeviceStatus):
    def __init__(self, data):
        self.data = data

    @property
    def mode(self) -> OperationMode:
        """Current operation mode."""
        return OperationMode(self.data["status"])

    @property
    def menu(self) -> int:
        """Selected menu id."""
        try:
            return COOKING_MENUS[self.data["menu"]]
        except KeyError:
            return "Unknown menu"

    @property
    def stage(self) -> int:
        """Current stage if cooking."""
        try:
            return COOKING_STAGES[self.data["phase"]]["name"]
        except KeyError:
            return "Unknown stage"

    @property
    def temperature(self) -> Optional[int]:
        """Current temperature, if idle.

        Example values: 29
        """
        return self.data["temp"]

    @property
    def start_time(self) -> int:
        """Start time of cooking?"""
        return int(self.data["t_start"])

    @property
    def remaining(self) -> int:
        """Remaining minutes of the cooking process."""
        return int(int(self.data["t_left"]) / 60)

    @property
    def cooking_delayed(self) -> Optional[int]:
        """Wait n minutes before cooking / scheduled cooking."""
        delay = int(self.data["t_pre"])

        if delay >= 0:
            return delay

        return None

    @property
    def duration(self) -> int:
        """Duration of the cooking process."""
        return int(self.data["t_cook"])

    @property
    def keep_warm(self) -> bool:
        """Keep warm after cooking?"""
        return self.data["akw"] == 1

    @property
    def settings(self) -> None:
        """Settings of the cooker."""
        return None

    @property
    def hardware_version(self) -> None:
        """Hardware version."""
        return None

    @property
    def firmware_version(self) -> None:
        """Firmware version."""
        return None

    @property
    def taste(self) -> None:
        """Taste id."""
        return self.data["taste"]

    @property
    def rice(self) -> None:
        """Rice id."""
        return self.data["rice"]

    @property
    def favorite(self) -> None:
        """Favored recipe id."""
        return self.data["favs"]


class MultiCooker(Device):
    """Main class representing the multi cooker."""

    @command(
        default_output=format_output(
            "",
            "Mode: {result.mode}\n"
            "Menu: {result.menu}\n"
            "Stage: {result.stage}\n"
            "Temperature: {result.temperature}\n"
            "Remaining: {result.remaining}\n"
            "Cooking delayed: {result.cooking_delayed}\n"
            "Duration: {result.duration}\n"
            "Keep warm: {result.keep_warm}\n"
            "Rice: {result.rice}\n"
            "Taste: {result.taste}\n"
            "Favorite: {result.favorite}\n",
        )
    )
    def status(self) -> CookerStatus:
        """Retrieve properties."""
        properties = [
            "status",
            "phase",
            "menu",
            "t_cook",
            "t_left",
            "t_pre",
            "t_kw",
            "taste",
            "temp",
            "rice",
            "favs",
            "akw",
            "t_start",
            "t_finish",
            "version",
            "setting",
            "code",
            "en_warm",
            "t_congee",
            "t_love",
            "boil",
        ]

        values = []
        for prop in properties:
            values.append(self.send("get_prop", [prop])[0])

        properties_count = len(properties)
        values_count = len(values)
        if properties_count != values_count:
            _LOGGER.debug(
                "Count (%s) of requested properties does not match the "
                "count (%s) of received values.",
                properties_count,
                values_count,
            )

        return CookerStatus(defaultdict(lambda: None, zip(properties, values)))

    @command(
        click.argument("profile", type=str, required=True),
        click.option("--duration", type=int, required=False),
        click.option("--schedule", type=int, required=False),
        click.option("--akw", type=bool, required=False),
        default_output=format_output("Cooking profile started"),
    )
    def start(self, profile: str, duration: int, schedule: int, akw: bool):
        """Start cooking a profile."""
        cookerProfile = MultiCookerProfile(profile, duration, schedule, akw)
        self.send("set_start", [cookerProfile.get_profile_hex()])

    @command(default_output=format_output("Cooking stopped"))
    def stop(self):
        """Stop cooking."""
        self.send("cancel_cooking", [])

    @command(
        click.argument("profile", type=str),
        click.option("--duration", type=int, required=False),
        click.option("--schedule", type=int, required=False),
        click.option("--akw", type=bool, required=False),
        default_output=format_output("Setting menu to {profile}"),
    )
    def menu(self, profile: str, duration: int, schedule: int, akw: bool):
        """Select one of the default(?) cooking profiles."""
        cookerProfile = MultiCookerProfile(profile, duration, schedule, akw)
        self.send("set_menu", [cookerProfile.get_profile_hex()])

    @command(default_output=format_output("", "Temperature history: {result}\n"))
    def get_temperature_history(self) -> TemperatureHistory:
        """Retrieves a temperature history.

        The temperature is only available while cooking. Approx. six data points per
        minute.
        """
        return TemperatureHistory(self.send("get_temp_history")[0])
