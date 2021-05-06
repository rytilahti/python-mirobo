import inspect
import logging
from enum import Enum
from pprint import pformat as pf
from typing import Any, Optional  # noqa: F401

import click

from .click_common import DeviceGroupMeta, LiteralParamType, command, format_output
from .deviceinfo import DeviceInfo
from .exceptions import DeviceInfoUnavailableException, PayloadDecodeException
from .miioprotocol import MiIOProtocol

_LOGGER = logging.getLogger(__name__)


class UpdateState(Enum):
    Downloading = "downloading"
    Installing = "installing"
    Failed = "failed"
    Idle = "idle"


class DeviceStatus:
    """Base class for status containers.

    All status container classes should inherit from this class. The __repr__
    implementation returns all defined properties and their values.
    """

    def __repr__(self):
        props = inspect.getmembers(self.__class__, lambda o: isinstance(o, property))

        s = f"<{self.__class__.__name__}"
        for prop_tuple in props:
            name, prop = prop_tuple
            try:
                prop_value = prop.fget(self)
            except Exception as ex:
                prop_value = ex.__class__.__name__

            s += f" {name}={prop_value}"
        s += ">"
        return s


class Device(metaclass=DeviceGroupMeta):
    """Base class for all device implementations.

    This is the main class providing the basic protocol handling for devices using the
    ``miIO`` protocol. This class should not be initialized directly but a device-
    specific class inheriting it should be used instead of it.
    """

    retry_count = 3
    timeout = 5

    def __init__(
        self,
        ip: str = None,
        token: str = None,
        start_id: int = 0,
        debug: int = 0,
        lazy_discover: bool = True,
        timeout: int = None,
        *,
        model: str = None,
    ) -> None:
        self.ip = ip
        self.token = token
        self._model = model
        self._info = None
        timeout = timeout if timeout is not None else self.timeout
        self._protocol = MiIOProtocol(
            ip, token, start_id, debug, lazy_discover, timeout
        )

    def send(
        self,
        command: str,
        parameters: Any = None,
        retry_count: int = None,
        *,
        extra_parameters=None,
    ) -> Any:
        """Send a command to the device.

        Basic format of the request:
        {"id": 1234, "method": command, "parameters": parameters}

        `extra_parameters` allows passing elements to the top-level of the request.
        This is necessary for some devices, such as gateway devices, which expect
        the sub-device identifier to be on the top-level.

        :param str command: Command to send
        :param dict parameters: Parameters to send
        :param int retry_count: How many times to retry on error
        :param dict extra_parameters: Extra top-level parameters
        :param str model: Force model to avoid autodetection
        """
        retry_count = retry_count if retry_count is not None else self.retry_count
        return self._protocol.send(
            command, parameters, retry_count, extra_parameters=extra_parameters
        )

    def send_handshake(self):
        """Send initial handshake to the device."""
        return self._protocol.send_handshake()

    @command(
        click.argument("command", type=str, required=True),
        click.argument("parameters", type=LiteralParamType(), required=False),
    )
    def raw_command(self, command, parameters):
        """Send a raw command to the device. This is mostly useful when trying out
        commands which are not implemented by a given device instance.

        :param str command: Command to send
        :param dict parameters: Parameters to send
        """
        return self.send(command, parameters)

    @command(
        default_output=format_output(
            "",
            "Model: {result.model}\n"
            "Hardware version: {result.hardware_version}\n"
            "Firmware version: {result.firmware_version}\n",
        ),
        skip_autodetect=True,
    )
    def info(self, *, skip_cache=False) -> DeviceInfo:
        """Get (and cache) miIO protocol information from the device.

        This includes information about connected wlan network, and hardware and
        software versions.

        :param force bool: Skip the cache
        """
        if self._info is not None and not skip_cache:
            return self._info

        try:
            devinfo = DeviceInfo(self.send("miIO.info"))
            self._info = devinfo
            _LOGGER.info("Detected model %s", devinfo.model)
            return devinfo
        except PayloadDecodeException as ex:
            raise DeviceInfoUnavailableException(
                "Unable to request miIO.info from the device"
            ) from ex

    @property
    def raw_id(self) -> int:
        """Return the last used protocol sequence id."""
        return self._protocol.raw_id

    @property
    def model(self) -> str:
        """Return device model."""
        if self._model is not None:
            return self._model

        return self.info().model

    def update(self, url: str, md5: str):
        """Start an OTA update."""
        payload = {
            "mode": "normal",
            "install": "1",
            "app_url": url,
            "file_md5": md5,
            "proc": "dnld install",
        }
        return self.send("miIO.ota", payload)[0] == "ok"

    def update_progress(self) -> int:
        """Return current update progress [0-100]."""
        return self.send("miIO.get_ota_progress")[0]

    def update_state(self):
        """Return current update state."""
        return UpdateState(self.send("miIO.get_ota_state")[0])

    def configure_wifi(self, ssid, password, uid=0, extra_params=None):
        """Configure the wifi settings."""
        if extra_params is None:
            extra_params = {}
        params = {"ssid": ssid, "passwd": password, "uid": uid, **extra_params}

        return self.send("miIO.config_router", params)[0]

    def get_properties(
        self, properties, *, property_getter="get_prop", max_properties=None
    ):
        """Request properties in slices based on given max_properties.

        This is necessary as some devices have limitation on how many
        properties can be queried at once.

        If `max_properties` is None, all properties are requested at once.

        :param list properties: List of properties to query from the device.
        :param int max_properties: Number of properties that can be requested at once.
        :return List of property values.
        """
        _props = properties.copy()
        values = []
        while _props:
            values.extend(self.send(property_getter, _props[:max_properties]))
            if max_properties is None:
                break

            _props[:] = _props[max_properties:]

        properties_count = len(properties)
        values_count = len(values)
        if properties_count != values_count:
            _LOGGER.debug(
                "Count (%s) of requested properties does not match the "
                "count (%s) of received values.",
                properties_count,
                values_count,
            )

        return values

    @command(
        click.argument("properties", type=str, nargs=-1, required=True),
    )
    def test_properties(self, properties):
        """Helper to test device properties."""

        def ok(x):
            click.echo(click.style(x, fg="green", bold=True))

        def fail(x):
            click.echo(click.style(x, fg="red", bold=True))

        try:
            model = self.info().model
        except Exception as ex:
            _LOGGER.warning("Unable to obtain device model: %s", ex)
            model = "<unavailable>"

        click.echo(f"Testing properties {properties} for {model}")
        valid_properties = {}
        max_property_len = max([len(p) for p in properties])
        for property in properties:
            try:
                click.echo(f"Testing {property:{max_property_len+2}} ", nl=False)
                value = self.get_properties([property])
                # Handle list responses
                if isinstance(value, list):
                    # unwrap single-element lists
                    if len(value) == 1:
                        value = value.pop()
                    # report on unexpected multi-element lists
                    elif len(value) > 1:
                        _LOGGER.error("Got an array as response: %s", value)
                    # otherwise we received an empty list, which we consider here as None
                    else:
                        value = None

                if value is None:
                    fail("None")
                else:
                    valid_properties[property] = value
                    ok(f"{repr(value)} {type(value)}")
            except Exception as ex:
                _LOGGER.warning("Unable to request %s: %s", property, ex)

        click.echo(
            f"Found {len(valid_properties)} valid properties, testing max_properties.."
        )

        props_to_test = list(valid_properties.keys())
        max_properties = -1
        while len(props_to_test) > 1:
            try:
                click.echo(
                    f"Testing {len(props_to_test)} properties at once ({' '.join(props_to_test)}): ",
                    nl=False,
                )
                resp = self.get_properties(props_to_test)

                if len(resp) == len(props_to_test):
                    max_properties = len(props_to_test)
                    ok(f"OK for {max_properties} properties")
                    break
                else:
                    removed_property = props_to_test.pop()
                    fail(
                        f"Got different amount of properties ({len(props_to_test)}) than requested ({len(resp)}), removing {removed_property}"
                    )

            except Exception as ex:
                removed_property = props_to_test.pop()
                msg = f"Unable to request properties: {ex} - removing {removed_property} for next try"
                _LOGGER.warning(msg)
                fail(ex)

        non_empty_properties = {
            k: v for k, v in valid_properties.items() if v is not None
        }

        click.echo(
            click.style("\nPlease copy the results below to your report", bold=True)
        )
        click.echo("### Results ###")
        click.echo(f"Model: {model}")
        _LOGGER.debug(f"All responsive properties:\n{pf(valid_properties)}")
        click.echo(f"Total responsives: {len(valid_properties)}")
        click.echo(f"Total non-empty: {len(non_empty_properties)}")
        click.echo(f"All non-empty properties:\n{pf(non_empty_properties)}")
        click.echo(f"Max properties: {max_properties}")

        return "Done"

    def __repr__(self):
        return f"<{self.__class__.__name__ }: {self.ip} (token: {self.token})>"
