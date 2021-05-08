# -*- coding: UTF-8 -*#
from datetime import datetime, time, timedelta
from enum import IntEnum
from typing import Any, Dict, List, Optional, Union

from croniter import croniter

from .device import DeviceStatus
from .utils import pretty_seconds, pretty_time


def pretty_area(x: float) -> float:
    return int(x) / 1000000


error_codes = {  # from vacuum_cleaner-EN.pdf
    0: "No error",
    1: "Laser distance sensor error",
    2: "Collision sensor error",
    3: "Wheels on top of void, move robot",
    4: "Clean hovering sensors, move robot",
    5: "Clean main brush",
    6: "Clean side brush",
    7: "Main wheel stuck?",
    8: "Device stuck, clean area",
    9: "Dust collector missing",
    10: "Clean filter",
    11: "Stuck in magnetic barrier",
    12: "Low battery",
    13: "Charging fault",
    14: "Battery fault",
    15: "Wall sensors dirty, wipe them",
    16: "Place me on flat surface",
    17: "Side brushes problem, reboot me",
    18: "Suction fan problem",
    19: "Unpowered charging station",
    21: "Laser disance sensor blocked",
    22: "Clean the dock charging contacts",
    23: "Docking station not reachable",
    24: "No-go zone or invisible wall detected",
}


