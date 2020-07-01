import logging
from dataclasses import dataclass, field

from .click_common import command
from .device import Device
from .exceptions import DeviceException

_LOGGER = logging.getLogger(__name__)


@dataclass
class MiotInfo:
    """Container for common MiotInfo service."""

    _siid = 1
    _max_properties = 1  # some devices respond with broken json otherwise

    manufacturer: str = field(metadata={"piid": 1})
    model: str = field(metadata={"piid": 2})
    serial_number: str = field(metadata={"piid": 3})
    firmware_version: str = field(metadata={"piid": 4})


class MiotDevice(Device):
    """Main class representing a MIoT device."""

    def __init__(
        self,
        ip: str = None,
        token: str = None,
        start_id: int = 0,
        debug: int = 0,
        lazy_discover: bool = True,
    ) -> None:
        super().__init__(ip, token, start_id, debug, lazy_discover)

    @command()
    def miot_info(self) -> MiotInfo:
        """Return common miot information."""
        return self.get_properties_for_dataclass(MiotInfo)

    def get_properties_for_dataclass(self, cls):
        """Run a query to fill property container."""
        fields = cls.__dataclass_fields__
        property_mapping = {}

        for field_name in fields:
            field_meta = fields[field_name].metadata

            if "piid" not in field_meta:
                continue
            piid = field_meta["piid"]

            siid = field_meta.get("siid", getattr(cls, "_siid", None))
            if siid is None:
                raise DeviceException(
                    f"no siid defined for {field_name} or for class {cls}"
                )

            property_mapping[field_name] = {"siid": siid, "piid": piid}

        response = {
            prop["did"]: prop["value"] if prop["code"] == 0 else None
            for prop in self.get_properties_for_mapping(
                property_mapping, max_properties=cls._max_properties
            )
        }

        return cls(**response)

    def set_property(self, **kwargs):
        """Helper to set properties using the device specific mapping."""
        if getattr(self, "_MAPPING") is None:
            raise DeviceException("Device class does not have _MAPPING")

        return self.set_properties_from_dataclass(self._MAPPING(**kwargs))

    def set_properties_from_dataclass(self, obj):
        """Set properties as defined in the given dataclass object."""
        # TODO: this needs cleanup.
        fields = obj.__dataclass_fields__
        properties_to_set = []

        for field_name in fields:
            field_meta = fields[field_name].metadata

            if "piid" not in field_meta:
                continue

            piid = field_meta["piid"]

            siid = field_meta.get("siid", getattr(obj, "_siid", None))
            if siid is None:
                raise DeviceException(
                    f"no siid defined for {field_name} or for class {obj.__class__}"
                )

            value = obj.__getattribute__(field_name)
            if value is None:
                continue

            property_set = {
                "siid": siid,
                "piid": piid,
                "did": field_name,
                "value": value,
            }

            properties_to_set.append(property_set)

        if not properties_to_set:
            raise DeviceException("No values to set!")

        # TODO: handle splitting based on _max_properties

        _LOGGER.debug("Going to set %s" % properties_to_set)
        return self.send("set_properties", properties_to_set)

    def get_properties_for_mapping(
        self, property_mapping, *, max_properties=15
    ) -> list:
        """Retrieve raw properties based on mapping."""

        # We send property key in "did" because it's sent back via response and we can identify the property.
        properties = [{"did": k, **v} for k, v in property_mapping.items()]

        return self.get_properties(properties, max_properties=max_properties)

    def set_property_from_mapping(self, property_mapping, property_key: str, value):
        """Sets property value."""

        return self.send(
            "set_properties",
            [{"did": property_key, **property_mapping[property_key], "value": value}],
        )
