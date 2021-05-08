import contextlib
import datetime
import enum
import json
import logging
import math
import os
import pathlib
import time
from typing import Dict, List, Optional, Union

import click
import pytz
from appdirs import user_cache_dir

from .click_common import (
    DeviceGroup,
    EnumType,
    GlobalContextObject,
    LiteralParamType,
    command,
)
from .device import Device
from .exceptions import DeviceException, DeviceInfoUnavailableException
from .vacuumcontainers import (
    CarpetModeStatus,
    CleaningDetails,
    CleaningSummary,
    ConsumableStatus,
    DNDStatus,
    SoundInstallStatus,
    SoundStatus,
    Timer,
    VacuumStatus,
)

_LOGGER = logging.getLogger(__name__)


class VacuumException(DeviceException):
    pass


class TimerState(enum.Enum):
    On = "on"
    Off = "off"


class Consumable(enum.Enum):
    MainBrush = "main_brush_work_time"
    SideBrush = "side_brush_work_time"
    Filter = "filter_work_time"
    SensorDirty = "sensor_dirty_time"


class FanspeedV1(enum.Enum):
    Silent = 38
    Standard = 60
    Medium = 77
    Turbo = 90


class FanspeedV2(enum.Enum):
    Silent = 101
    Standard = 102
    Medium = 103
    Turbo = 104
    Gentle = 105


class FanspeedV3(enum.Enum):
    Silent = 38
    Standard = 60
    Medium = 75
    Turbo = 100


class FanspeedE2(enum.Enum):
    # Original names from the app: Gentle, Silent, Standard, Strong, Max
    Gentle = 41
    Silent = 50
    Standard = 68
    Medium = 79
    Turbo = 100


class FanspeedS7(enum.Enum):
    Quiet = 101
    Balanced = 102
    Turbo = 103
    Max = 104


class WaterFlow(enum.Enum):
    """Water flow strength on s5 max."""

    Minimum = 200
    Low = 201
    High = 202
    Maximum = 203


class MopMode(enum.Enum):
    """Mop routing on S7."""

    Standard = 300
    Deep = 301


ROCKROBO_V1 = "rockrobo.vacuum.v1"
ROCKROBO_S5 = "roborock.vacuum.s5"
ROCKROBO_S6 = "roborock.vacuum.s6"
ROCKROBO_S6_MAXV = "roborock.vacuum.a10"
ROCKROBO_S7 = "roborock.vacuum.a15"