class VacuumStatus(DeviceStatus):
    """Container for status reports from the vacuum."""

    def __init__(self, data: Dict[str, Any]) -> None:
        # {'result': [{'state': 8, 'dnd_enabled': 1, 'clean_time': 0,
        #  'msg_ver': 4, 'map_present': 1, 'error_code': 0, 'in_cleaning': 0,
        #  'clean_area': 0, 'battery': 100, 'fan_power': 20, 'msg_seq': 320}],
        #  'id': 1}

        # v8 new items
        # clean_mode, begin_time, clean_trigger,
        # back_trigger, clean_strategy, and completed
        # TODO: create getters if wanted
        #
        # {"msg_ver":8,"msg_seq":60,"state":5,"battery":93,"clean_mode":0,
        # "fan_power":50,"error_code":0,"map_present":1,"in_cleaning":1,
        # "dnd_enabled":0,"begin_time":1534333389,"clean_time":21,
        # "clean_area":202500,"clean_trigger":2,"back_trigger":0,
        # "completed":0,"clean_strategy":1}

        # Example of S6 in the segment cleaning mode
        # new items: in_fresh_state, water_box_status, lab_status, map_status, lock_status
        #
        # [{'msg_ver': 2, 'msg_seq': 28, 'state': 18, 'battery': 95,
        # 'clean_time': 606, 'clean_area': 8115000, 'error_code': 0,
        # 'map_present': 1, 'in_cleaning': 3, 'in_returning': 0,
        # 'in_fresh_state': 0, 'lab_status': 1, 'water_box_status': 0,
        # 'fan_power': 102, 'dnd_enabled': 0, 'map_status': 3, 'lock_status': 0}]

        # Example of S7 in charging mode
        # new items: is_locating, water_box_mode, water_box_carriage_status,
        # mop_forbidden_enable, adbumper_status, water_shortage_status,
        # dock_type, dust_collection_status, auto_dust_collection, mop_mode, debug_mode
        #
        # [{'msg_ver': 2, 'msg_seq': 1839, 'state': 8, 'battery': 100,
        # 'clean_time': 2311, 'clean_area': 35545000, 'error_code': 0,
        # 'map_present': 1, 'in_cleaning': 0, 'in_returning': 0,
        # 'in_fresh_state': 1, 'lab_status': 3, 'water_box_status': 1,
        # 'fan_power': 102, 'dnd_enabled': 0, 'map_status': 3, 'is_locating': 0,
        # 'lock_status': 0, 'water_box_mode': 202, 'water_box_carriage_status': 0,
        # 'mop_forbidden_enable': 0, 'adbumper_status': [0, 0, 0],
        # 'water_shortage_status': 0, 'dock_type': 0, 'dust_collection_status': 0,
        # 'auto_dust_collection': 1,  'mop_mode': 300, 'debug_mode': 0}]
        self.data = data

    @property
    def state_code(self) -> int:
        """State code as returned by the device."""
        return int(self.data["state"])

    @property
    def state(self) -> str:
        """Human readable state description, see also :func:`state_code`."""
        states = {
            1: "Starting",
            2: "Charger disconnected",
            3: "Idle",
            4: "Remote control active",
            5: "Cleaning",
            6: "Returning home",
            7: "Manual mode",
            8: "Charging",
            9: "Charging problem",
            10: "Paused",
            11: "Spot cleaning",
            12: "Error",
            13: "Shutting down",
            14: "Updating",
            15: "Docking",
            16: "Going to target",
            17: "Zoned cleaning",
            18: "Segment cleaning",
            100: "Charging complete",
            101: "Device offline",
        }
        try:
            return states[int(self.state_code)]
        except KeyError:
            return "Definition missing for state %s" % self.state_code

    @property
    def error_code(self) -> int:
        """Error code as returned by the device."""
        return int(self.data["error_code"])

    @property
    def error(self) -> str:
        """Human readable error description, see also :func:`error_code`."""
        try:
            return error_codes[self.error_code]
        except KeyError:
            return "Definition missing for error %s" % self.error_code

    @property
    def battery(self) -> int:
        """Remaining battery in percentage."""
        return int(self.data["battery"])

    @property
    def fanspeed(self) -> int:
        """Current fan speed."""
        return int(self.data["fan_power"])

    @property
    def clean_time(self) -> timedelta:
        """Time used for cleaning (if finished, shows how long it took)."""
        return pretty_seconds(self.data["clean_time"])

    @property
    def clean_area(self) -> float:
        """Cleaned area in m2."""
        return pretty_area(self.data["clean_area"])

    @property
    def map(self) -> bool:
        """Map token."""
        return bool(self.data["map_present"])

    @property
    def in_zone_cleaning(self) -> bool:
        """Return True if the vacuum is in zone cleaning mode."""
        return self.data["in_cleaning"] == 2

    @property
    def in_segment_cleaning(self) -> bool:
        """Return True if the vacuum is in segment cleaning mode."""
        return self.data["in_cleaning"] == 3

    @property
    def is_paused(self) -> bool:
        """Return True if vacuum is paused."""
        return self.state_code == 10

    @property
    def is_on(self) -> bool:
        """True if device is currently cleaning in any mode."""
        return (
            self.state_code == 5
            or self.state_code == 7
            or self.state_code == 11
            or self.state_code == 17
            or self.state_code == 18
        )

    @property
    def is_water_box_attached(self) -> bool:
        """Return True is water box is installed."""
        return "water_box_status" in self.data and self.data["water_box_status"] == 1

    @property
    def is_water_box_carriage_attached(self) -> Optional[bool]:
        """Return True if water box carriage (mop) is installed, None if sensor not
        present."""
        if "water_box_carriage_status" in self.data:
            return self.data["water_box_carriage_status"] == 1
        else:
            return None

    @property
    def is_water_shortage(self) -> Optional[bool]:
        """Returns True if water is low in the tank, None if sensor not present."""
        if "water_shortage_status" in self.data:
            return self.data["water_shortage_status"] == 1
        else:
            return None

    @property
    def is_child_lock(self) -> bool:
        """Returns True if the child lock is active."""
        return self.data["lock_status"] == 1

    @property
    def got_error(self) -> bool:
        """True if an error has occured."""
        return self.error_code != 0


class CleaningSummary(DeviceStatus):
    """Contains summarized information about available cleaning runs."""

    def __init__(self, data: Union[List[Any], Dict[str, Any]]) -> None:
        # total duration, total area, amount of cleans
        # [ list, of, ids ]
        # { "result": [ 174145, 2410150000, 82,
        # [ 1488240000, 1488153600, 1488067200, 1487980800,
        #  1487894400, 1487808000, 1487548800 ] ],
        #  "id": 1 }
        # newer models return a dict
        if type(data) is list:
            self.data = {
                "clean_time": data[0],
                "clean_area": data[1],
                "clean_count": data[2],
            }
            if len(data) > 3:
                self.data["records"] = data[3]
        else:
            self.data = data

        if "records" not in self.data:
            self.data["records"] = []

    @property
    def total_duration(self) -> timedelta:
        """Total cleaning duration."""
        return pretty_seconds(self.data["clean_time"])

    @property
    def total_area(self) -> float:
        """Total cleaned area."""
        return pretty_area(self.data["clean_area"])

    @property
    def count(self) -> int:
        """Number of cleaning runs."""
        return int(self.data["clean_count"])

    @property
    def ids(self) -> List[int]:
        """A list of available cleaning IDs, see also :class:`CleaningDetails`."""
        return list(self.data["records"])

    @property
    def dust_collection_count(self) -> Optional[int]:
        """Total number of dust collections."""
        if "dust_collection_count" in self.data:
            return int(self.data["dust_collection_count"])
        else:
            return None


