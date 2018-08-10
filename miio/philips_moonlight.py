import logging
from collections import defaultdict
from typing import Any, Dict

import click

from .click_common import command, format_output
from .device import Device, DeviceException

_LOGGER = logging.getLogger(__name__)


class PhilipsMoonlightException(DeviceException):
    pass


class PhilipsMoonlightStatus:
    """Container for status reports from Xiaomi Philips Zhirui Bedside Lamp."""

    def __init__(self, data: Dict[str, Any]) -> None:
        """
        Response of a Moonlight (philips.light.moonlight):

        {'pow': 'off', 'sta': 0, 'bri': 1, 'rgb': 16741971, 'cct': 1, 'snm': 0, 'spr': 0,
         'spt': 15, 'wke': 0, 'bl': 1, 'ms': 1, 'mb': 1, 'wkp': [0, 24, 0]}
        """
        self.data = data

    @property
    def power(self) -> str:
        return self.data["pow"]

    @property
    def is_on(self) -> bool:
        return self.power == "on"

    @property
    def brightness(self) -> int:
        return self.data["bri"]

    @property
    def color_temperature(self) -> int:
        return self.data["cct"]

    @property
    def rgb(self) -> int:
        return self.data["rgb"]

    @property
    def scene(self) -> int:
        return self.data["snm"]

    def __repr__(self) -> str:
        s = "<PhilipsMoonlightStatus power=%s, " \
            "brightness=%s, " \
            "color_temperature=%s, " \
            "rgb=%s, " \
            "scene=%s>" % \
            (self.power,
             self.brightness,
             self.color_temperature,
             self.rgb,
             self.scene)
        return s

    def __json__(self):
        return self.data


class PhilipsMoonlight(Device):
    """Main class representing Xiaomi Philips Zhirui Bedside Lamp.

    Not yet implemented features/methods:

    add_mb                          # Add miband
    get_band_period                 # Bracelet work time
    get_mb_rssi                     # Miband RSSI
    get_mb_mac                      # Miband MAC address
    enable_mibs
    set_band_period
    miIO.bleStartSearchBand
    miIO.bleGetNearbyBandList

    enable_sub_voice                # Sub voice control?
    enable_voice                    # Voice control

    skip_breath
    set_sleep_time
    set_wakeup_time
    en_sleep
    en_wakeup
    go_night                        # Night light / read mode
    get_wakeup_time
    enable_bl                       # Night light
    set_brirgb                      # Brightness & RGB
 
    """

    @command(
        default_output=format_output(
            "",
            "Power: {result.power}\n"
            "Brightness: {result.brightness}\n"
            "Color temperature: {result.color_temperature}\n"
            "Scene: {result.scene}\n"
        )
    )
    def status(self) -> PhilipsMoonlightStatus:
        """Retrieve properties."""
        properties = ['pow', 'sta', 'bri', 'rgb', 'cct', 'snm', 'spr', 'spt', 'wke', 'bl', 'ms',
                      'mb', 'wkp']
        values = self.send(
            "get_prop",
            properties
        )

        properties_count = len(properties)
        values_count = len(values)
        if properties_count != values_count:
            _LOGGER.debug(
                "Count (%s) of requested properties does not match the "
                "count (%s) of received values.",
                properties_count, values_count)

        return PhilipsMoonlightStatus(
            defaultdict(lambda: None, zip(properties, values)))

    @command(
        default_output=format_output("Powering on"),
    )
    def on(self):
        """Power on."""
        return self.send("set_power", ["on"])

    @command(
        default_output=format_output("Powering off"),
    )
    def off(self):
        """Power off."""
        return self.send("set_power", ["off"])

    @command(
        click.argument("rgb", type=int),
        default_output=format_output("Setting color to {rgb}")
    )
    def set_rgb(self, rgb):
        """Set color in encoded RGB."""
        if rgb < 0 or rgb > 16777215:
            raise PhilipsMoonlightException("Invalid color: %s" % rgb)

        return self.send("set_rgb", [rgb])

    @command(
        click.argument("level", type=int),
        default_output=format_output("Setting brightness to {level}")
    )
    def set_brightness(self, level: int):
        """Set brightness level."""
        if level < 1 or level > 100:
            raise PhilipsMoonlightException("Invalid brightness: %s" % level)

        return self.send("set_bright", [level])

    @command(
        click.argument("level", type=int),
        default_output=format_output("Setting color temperature to {level}")
    )
    def set_color_temperature(self, level: int):
        """Set Correlated Color Temperature."""
        if level < 1 or level > 100:
            raise PhilipsMoonlightException("Invalid color temperature: %s" % level)

        return self.send("set_cct", [level])

    @command(
        click.argument("brightness", type=int),
        click.argument("cct", type=int),
        default_output=format_output(
            "Setting brightness to {brightness} and color temperature to {cct}")
    )
    def set_brightness_and_color_temperature(self, brightness: int, cct: int):
        """Set brightness level and the correlated color temperature."""
        if brightness < 1 or brightness > 100:
            raise PhilipsMoonlightException("Invalid brightness: %s" % brightness)

        if cct < 1 or cct > 100:
            raise PhilipsMoonlightException("Invalid color temperature: %s" % cct)

        return self.send("set_bricct", [brightness, cct])

    @command(
        click.argument("number", type=int),
        default_output=format_output("Setting fixed scene to {number}")
    )
    def set_scene(self, number: int):
        """Set scene number."""
        if number < 1 or number > 4:
            raise PhilipsMoonlightException("Invalid fixed scene number: %s" % number)

        return self.send("apply_fixed_scene", [number])