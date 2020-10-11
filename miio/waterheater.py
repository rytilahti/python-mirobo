import logging
from typing import Any, Dict

from .click_common import command, format_output
from .device import Device

_LOGGER = logging.getLogger(__name__)


class WaterHeaterStatus:

    def __init__(self, data: Dict[str, Any]) -> None:
        self.data = data

    @property
    def washStatus(self) -> str:
        return self.data["washStatus"]

    @property
    def velocity(self) -> str:
        return self.data["velocity"]

    @property
    def waterTemp(self) -> str:
        return self.data["waterTemp"]

    @property
    def targetTemp(self) -> str:
        return self.data["targetTemp"]

    @property
    def errStatus(self) -> str:
        return self.data["errStatus"]

    @property
    def hotWater(self) -> str:
        return self.data["hotWater"]

    @property
    def needClean(self) -> str:
        return self.data["needClean"]

    @property
    def modeType(self) -> str:
        return self.data["modeType"]

    @property
    def appointStart(self) -> str:
        return self.data["appointStart"]

    @property
    def appointEnd(self) -> str:
        return self.data["appointEnd"]

    def __repr__(self) -> str:
        return (
            "<WaterHeaterStatus "
            "washStatus=%s, "
            "velocity=%s, "
            "waterTemp=%s, "
            "targetTemp=%s, "
            "errStatus=%s, "
            "hotWater=%s, "
            "needClean=%s, "
            "modeType=%s, "
            "appointStart=%s, "
            "appointEnd=%s>"
            % (
                self.washStatus,
                self.velocity,
                self.waterTemp,
                self.targetTemp,
                self.errStatus,
                self.hotWater,
                self.needClean,
                self.modeType,
                self.appointStart,
                self.appointEnd,
            )
        )

    def __json__(self):
        return self.data


class WaterHeater(Device):
    """Main class representing the waiter purifier."""

    @command(
        default_output=format_output(
            "",
            "Status: {result.washStatus}\n"
            "Velocity: {result.velocity}\n"
            "Water temperature: {result.waterTemp}\n"
            "Target temperature: {result.targetTemp}\n"
            "Error status: {result.errStatus}\n"
            "Hot Water: {result.hotWater}\n"
            "Need Clean: {result.needClean}\n"
            "Mode Type: {result.modeType}\n"
            "Appoint Start: {result.appointStart}\n"
            "Appoint End: {result.appointEnd}\n",
        )
    )
    def status(self) -> WaterHeaterStatus:
        """Retrieve properties."""

        properties = [
            "washStatus",
            "velocity",
            "waterTemp",
            "targetTemp",
            "errStatus",
            "hotWater",
            "needClean",
            "modeType",
            "appointStart",
            "appointEnd",
        ]

        _props_per_request = 1
        values = self.get_properties(properties, max_properties=_props_per_request)

        return WaterHeaterStatus(dict(zip(properties, values)))

    @command(default_output=format_output("Powering on"))
    def on(self):
        """Power on."""
        return self.send("set_power", [1])

    @command(default_output=format_output("Powering off"))
    def off(self):
        """Power off."""
        return self.send("set_power", [0])