class CleaningDetails(DeviceStatus):
    """Contains details about a specific cleaning run."""

    def __init__(self, data: Union[List[Any], Dict[str, Any]]) -> None:
        # start, end, duration, area, unk, complete
        # { "result": [ [ 1488347071, 1488347123, 16, 0, 0, 0 ] ], "id": 1 }
        # newer models return a dict
        if type(data) is list:
            self.data = {
                "begin": data[0],
                "end": data[1],
                "duration": data[2],
                "area": data[3],
                "error": data[4],
                "complete": data[5],
            }
        else:
            self.data = data

    @property
    def start(self) -> datetime:
        """When cleaning was started."""
        return pretty_time(self.data["begin"])

    @property
    def end(self) -> datetime:
        """When cleaning was finished."""
        return pretty_time(self.data["end"])

    @property
    def duration(self) -> timedelta:
        """Total duration of the cleaning run."""
        return pretty_seconds(self.data["duration"])

    @property
    def area(self) -> float:
        """Total cleaned area."""
        return pretty_area(self.data["area"])

    @property
    def error_code(self) -> int:
        """Error code."""
        return int(self.data["error"])

    @property
    def error(self) -> str:
        """Error state of this cleaning run."""
        return error_codes[self.data["error"]]

    @property
    def complete(self) -> bool:
        """Return True if the cleaning run was complete (e.g. without errors).

        see also :func:`error`.
        """
        return bool(self.data["complete"] == 1)


