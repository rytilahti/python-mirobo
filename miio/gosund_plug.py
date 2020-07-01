import logging
from dataclasses import dataclass, field

from .click_common import command, format_output
from .miot_device import MiotDevice

_LOGGER = logging.getLogger(__name__)


@dataclass
class GosundPlugStatus:
    _max_properties = 1
    state: bool = field(metadata={"siid": 2, "piid": 1})


class GosundPlug(MiotDevice):
    """Support for gosund miot plug (cuco.plug.cp1)."""

    _MAPPING = GosundPlugStatus

    @command()
    def status(self) -> GosundPlugStatus:
        """Return current state of the plug."""

        return self.get_properties_for_dataclass(GosundPlugStatus)

    @command(default_output=format_output("Powering on"))
    def on(self):
        """Power on."""
        return self.set_property(state=True)

    @command(default_output=format_output("Powering off"))
    def off(self):
        """Power off."""
        return self.set_property(state=False)