class Vacuum(Device):
    """Main class representing the vacuum."""

    def __init__(
        self, ip: str, token: str = None, start_id: int = 0, debug: int = 0
    ) -> None:
        super().__init__(ip, token, start_id, debug)
        self.manual_seqnum = -1
        self.model = None
        self._fanspeeds = FanspeedV1

    @command()
    def start(self):
        """Start cleaning."""
        return self.send("app_start")

    @command()
    def stop(self):
        """Stop cleaning.

        Note, prefer 'pause' instead of this for wider support. Some newer vacuum models
        do not support this command.
        """
        return self.send("app_stop")

    @command()
    def spot(self):
        """Start spot cleaning."""
        return self.send("app_spot")

    @command()
    def pause(self):
        """Pause cleaning."""
        return self.send("app_pause")

    @command()
    def resume_or_start(self):
        """A shortcut for resuming or starting cleaning."""
        status = self.status()
        if status.in_zone_cleaning and (status.is_paused or status.got_error):
            return self.resume_zoned_clean()
        if status.in_segment_cleaning and (status.is_paused or status.got_error):
            return self.resume_segment_clean()

        return self.start()

    @command()
    def home(self):
        """Stop cleaning and return home."""
        if self.model is None:
            self._autodetect_model()

        SKIP_PAUSE = [
            ROCKROBO_S5,
            ROCKROBO_S6,
            ROCKROBO_S6_MAXV,
        ]

        if self.model not in SKIP_PAUSE:
            self.send("app_pause")

        return self.send("app_charge")

    @command(click.argument("x_coord", type=int), click.argument("y_coord", type=int))
    def goto(self, x_coord: int, y_coord: int):
        """Go to specific target.

        :param int x_coord: x coordinate
        :param int y_coord: y coordinate
        """
        return self.send("app_goto_target", [x_coord, y_coord])

    @command(click.argument("zones", type=LiteralParamType(), required=True))
    def zoned_clean(self, zones: List):
        """Clean zones.

        :param List zones: List of zones to clean: [[x1,y1,x2,y2, iterations],[x1,y1,x2,y2, iterations]]
        """
        return self.send("app_zoned_clean", zones)

    @command()
    def resume_zoned_clean(self):
        """Resume zone cleaning after being paused."""
        return self.send("resume_zoned_clean")

    @command()
    def manual_start(self):
        """Start manual control mode."""
        self.manual_seqnum = 0
        return self.send("app_rc_start")

    @command()
    def manual_stop(self):
        """Stop manual control mode."""
        self.manual_seqnum = 0
        return self.send("app_rc_end")

    MANUAL_ROTATION_MAX = 180
    MANUAL_ROTATION_MIN = -MANUAL_ROTATION_MAX
    MANUAL_VELOCITY_MAX = 0.3
    MANUAL_VELOCITY_MIN = -MANUAL_VELOCITY_MAX
    MANUAL_DURATION_DEFAULT = 1500

    @command(
        click.argument("rotation", type=int),
        click.argument("velocity", type=float),
        click.argument(
            "duration", type=int, required=False, default=MANUAL_DURATION_DEFAULT
        ),
    )
    def manual_control_once(
        self, rotation: int, velocity: float, duration: int = MANUAL_DURATION_DEFAULT
    ):
        """Starts the remote control mode and executes the action once before
        deactivating the mode."""
        number_of_tries = 3
        self.manual_start()
        while number_of_tries > 0:
            if self.status().state_code == 7:
                time.sleep(5)
                self.manual_control(rotation, velocity, duration)
                time.sleep(5)
                return self.manual_stop()

            time.sleep(2)
            number_of_tries -= 1

    @command(
        click.argument("rotation", type=int),
        click.argument("velocity", type=float),
        click.argument(
            "duration", type=int, required=False, default=MANUAL_DURATION_DEFAULT
        ),
    )
    def manual_control(
        self, rotation: int, velocity: float, duration: int = MANUAL_DURATION_DEFAULT
    ):
        """Give a command over manual control interface."""
        if rotation < self.MANUAL_ROTATION_MIN or rotation > self.MANUAL_ROTATION_MAX:
            raise DeviceException(
                "Given rotation is invalid, should be ]%s, %s[, was %s"
                % (self.MANUAL_ROTATION_MIN, self.MANUAL_ROTATION_MAX, rotation)
            )
        if velocity < self.MANUAL_VELOCITY_MIN or velocity > self.MANUAL_VELOCITY_MAX:
            raise DeviceException(
                "Given velocity is invalid, should be ]%s, %s[, was: %s"
                % (self.MANUAL_VELOCITY_MIN, self.MANUAL_VELOCITY_MAX, velocity)
            )

        self.manual_seqnum += 1
        params = {
            "omega": round(math.radians(rotation), 1),
            "velocity": velocity,
            "duration": duration,
            "seqnum": self.manual_seqnum,
        }

        self.send("app_rc_move", [params])

    @command()
    def status(self) -> VacuumStatus:
        """Return status of the vacuum."""
        return VacuumStatus(self.send("get_status")[0])

    def enable_log_upload(self):
        raise NotImplementedError("unknown parameters")
        # return self.send("enable_log_upload")

    @command()
    def log_upload_status(self):
        # {"result": [{"log_upload_status": 7}], "id": 1}
        return self.send("get_log_upload_status")

    @command()
    def consumable_status(self) -> ConsumableStatus:
        """Return information about consumables."""
        return ConsumableStatus(self.send("get_consumable")[0])

    @command(click.argument("consumable", type=Consumable))
    def consumable_reset(self, consumable: Consumable):
        """Reset consumable information."""
        return self.send("reset_consumable", [consumable.value])

    @command()
    def map(self):
        """Return map token."""
        # returns ['retry'] without internet
        return self.send("get_map_v1")

    @command(click.argument("start", type=bool))
    def edit_map(self, start):
        """Start map editing?"""
        if start:
            return self.send("start_edit_map")[0] == "ok"
        else:
            return self.send("end_edit_map")[0] == "ok"

    @command(click.option("--version", default=1))
    def fresh_map(self, version):
        """Return fresh map?"""
        if version not in [1, 2]:
            raise VacuumException("Unknown map version: %s" % version)

        if version == 1:
            return self.send("get_fresh_map")
        elif version == 2:
            return self.send("get_fresh_map_v2")

    @command(click.option("--version", default=1))
    def persist_map(self, version):
        """Return fresh map?"""
        if version not in [1, 2]:
            raise VacuumException("Unknown map version: %s" % version)

        if version == 1:
            return self.send("get_persist_map")
        elif version == 2:
            return self.send("get_persist_map_v2")

    @command(
        click.argument("x1", type=int),
        click.argument("y1", type=int),
        click.argument("x2", type=int),
        click.argument("y2", type=int),
    )
    def create_software_barrier(self, x1, y1, x2, y2):
        """Create software barrier (gen2 only?).

        NOTE: Multiple nogo zones and barriers could be added by passing
        a list of them to save_map.

        Requires new fw version.
        3.3.9_001633+?
        """
        # First parameter indicates the type, 1 = barrier
        payload = [1, x1, y1, x2, y2]
        return self.send("save_map", payload)[0] == "ok"

    @command(
        click.argument("x1", type=int),
        click.argument("y1", type=int),
        click.argument("x2", type=int),
        click.argument("y2", type=int),
        click.argument("x3", type=int),
        click.argument("y3", type=int),
        click.argument("x4", type=int),
        click.argument("y4", type=int),
    )
    def create_nogo_zone(self, x1, y1, x2, y2, x3, y3, x4, y4):
        """Create a rectangular no-go zone (gen2 only?).

        NOTE: Multiple nogo zones and barriers could be added by passing
        a list of them to save_map.

        Requires new fw version.
        3.3.9_001633+?
        """
        # First parameter indicates the type, 0 = zone
        payload = [0, x1, y1, x2, y2, x3, y3, x4, y4]
        return self.send("save_map", payload)[0] == "ok"

    @command(click.argument("enable", type=bool))
    def enable_lab_mode(self, enable):
        """Enable persistent maps and software barriers.

        This is required to use create_nogo_zone and create_software_barrier commands.
        """
        return self.send("set_lab_status", int(enable))["ok"]

    @command()
    def clean_history(self) -> CleaningSummary:
        """Return generic cleaning history."""
        return CleaningSummary(self.send("get_clean_summary"))

    @command()
    def last_clean_details(self) -> Optional[CleaningDetails]:
        """Return details from the last cleaning.

        Returns None if there has been no cleanups.
        """
        history = self.clean_history()
        if not history.ids:
            return None

        last_clean_id = history.ids.pop(0)
        return self.clean_details(last_clean_id, return_list=False)

    @command(
        click.argument("id_", type=int, metavar="ID"),
        click.argument("return_list", type=bool, default=False),
    )
    def clean_details(
        self, id_: int, return_list=True
    ) -> Union[List[CleaningDetails], Optional[CleaningDetails]]:
        """Return details about specific cleaning."""
        details = self.send("get_clean_record", [id_])

        if not details:
            _LOGGER.warning("No cleaning record found for id %s" % id_)
            return None

        if return_list:
            _LOGGER.warning(
                "This method will be returning the details "
                "without wrapping them into a list in the "
                "near future. The current behavior can be "
                "kept by passing return_list=True and this "
                "warning will be removed when the default gets "
                "changed."
            )
            return [CleaningDetails(entry) for entry in details]

        if len(details) > 1:
            _LOGGER.warning("Got multiple clean details, returning the first")

        res = CleaningDetails(details.pop())
        return res

    @command()
    def find(self):
        """Find the robot."""
        return self.send("find_me", [""])

    @command()
    def timer(self) -> List[Timer]:
        """Return a list of timers."""
        timers = list()
        timezone = pytz.timezone(self.timezone())
        for rec in self.send("get_timer", [""]):
            try:
                timers.append(Timer(rec, timezone=timezone))
            except Exception as ex:
                _LOGGER.warning("Unable to add timer for %s: %s", rec, ex)

        return timers

    @command(
        click.argument("cron"),
        click.argument("command", required=False, default=""),
        click.argument("parameters", required=False, default=""),
    )
    def add_timer(self, cron: str, command: str, parameters: str):
        """Add a timer.

        :param cron: schedule in cron format
        :param command: ignored by the vacuum.
        :param parameters: ignored by the vacuum.
        """
        import time

        ts = int(round(time.time() * 1000))
        return self.send("set_timer", [[str(ts), [cron, [command, parameters]]]])

    @command(click.argument("timer_id", type=int))
    def delete_timer(self, timer_id: int):
        """Delete a timer with given ID.

        :param int timer_id: Timer ID
        """
        return self.send("del_timer", [str(timer_id)])

    @command(
        click.argument("timer_id", type=int), click.argument("mode", type=TimerState)
    )
    def update_timer(self, timer_id: int, mode: TimerState):
        """Update a timer with given ID.

        :param int timer_id: Timer ID
        :param TimerStae mode: either On or Off
        """
        if mode != TimerState.On and mode != TimerState.Off:
            raise DeviceException("Only 'On' or 'Off' are  allowed")
        return self.send("upd_timer", [str(timer_id), mode.value])

    @command()
    def dnd_status(self):
        """Returns do-not-disturb status."""
        # {'result': [{'enabled': 1, 'start_minute': 0, 'end_minute': 0,
        #  'start_hour': 22, 'end_hour': 8}], 'id': 1}
        return DNDStatus(self.send("get_dnd_timer")[0])

    @command(
        click.argument("start_hr", type=int),
        click.argument("start_min", type=int),
        click.argument("end_hr", type=int),
        click.argument("end_min", type=int),
    )
    def set_dnd(self, start_hr: int, start_min: int, end_hr: int, end_min: int):
        """Set do-not-disturb.

        :param int start_hr: Start hour
        :param int start_min: Start minute
        :param int end_hr: End hour
        :param int end_min: End minute
        """
        return self.send("set_dnd_timer", [start_hr, start_min, end_hr, end_min])

    @command()
    def disable_dnd(self):
        """Disable do-not-disturb."""
        return self.send("close_dnd_timer", [""])

    @command(click.argument("speed", type=int))
    def set_fan_speed(self, speed: int):
        """Set fan speed.

        :param int speed: Fan speed to set
        """
        # speed = [38, 60 or 77]
        return self.send("set_custom_mode", [speed])

    @command()
    def fan_speed(self):
        """Return fan speed."""
        return self.send("get_custom_mode")[0]

    def _autodetect_model(self):
        """Detect the model of the vacuum.

        For the moment this is used only for the fanspeeds, but that could be extended
        to cover other supported features.
        """
        try:
            info = self.info()
            self.model = info.model
        except (TypeError, DeviceInfoUnavailableException):
            # cloud-blocked vacuums will not return proper payloads
            self._fanspeeds = FanspeedV1
            self.model = ROCKROBO_V1
            _LOGGER.warning("Unable to query model, falling back to %s", self.model)
            return
        finally:
            _LOGGER.debug("Model: %s", self.model)

        if self.model == ROCKROBO_V1:
            _LOGGER.debug("Got robov1, checking for firmware version")
            fw_version = info.firmware_version
            version, build = fw_version.split("_")
            version = tuple(map(int, version.split(".")))
            if version >= (3, 5, 8):
                self._fanspeeds = FanspeedV3
            elif version == (3, 5, 7):
                self._fanspeeds = FanspeedV2
            else:
                self._fanspeeds = FanspeedV1
        elif self.model == "roborock.vacuum.e2":
            self._fanspeeds = FanspeedE2
        elif self.model == ROCKROBO_S7:
            self._fanspeeds = FanspeedS7
        else:
            self._fanspeeds = FanspeedV2

        _LOGGER.debug(
            "Using new fanspeed mapping %s for %s", self._fanspeeds, info.model
        )

    @command()
    def fan_speed_presets(self) -> Dict[str, int]:
        """Return dictionary containing supported fan speeds."""
        if self.model is None:
            self._autodetect_model()

        return {x.name: x.value for x in list(self._fanspeeds)}

    @command()
    def sound_info(self):
        """Get voice settings."""
        return SoundStatus(self.send("get_current_sound")[0])

    @command(
        click.argument("url"),
        click.argument("md5sum"),
        click.argument("sound_id", type=int),
    )
    def install_sound(self, url: str, md5sum: str, sound_id: int):
        """Install sound from the given url."""
        payload = {"url": url, "md5": md5sum, "sid": int(sound_id)}
        return SoundInstallStatus(self.send("dnld_install_sound", payload)[0])

    @command()
    def sound_install_progress(self):
        """Get sound installation progress."""
        return SoundInstallStatus(self.send("get_sound_progress")[0])

    @command()
    def sound_volume(self) -> int:
        """Get sound volume."""
        return self.send("get_sound_volume")[0]

    @command(click.argument("vol", type=int))
    def set_sound_volume(self, vol: int):
        """Set sound volume [0-100]."""
        return self.send("change_sound_volume", [vol])

    @command()
    def test_sound_volume(self):
        """Test current sound volume."""
        return self.send("test_sound_volume")

    @command()
    def serial_number(self):
        """Get serial number."""
        serial = self.send("get_serial_number")
        if isinstance(serial, list):
            return serial[0]["serial_number"]
        return serial

    @command()
    def locale(self):
        """Return locale information."""
        return self.send("app_get_locale")

    @command()
    def timezone(self):
        """Get the timezone."""
        res = self.send("get_timezone")

        def _fallback_timezone(data):
            fallback = "UTC"
            _LOGGER.error(
                "Unsupported timezone format (%s), falling back to %s", data, fallback
            )
            return fallback

        if isinstance(res, int):
            return _fallback_timezone(res)

        res = res[0]
        if isinstance(res, dict):
            # Xiaowa E25 example
            # {'olson': 'Europe/Berlin', 'posix': 'CET-1CEST,M3.5.0,M10.5.0/3'}
            if "olson" not in res:
                return _fallback_timezone(res)

            return res["olson"]

        return res

    def set_timezone(self, new_zone):
        """Set the timezone."""
        return self.send("set_timezone", [new_zone])[0] == "ok"

    def configure_wifi(self, ssid, password, uid=0, timezone=None):
        """Configure the wifi settings."""
        extra_params = {}
        if timezone is not None:
            now = datetime.datetime.now(pytz.timezone(timezone))
            offset_as_float = now.utcoffset().total_seconds() / 60 / 60
            extra_params["tz"] = timezone
            extra_params["gmt_offset"] = offset_as_float

        return super().configure_wifi(ssid, password, uid, extra_params)

    @command()
    def carpet_mode(self):
        """Get carpet mode settings."""
        return CarpetModeStatus(self.send("get_carpet_mode")[0])

    @command(
        click.argument("enabled", required=True, type=bool),
        click.argument("stall_time", required=False, default=10, type=int),
        click.argument("low", required=False, default=400, type=int),
        click.argument("high", required=False, default=500, type=int),
        click.argument("integral", required=False, default=450, type=int),
    )
    def set_carpet_mode(
        self,
        enabled: bool,
        stall_time: int = 10,
        low: int = 400,
        high: int = 500,
        integral: int = 450,
    ):
        """Set the carpet mode."""
        click.echo("Setting carpet mode: %s" % enabled)
        data = {
            "enable": int(enabled),
            "stall_time": stall_time,
            "current_low": low,
            "current_high": high,
            "current_integral": integral,
        }
        return self.send("set_carpet_mode", [data])[0] == "ok"

    @command()
    def stop_zoned_clean(self):
        """Stop cleaning a zone."""
        return self.send("stop_zoned_clean")

    @command()
    def stop_segment_clean(self):
        """Stop cleaning a segment."""
        return self.send("stop_segment_clean")

    @command()
    def resume_segment_clean(self):
        """Resuming cleaning a segment."""
        return self.send("resume_segment_clean")

    @command(click.argument("segments", type=LiteralParamType(), required=True))
    def segment_clean(self, segments: List):
        """Clean segments.

        :param List segments: List of segments to clean: [16,17,18]
        """
        return self.send("app_segment_clean", segments)

    @command()
    def get_room_mapping(self):
        """Retrieves a list of segments."""
        return self.send("get_room_mapping")

    @command()
    def get_backup_maps(self):
        """Get backup maps."""
        return self.send("get_recover_maps")

    @command(click.argument("id", type=int))
    def use_backup_map(self, id: int):
        """Set backup map."""
        click.echo("Setting the map %s as active" % id)
        return self.send("recover_map", [id])

    @command()
    def get_segment_status(self):
        """Get the status of a segment."""
        return self.send("get_segment_status")

    def name_segment(self):
        raise NotImplementedError("unknown parameters")
        # return self.send("name_segment")

    def merge_segment(self):
        raise NotImplementedError("unknown parameters")
        # return self.send("merge_segment")

    def split_segment(self):
        raise NotImplementedError("unknown parameters")
        # return self.send("split_segment")

    @command()
    def waterflow(self) -> WaterFlow:
        """Get water flow setting."""
        return WaterFlow(self.send("get_water_box_custom_mode")[0])

    @command(click.argument("waterflow", type=EnumType(WaterFlow)))
    def set_waterflow(self, waterflow: WaterFlow):
        """Set water flow setting."""
        return self.send("set_water_box_custom_mode", [waterflow.value])

    @command()
    def mop_mode(self) -> Optional[MopMode]:
        """Get mop mode setting."""
        try:
            return MopMode(self.send("get_mop_mode")[0])
        except ValueError:
            return None

    @command(click.argument("mop_mode", type=EnumType(MopMode)))
    def set_mop_mode(self, mop_mode: MopMode):
        """Set mop mode setting."""
        return self.send("set_mop_mode", [mop_mode.value])

    @command()
    def child_lock(self) -> bool:
        """Get child lock setting."""
        return self.send("get_child_lock_status")["lock_status"] == 1

    @command(click.argument("lock", type=bool))
    def set_child_lock(self, lock: bool) -> bool:
        """Set child lock setting."""
        return self.send("set_child_lock_status", {"lock_status": int(lock)})[0] == "ok"

    @classmethod
    def get_device_group(cls):
        @click.pass_context
        def callback(ctx, *args, id_file, **kwargs):
            gco = ctx.find_object(GlobalContextObject)
            if gco:
                kwargs["debug"] = gco.debug

            start_id = manual_seq = 0
            with contextlib.suppress(FileNotFoundError, TypeError, ValueError), open(
                id_file, "r"
            ) as f:
                x = json.load(f)
                start_id = x.get("seq", 0)
                manual_seq = x.get("manual_seq", 0)
                _LOGGER.debug("Read stored sequence ids: %s", x)

            ctx.obj = cls(*args, start_id=start_id, **kwargs)
            ctx.obj.manual_seqnum = manual_seq

        dg = DeviceGroup(
            cls,
            params=DeviceGroup.DEFAULT_PARAMS
            + [
                click.Option(
                    ["--id-file"],
                    type=click.Path(dir_okay=False, writable=True),
                    default=os.path.join(
                        user_cache_dir("python-miio"), "python-mirobo.seq"
                    ),
                )
            ],
            callback=callback,
        )

        @dg.resultcallback()
        @dg.device_pass
        def cleanup(vac: Vacuum, *args, **kwargs):
            if vac.ip is None:  # dummy Device for discovery, skip teardown
                return
            id_file = kwargs["id_file"]
            seqs = {"seq": vac._protocol.raw_id, "manual_seq": vac.manual_seqnum}
            _LOGGER.debug("Writing %s to %s", seqs, id_file)
            path_obj = pathlib.Path(id_file)
            cache_dir = path_obj.parents[0]
            cache_dir.mkdir(parents=True, exist_ok=True)
            with open(id_file, "w") as f:
                json.dump(seqs, f)

        return dg
