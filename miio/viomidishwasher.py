import enum
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import click

from .click_common import EnumType, command, format_output
from .device import Device
from .exceptions import DeviceException

_LOGGER = logging.getLogger(__name__)

MODEL_DISWAHSER_M02 = "viomi.dishwasher.m02"

MODELS_SUPPORTED = [MODEL_DISWAHSER_M02]


class MachineStatus(enum.IntEnum):
    Off = 0
    On = 1
    Running = 2
    Paused = 3
    Scheduled = 5


class ProgramStatus(enum.IntEnum):
    Standby = 0
    Prewash = 1
    Wash = 2
    Rinse = 3
    Drying = 4
    Unknown = -1


class Program(enum.IntEnum):
    Standard = 0
    Eco = 1
    Quick = 2
    Intensive = 3
    Glassware = 4
    Sterilize = 7
    Unknown = -1

    @property
    def run_time(self):
        return ProgramRunTime[self.value]


ProgramRunTime = {
    Program.Standard: 7102,
    Program.Eco: 7702,
    Program.Quick: 1675,
    Program.Intensive: 7522,
    Program.Glassware: 6930,
    Program.Sterilize: 8295,
}


class ChildLockStatus(enum.IntEnum):
    Enabled = 1
    Disabled = 0


class DoorStatus(enum.IntEnum):
    Open = 128
    Closed = 0


class SystemStatus(enum.IntEnum):
    WaterLeak = 1
    InsufficientWaterFlow = 4
    InternalConnectionError = 9
    ThermistorError = 32
    InsufficientWaterSoftener = 512
    HeatingElementError = 2048


class PowerStatus(enum.IntEnum):
    On = 1
    Off = 0


class ViomiDishwasherStatus:
    def __init__(self, data: Dict[str, Any]) -> None:
        self.data = data

    @property
    def child_lock(self) -> ChildLockStatus:
        return ChildLockStatus(self.data["child_lock"])

    @property
    def program(self) -> Program:
        try:
            return Program(self.data["program"])
        except ValueError:
            return Program.Unknown

    @property
    def door(self) -> DoorStatus:
        return DoorStatus(self.data["run_status"] & (1 << 7))

    @property
    def system_status_raw(self) -> [int, SystemStatus]:
        return self.data["run_status"]

    @property
    def status(self) -> MachineStatus:
        return MachineStatus(self.data["wash_status"])

    @property
    def temperature(self) -> int:
        return self.data["wash_temp"]

    @property
    def power(self) -> PowerStatus:
        return PowerStatus(self.data["power"])

    @property
    def time_left(self) -> int:
        return self.data["left_time"]

    @property
    def schedule(self) -> [datetime, None]:
        schedule = self.data["wash_done_appointment"]
        return datetime.fromtimestamp(schedule) if schedule else None

    @property
    def air_refresh_interval(self) -> int:
        return self.data["freshdry_interval"]

    @property
    def program_progress(self) -> ProgramStatus:
        try:
            return ProgramStatus(self.data["wash_process"])
        except ValueError:
            return ProgramStatus.Unknown

    @property
    def errors(self) -> List[Optional[SystemStatus]]:
        errors = []
        if self.data["run_status"] & (1 << 0):
            errors.append(SystemStatus.WaterLeak)
        if self.data["run_status"] & (1 << 3):
            errors.append(SystemStatus.InternalConnectionError)
        if self.data["run_status"] & (1 << 2):
            errors.append(SystemStatus.InsufficientWaterFlow)
        if self.data["run_status"] & (1 << 5):
            errors.append(SystemStatus.ThermistorError)
        if self.data["run_status"] & (1 << 9):
            errors.append(SystemStatus.InsufficientWaterSoftener)
        if self.data["run_status"] & (1 << 11):
            errors.append(SystemStatus.HeatingElementError)

        return errors

    def __repr__(self) -> str:
        return (
            f"<ViomiDishwasherStatus "
            f"child_lock={self.child_lock}, "
            f"program={self.program}, "
            f"door={self.door}, "
            f"system_status_raw={self.system_status_raw}, "
            f"status={self.status}, "
            f"temperature={self.temperature}, "
            f"power={self.power}, "
            f"time_left={self.time_left}, "
            f"schedule={self.schedule}, "
            f"air_refresh_interval={self.air_refresh_interval}, "
            f"program_progress={self.program_progress}, "
            f"errors={self.errors}>"
        )