class ConsumableStatus(DeviceStatus):
    """Container for consumable status information, including information about brushes
    and duration until they should be changed. The methods returning time left are based
    on the following lifetimes:

    - Sensor cleanup time: XXX FIXME
    - Main brush: 300 hours
    - Side brush: 200 hours
    - Filter: 150 hours
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        # {'id': 1, 'result': [{'filter_work_time': 32454,
        #  'sensor_dirty_time': 3798,
        # 'side_brush_work_time': 32454,
        #  'main_brush_work_time': 32454}]}
        self.data = data
        self.main_brush_total = timedelta(hours=300)
        self.side_brush_total = timedelta(hours=200)
        self.filter_total = timedelta(hours=150)
        self.sensor_dirty_total = timedelta(hours=30)

    @property
    def main_brush(self) -> timedelta:
        """Main brush usage time."""
        return pretty_seconds(self.data["main_brush_work_time"])

    @property
    def main_brush_left(self) -> timedelta:
        """How long until the main brush should be changed."""
        return self.main_brush_total - self.main_brush

    @property
    def side_brush(self) -> timedelta:
        """Side brush usage time."""
        return pretty_seconds(self.data["side_brush_work_time"])

    @property
    def side_brush_left(self) -> timedelta:
        """How long until the side brush should be changed."""
        return self.side_brush_total - self.side_brush

    @property
    def filter(self) -> timedelta:
        """Filter usage time."""
        return pretty_seconds(self.data["filter_work_time"])

    @property
    def filter_left(self) -> timedelta:
        """How long until the filter should be changed."""
        return self.filter_total - self.filter

    @property
    def sensor_dirty(self) -> timedelta:
        """Return ``sensor_dirty_time``"""
        return pretty_seconds(self.data["sensor_dirty_time"])

    @property
    def sensor_dirty_left(self) -> timedelta:
        return self.sensor_dirty_total - self.sensor_dirty


class DNDStatus(DeviceStatus):
    """A container for the do-not-disturb status."""

    def __init__(self, data: Dict[str, Any]):
        # {'end_minute': 0, 'enabled': 1, 'start_minute': 0,
        #  'start_hour': 22, 'end_hour': 8}
        self.data = data

    @property
    def enabled(self) -> bool:
        """True if DnD is enabled."""
        return bool(self.data["enabled"])

    @property
    def start(self) -> time:
        """Start time of DnD."""
        return time(hour=self.data["start_hour"], minute=self.data["start_minute"])

    @property
    def end(self) -> time:
        """End time of DnD."""
        return time(hour=self.data["end_hour"], minute=self.data["end_minute"])


class Timer(DeviceStatus):
    """A container for scheduling.

    The timers are accessed using an integer ID, which is based on the unix timestamp of
    the creation time.
    """

    def __init__(self, data: List[Any], timezone: "datetime.tzinfo") -> None:
        # id / timestamp, enabled, ['<cron string>', ['command', 'params']
        # [['1488667794112', 'off', ['49 22 * * 6', ['start_clean', '']]],
        #  ['1488667777661', 'off', ['49 21 * * 3,4,5,6', ['start_clean', '']]
        # ],
        self.data = data
        self.timezone = timezone

        # Initialize croniter to cause an exception on invalid entries (#847)
        self.croniter = croniter(
            self.cron, start_time=timezone.localize(datetime.now())
        )

    @property
    def id(self) -> int:
        """ID which can be used to point to this timer."""
        return int(self.data[0])

    @property
    def ts(self) -> datetime:
        """Pretty-printed ID (timestamp) presentation as time."""
        return pretty_time(int(self.data[0]) / 1000)

    @property
    def enabled(self) -> bool:
        """True if the timer is active."""
        return bool(self.data[1] == "on")

    @property
    def cron(self) -> str:
        """Cron-formated timer string."""
        return str(self.data[2][0])

    @property
    def action(self) -> str:
        """The action to be taken on the given time.

        Note, this seems to be always 'start'.
        """
        return str(self.data[2][1])

    @property
    def next_schedule(self) -> datetime:
        """Next schedule for the timer."""
        return self.croniter.get_next(ret_type=datetime)


class SoundStatus(DeviceStatus):
    """Container for sound status."""

    def __init__(self, data):
        # {'sid_in_progress': 0, 'sid_in_use': 1004}
        self.data = data

    @property
    def current(self):
        return self.data["sid_in_use"]

    @property
    def being_installed(self):
        return self.data["sid_in_progress"]


class SoundInstallState(IntEnum):
    Unknown = 0
    Downloading = 1
    Installing = 2
    Installed = 3
    Error = 4


class SoundInstallStatus(DeviceStatus):
    """Container for sound installation status."""

    def __init__(self, data):
        # {'progress': 0, 'sid_in_progress': 0, 'state': 0, 'error': 0}
        # error 0 = no error
        # error 1 = unknown 1
        # error 2 = download error
        # error 3 = checksum error
        # error 4 = unknown 4

        self.data = data

    @property
    def state(self) -> SoundInstallState:
        """Installation state."""
        return SoundInstallState(self.data["state"])

    @property
    def progress(self) -> int:
        """Progress in percentages."""
        return self.data["progress"]

    @property
    def sid(self) -> int:
        """Sound ID for the sound being installed."""
        # this is missing on install confirmation, so let's use get
        return self.data.get("sid_in_progress", None)

    @property
    def error(self) -> int:
        """Error code, 0 is no error, other values unknown."""
        return self.data["error"]

    @property
    def is_installing(self) -> bool:
        """True if install is in progress."""
        return (
            self.state == SoundInstallState.Downloading
            or self.state == SoundInstallState.Installing
        )

    @property
    def is_errored(self) -> bool:
        """True if the state has an error, use `error` to access it."""
        return self.state == SoundInstallState.Error


class CarpetModeStatus(DeviceStatus):
    """Container for carpet mode status."""

    def __init__(self, data):
        # {'current_high': 500, 'enable': 1, 'current_integral': 450,
        #  'current_low': 400, 'stall_time': 10}
        self.data = data

    @property
    def enabled(self) -> bool:
        """True if carpet mode is enabled."""
        return self.data["enable"] == 1

    @property
    def stall_time(self) -> int:
        return self.data["stall_time"]

    @property
    def current_low(self) -> int:
        return self.data["current_low"]

    @property
    def current_high(self) -> int:
        return self.data["current_high"]

    @property
    def current_integral(self) -> int:
        return self.data["current_integral"]