class ViomiDishwasher(Device):
    """Main class representing the dishwasher."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        model = self.info().model
        if model not in MODELS_SUPPORTED:
            _LOGGER.warning(
                "Dishwasher model '%s' has not been tested. Please continue with caution and open a GitHub issue to get this model supported.",
                model,
            )

    @command(
        default_output=format_output(
            "",
            "Program: {result.program.name}\n"
            "Program state: {result.program_progress.name}\n"
            "Program time left: {result.time_left}\n"
            "Dishwasher status: {result.status.name}\n"
            "Power status: {result.power.name}\n"
            "Door: {result.door.name}\n"
            "Temperature: {result.temperature}\n"
            "Schedule: {result.schedule}\n"
            "Air refresh interval: {result.air_refresh_interval}\n"
            "Child lock: {result.child_lock.name}\n"
            "System status (raw): {result.system_status_raw}\n"
            "Errors: {result.errors}",
        )
    )
    def status(self) -> ViomiDishwasherStatus:
        """Retrieve properties."""

        properties = [
            "child_lock",
            "program",
            "run_status",
            "wash_status",
            "wash_temp",
            "power",
            "left_time",
            "wash_done_appointment",
            "freshdry_interval",
            "wash_process",
        ]

        import inspect

        if "flatten_request" in inspect.getfullargspec(self.get_properties).args:
            values = self.get_properties(properties, flatten_request=True)
        else:
            values = self.get_properties(properties, max_properties=1)

        return ViomiDishwasherStatus(defaultdict(lambda: None, zip(properties, values)))

    # FIXME: Change these to use the ViomiDishwasherStatus once we can query multiple properties at once (or cache?).
    def _is_on(self) -> bool:
        return bool(PowerStatus(self.get_properties(["power"])[0]))

    def _is_valid_program(self, program: Program) -> bool:
        return True if not program == Program.Unknown else False

    def _is_running(self) -> bool:
        current_status = ProgramStatus(self.get_properties(["wash_process"])[0])
        return True if current_status > 0 else False

    def _set_wash_status(self, status: MachineStatus) -> bool:
        self.send("set_wash_status", [status.value])

    @command(default_output=format_output("Powering on"))
    def on(self):
        """Power on."""
        return self.send("set_power", [PowerStatus.On.value])

    @command(default_output=format_output("Powering off"))
    def off(self):
        """Power off."""
        return self.send("set_power", [PowerStatus.Off.value])

    @command(
        click.argument("status", type=EnumType(ChildLockStatus)),
        default_output=format_output("Setting child lock to '{status.name}'"),
    )
    def child_lock(self, status: ChildLockStatus):
        """Set child lock."""

        if not self._is_on():
            self.on()
            output = self.send("set_child_lock", [status.value])
            self.off()
        else:
            output = self.send("set_child_lock", [status.value])

        return output

    @command(
        click.argument("time", type=click.DateTime(formats=["%H:%M"])),
        click.argument("program", type=EnumType(Program)),
    )
    def schedule(self, time: datetime, program: Program) -> str:
        """Schedule a program run."""

        if not self._is_valid_program(program):
            DeviceException(f"Program {program.name} is not valid for this function.")

        scheduled_finish_date = datetime.now().replace(
            hour=time.hour, minute=time.minute, second=0, microsecond=0
        )
        scheduled_start_date = scheduled_finish_date - timedelta(
            seconds=program.run_time
        )
        if scheduled_start_date < datetime.now():
            raise DeviceException(
                "Proposed time is in the past (the proposed time is the finishing time, not the start time)."
            )

        if not self._is_on():
            self.on()

        if self._is_running():
            raise DeviceException(
                "A wash program is already running. Wait for current program to finish or stop."
            )

        if self.get_properties(["wash_done_appointment"])[0] > 0:
            self.cancel_schedule(check_if_on=False)

        params = f"{round(scheduled_finish_date.timestamp())},{program.value}"
        self.send("set_wash_done_appointment", [params])
        return f"Program {program.name} will start at {scheduled_start_date} and finish around {scheduled_finish_date}."

    @command()
    def cancel_schedule(self, check_if_on=True) -> str:
        """Cancel an existing schedule."""

        if not self._is_on() and check_if_on:
            return "Dishwasher is not turned on. Nothing scheduled."

        self.send("set_wash_done_appointment", ["0,0"])
        return "Schedule cancelled."

    @command(
        click.argument("program", type=EnumType(Program), required=False),
    )
    def start(self, program: [Program, None]) -> str:
        """Start a program (with optional program or current)."""

        if program:
            self.send("set_program", [program.value])
            return f"Started program {program.name}"

        if not self._is_on():
            self.on()

        program = Program(self.get_properties(["program"])[0])
        self._set_wash_status(MachineStatus.Running)
        return f"Started program {program.name}"

    @command()
    def stop(self) -> str:
        """Stop a program."""

        if not self._is_running():
            raise DeviceException("No program running.")

        self._set_wash_status(MachineStatus.On)
        return "Program stopped."

    @command()
    def pause(self) -> str:
        """Pause a program."""

        if not self._is_running():
            raise DeviceException("No program running.")

        self._set_wash_status(MachineStatus.Paused)
        return "Program paused."

    @command(name="continue")
    def continue_program(self) -> str:
        """Continue a program."""

        if not self._is_running():
            raise DeviceException("No program running.")

        self._set_wash_status(MachineStatus.Running)
        return "Program continued."

    @command(
        click.argument("time", type=int),
        default_output=format_output("Setting air refresh to '{time}'"),
    )
    def airrefresh(self, time: int) -> List[str]:
        """Set air refresh interval."""

        return self.send("set_freshdry_interval_t", [time])
