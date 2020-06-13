"""Xiaomi Aqara Gateway implementation using Miio protecol."""

import logging
from datetime import datetime
from enum import Enum, IntEnum
from typing import Optional
from random import randrange

import attr
import click

from .click_common import EnumType, command, format_output
from .device import Device
from .exceptions import DeviceException
from .fake_device import ipv4_nonloop_ips
from .gateway_scripts import (
    action_id,
    build_doublepress,
    build_flip90,
    build_flip180,
    build_longpress,
    build_move,
    build_rotate,
    build_shake,
    build_shakeair,
    build_singlepress,
    build_taptap,
)
from .utils import brightness_and_color_to_int, int_to_brightness, int_to_rgb

_LOGGER = logging.getLogger(__name__)


color_map = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "white": (255, 255, 255),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
    "aqua": (0, 255, 255),
    "olive": (128, 128, 0),
    "purple": (128, 0, 128),
}


class GatewayException(DeviceException):
    """Exception for the Xioami Gateway communication."""


class DeviceType(IntEnum):
    """DeviceType matching using the values provided by Xiaomi."""

    Unknown = -1
    Gateway = 0  # lumi.0
    Switch = 1
    Motion = 2
    Magnet = 3
    SwitchTwoChannels = 7
    Cube = 8  # lumi.sensor_cube.v1
    SwitchOneChannel = 9  # lumi.ctrl_neutral1.v1
    SensorHT = 10
    Plug = 11
    RemoteSwitchSingleV1 = 14  # lumi.sensor_86sw1.v1
    SensorSmoke = 15
    AqaraHT = 19  # lumi.weather.v1
    SwitchLiveOneChannel = 20
    SwitchLiveTwoChannels = 21
    AqaraSwitch = 51
    AqaraMotion = 52
    AqaraMagnet = 53  # lumi.sensor_magnet.aq2
    AqaraRelayTwoChannels = 54
    AqaraSquareButton = 62  # lumi.sensor_switch.aq3
    AqaraSwitchOneChannel = 63
    AqaraSwitchTwoChannels = 64
    AqaraWallOutlet = 65  # lumi.ctrl_86plug.aq1
    RemoteSwitchSingle = 134  # lumi.remote.b186acn01
    RemoteSwitchDouble = 135  # lumi.remote.b286acn01


@attr.s(auto_attribs=True)
class SubDeviceInfo:
    """SubDevice discovery info."""

    sid: str
    type_id: int
    unknown: int
    unknown2: int
    fw_ver: int


class Gateway(Device):
    """Main class representing the Xiaomi Gateway.

    Use the given property getters to access specific functionalities such
    as `alarm` (for alarm controls) or `light` (for lights).

    Commands whose functionality or parameters are unknown,
    feel free to implement!
    * toggle_device
    * toggle_plug
    * remove_all_bind
    * list_bind [0]

    * self.get_prop("used_for_public") # Return the 'used_for_public' status, return value: [0] or [1], probably this has to do with developer mode.
    * self.set_prop("used_for_public", state) # Set the 'used_for_public' state, value: 0 or 1, probably this has to do with developer mode.

    * welcome
    * set_curtain_level

    * get_corridor_on_time
    * set_corridor_light ["off"]
    * get_corridor_light -> "on"

    * set_default_sound
    * set_doorbell_push, get_doorbell_push ["off"]
    * set_doorbell_volume [100], get_doorbell_volume
    * set_gateway_volume, get_gateway_volume
    * set_clock_volume
    * set_clock
    * get_sys_data
    * update_neighbor_token [{"did":x, "token":x, "ip":x}]

    ## property getters
    * ctrl_device_prop
    * get_device_prop_exp [[sid, list, of, properties]]

    ## scene
    * get_lumi_bind ["scene", <page number>] for rooms/devices"""

    def __init__(
        self,
        ip: str = None,
        token: str = None,
        start_id: int = 0,
        debug: int = 0,
        lazy_discover: bool = True,
    ) -> None:
        super().__init__(ip, token, start_id, debug, lazy_discover)
        self._alarm = GatewayAlarm(parent=self)
        self._radio = GatewayRadio(parent=self)
        self._zigbee = GatewayZigbee(parent=self)
        self._light = GatewayLight(parent=self)
        self._devices = {}

    @property
    def alarm(self) -> "GatewayAlarm":
        """Return alarm control interface."""
        # example: gateway.alarm.on()
        return self._alarm

    @property
    def radio(self) -> "GatewayRadio":
        """Return radio control interface."""
        return self._radio

    @property
    def zigbee(self) -> "GatewayZigbee":
        """Return zigbee control interface."""
        return self._zigbee

    @property
    def light(self) -> "GatewayLight":
        """Return light control interface."""
        return self._light

    @property
    def devices(self):
        """Return a dict of the already discovered devices."""
        return self._devices

    @command()
    def discover_devices(self):
        """
        Discovers SubDevices
        and returns a list of the discovered devices.
        """
        # from https://github.com/aholstenson/miio/issues/26
        device_type_mapping = {
            DeviceType.AqaraRelayTwoChannels: AqaraRelayTwoChannels,
            DeviceType.Plug: AqaraPlug,
            DeviceType.SensorHT: SensorHT,
            DeviceType.AqaraHT: AqaraHT,
            DeviceType.Cube: Cube,
            DeviceType.AqaraSquareButton: AqaraSquareButton,
            DeviceType.AqaraMagnet: AqaraMagnet,
            DeviceType.AqaraSwitchOneChannel: AqaraSwitchOneChannel,
            DeviceType.AqaraSwitchTwoChannels: AqaraSwitchTwoChannels,
            DeviceType.AqaraWallOutlet: AqaraWallOutlet,
            DeviceType.Cube: Cube,
            DeviceType.AqaraSquareButton: AqaraSquareButton,
            DeviceType.SwitchOneChannel: SwitchOneChannel,
            DeviceType.RemoteSwitchSingleV1: RemoteSwitchSingleV1,
            DeviceType.RemoteSwitchSingle: RemoteSwitchSingle,
            DeviceType.RemoteSwitchDouble: RemoteSwitchDouble,
        }
        devices_raw = self.get_prop("device_list")
        self._devices = {}

        for x in range(0, len(devices_raw), 5):
            # Extract discovered information
            dev_info = SubDeviceInfo(*devices_raw[x : x + 5])

            # Construct DeviceType
            try:
                device_type = DeviceType(dev_info.type_id)
            except ValueError:
                _LOGGER.warning(
                    "Unknown subdevice type %s discovered, "
                    "of Xiaomi gateway with ip: %s",
                    dev_info,
                    self.ip,
                )
                device_type = DeviceType(-1)

            # Obtain the correct subdevice class, ignoring the gateway itself
            subdevice_cls = device_type_mapping.get(device_type)
            if subdevice_cls is None and device_type != DeviceType.Gateway:
                subdevice_cls = SubDevice
                _LOGGER.info(
                    "Gateway device type '%s' "
                    "does not have device specific methods defined, "
                    "only basic default methods will be available",
                    device_type.name,
                )

            # Initialize and save the subdevice, ignoring the gateway itself
            if device_type != DeviceType.Gateway:
                self._devices[dev_info.sid] = subdevice_cls(self, dev_info)

        return self._devices

    def x_del(self, script_id):
        """Delete script by id."""
        return self.send("miIO.xdel", [script_id])

    @command(
        click.argument("sid"),
        click.argument("command"),
        click.argument("encoded_token"),
    )
    def subdevice_command(self, sid, command, encoded_token):
        """Send command to subdevice."""
        self.discover_devices()
        target = list(filter(lambda subdevice: subdevice.sid == sid, self.devices))
        if len(target) < 1:
            return f"Device with sid={sid} not found"
        elif not hasattr(target[0], command):
            return f"Device with sid={sid} has no method {command}"
        else:
            return getattr(target[0], command)(encoded_token)

    def install_script(self, sid, builder, encoded_token, ip=None):
        """Install script for by building script source and sending it with miio method. You need to run fake or real device to capture script execution results."""
        if ip is None:
            addresses = ipv4_nonloop_ips()
            my_ip = addresses[0]  # Taking first public IP
        else:
            my_ip = ip

        data_tkn = randrange(5000, 10000)
        source = builder(sid, my_ip, encoded_token)
        return self.send(
            "send_data_frame",
            {
                "cur": 0,
                "data": source,
                "data_tkn": data_tkn,
                "total": 1,
                "type": "scene",
            },
        )

    @command(click.argument("property"))
    def get_prop(self, property):
        """Get the value of a property for given sid."""
        return self.send("get_device_prop", ["lumi.0", property])

    @command(click.argument("properties", nargs=-1))
    def get_prop_exp(self, properties):
        """Get the value of a bunch of properties for given sid."""
        return self.send("get_device_prop_exp", [["lumi.0"] + list(properties)])

    @command(click.argument("property"), click.argument("value"))
    def set_prop(self, property, value):
        """Set the device property."""
        return self.send("set_device_prop", {"sid": "lumi.0", property: value})

    @command()
    def clock(self):
        """Alarm clock"""
        # payload of clock volume ("get_clock_volume")
        # already in get_clock response
        return self.send("get_clock")

    # Developer key
    @command()
    def get_developer_key(self):
        """Return the developer API key."""
        return self.send("get_lumi_dpf_aes_key")[0]

    @command(click.argument("key"))
    def set_developer_key(self, key):
        """Set the developer API key."""
        if len(key) != 16:
            click.echo("Key must be of length 16, was %s" % len(key))

        return self.send("set_lumi_dpf_aes_key", [key])

    @command()
    def timezone(self):
        """Get current timezone."""
        return self.get_prop("tzone_sec")

    @command()
    def get_illumination(self):
        """Get illumination. In lux?"""
        return self.send("get_illumination").pop()


class GatewayDevice(Device):
    """
    GatewayDevice class
    Specifies the init method for all gateway device functionalities.
    """

    def __init__(
        self,
        ip: str = None,
        token: str = None,
        start_id: int = 0,
        debug: int = 0,
        lazy_discover: bool = True,
        parent: Gateway = None,
    ) -> None:
        if parent is not None:
            self._gateway = parent
        else:
            self._gateway = Device(ip, token, start_id, debug, lazy_discover)
            _LOGGER.debug(
                "Creating new device instance, only use this for cli interface"
            )


class GatewayAlarm(GatewayDevice):
    """Class representing the Xiaomi Gateway Alarm."""

    @command(default_output=format_output("[alarm_status]"))
    def status(self) -> str:
        """Return the alarm status from the device."""
        # Response: 'on', 'off', 'oning'
        return self._gateway.send("get_arming").pop()

    @command(default_output=format_output("Turning alarm on"))
    def on(self):
        """Turn alarm on."""
        return self._gateway.send("set_arming", ["on"])

    @command(default_output=format_output("Turning alarm off"))
    def off(self):
        """Turn alarm off."""
        return self._gateway.send("set_arming", ["off"])

    @command()
    def arming_time(self) -> int:
        """
        Return time in seconds the alarm stays 'oning'
        before transitioning to 'on'
        """
        # Response: 5, 15, 30, 60
        return self._gateway.send("get_arm_wait_time").pop()

    @command(click.argument("seconds"))
    def set_arming_time(self, seconds):
        """Set time the alarm stays at 'oning' before transitioning to 'on'"""
        return self._gateway.send("set_arm_wait_time", [seconds])

    @command()
    def triggering_time(self) -> int:
        """Return the time in seconds the alarm is going off when triggered"""
        # Response: 30, 60, etc.
        return self._gateway.get_prop("alarm_time_len").pop()

    @command(click.argument("seconds"))
    def set_triggering_time(self, seconds):
        """Set the time in seconds the alarm is going off when triggered"""
        return self._gateway.set_prop("alarm_time_len", seconds)

    @command()
    def triggering_light(self) -> int:
        """
        Return the time the gateway light blinks
        when the alarm is triggerd
        """
        # Response: 0=do not blink, 1=always blink, x>1=blink for x seconds
        return self._gateway.get_prop("en_alarm_light").pop()

    @command(click.argument("seconds"))
    def set_triggering_light(self, seconds):
        """Set the time the gateway light blinks when the alarm is triggerd"""
        # values: 0=do not blink, 1=always blink, x>1=blink for x seconds
        return self._gateway.set_prop("en_alarm_light", seconds)

    @command()
    def triggering_volume(self) -> int:
        """Return the volume level at which alarms go off [0-100]"""
        return self._gateway.send("get_alarming_volume").pop()

    @command(click.argument("volume"))
    def set_triggering_volume(self, volume):
        """Set the volume level at which alarms go off [0-100]"""
        return self._gateway.send("set_alarming_volume", [volume])

    @command()
    def last_status_change_time(self) -> datetime:
        """
        Return the last time the alarm changed status
        """
        return datetime.fromtimestamp(self._gateway.send("get_arming_time").pop())


class GatewayZigbee(GatewayDevice):
    """Zigbee controls."""

    @command()
    def get_zigbee_version(self):
        """timeouts on device"""
        return self._gateway.send("get_zigbee_device_version")

    @command()
    def get_zigbee_channel(self):
        """Return currently used zigbee channel."""
        return self._gateway.send("get_zigbee_channel")[0]

    @command(click.argument("channel"))
    def set_zigbee_channel(self, channel):
        """Set zigbee channel."""
        return self._gateway.send("set_zigbee_channel", [channel])

    @command(click.argument("timeout", type=int))
    def zigbee_pair(self, timeout):
        """Start pairing, use 0 to disable"""
        return self._gateway.send("start_zigbee_join", [timeout])

    def send_to_zigbee(self):
        """How does this differ from writing? Unknown."""
        raise NotImplementedError()
        return self._gateway.send("send_to_zigbee")

    def read_zigbee_eep(self):
        """Read eeprom?"""
        raise NotImplementedError()
        return self._gateway.send("read_zig_eep", [0])  # 'ok'

    def read_zigbee_attribute(self):
        """Read zigbee data?"""
        raise NotImplementedError()
        return self._gateway.send("read_zigbee_attribute", [0x0000, 0x0080])

    def write_zigbee_attribute(self):
        """Unknown parameters."""
        raise NotImplementedError()
        return self._gateway.send("write_zigbee_attribute")

    @command()
    def zigbee_unpair_all(self):
        """Unpair all devices."""
        return self._gateway.send("remove_all_device")

    def zigbee_unpair(self, sid):
        """Unpair a device."""
        # get a device obj an call dev.unpair()
        raise NotImplementedError()


class GatewayRadio(GatewayDevice):
    """Radio controls for the gateway."""

    @command()
    def get_radio_info(self):
        """Radio play info."""
        return self._gateway.send("get_prop_fm")

    @command(click.argument("volume"))
    def set_radio_volume(self, volume):
        """Set radio volume"""
        return self._gateway.send("set_fm_volume", [volume])

    def play_music_new(self):
        """Unknown."""
        # {'from': '4', 'id': 9514,
        #  'method': 'set_default_music', 'params': [2, '21']}
        # {'from': '4', 'id': 9515,
        #  'method': 'play_music_new', 'params': ['21', 0]}
        raise NotImplementedError()

    def play_specify_fm(self):
        """play specific stream?"""
        raise NotImplementedError()
        # {"from": "4", "id": 65055, "method": "play_specify_fm",
        # "params": {"id": 764, "type": 0,
        # "url": "http://live.xmcdn.com/live/764/64.m3u8"}}
        return self._gateway.send("play_specify_fm")

    def play_fm(self):
        """radio on/off?"""
        raise NotImplementedError()
        # play_fm","params":["off"]}
        return self._gateway.send("play_fm")

    def volume_ctrl_fm(self):
        """Unknown."""
        raise NotImplementedError()
        return self._gateway.send("volume_ctrl_fm")

    def get_channels(self):
        """Unknown."""
        raise NotImplementedError()
        # "method": "get_channels", "params": {"start": 0}}
        return self._gateway.send("get_channels")

    def add_channels(self):
        """Unknown."""
        raise NotImplementedError()
        return self._gateway.send("add_channels")

    def remove_channels(self):
        """Unknown."""
        raise NotImplementedError()
        return self._gateway.send("remove_channels")

    def get_default_music(self):
        """seems to timeout (w/o internet)"""
        # params [0,1,2]
        raise NotImplementedError()
        return self._gateway.send("get_default_music")

    @command()
    def get_music_info(self):
        """Unknown."""
        info = self._gateway.send("get_music_info")
        click.echo("info: %s" % info)
        free_space = self._gateway.send("get_music_free_space")
        click.echo("free space: %s" % free_space)

    @command()
    def get_mute(self):
        """mute of what?"""
        return self._gateway.send("get_mute")

    def download_music(self):
        """Unknown"""
        raise NotImplementedError()
        return self._gateway.send("download_music")

    def delete_music(self):
        """delete music"""
        raise NotImplementedError()
        return self._gateway.send("delete_music")

    def download_user_music(self):
        """Unknown."""
        raise NotImplementedError()
        return self._gateway.send("download_user_music")

    def get_download_progress(self):
        """progress for music downloads or updates?"""
        # returns [':0']
        raise NotImplementedError()
        return self._gateway.send("get_download_progress")

    @command()
    def set_sound_playing(self):
        """stop playing?"""
        return self._gateway.send("set_sound_playing", ["off"])

    def set_default_music(self):
        """Unknown."""
        raise NotImplementedError()
        # method":"set_default_music","params":[0,"2"]}


class GatewayLight(GatewayDevice):
    """Light controls for the gateway."""

    @command()
    def get_night_light_rgb(self):
        """Unknown."""
        # Returns 0 when light is off?"""
        # looks like this is the same as get_rgb
        # id': 65064, 'method': 'set_night_light_rgb', 'params': [419407616]}
        # {'method': 'props', 'params':
        # {'light': 'on', 'from.light': '4,,,'}, 'id': 88457} ?!
        return self._gateway.send("get_night_light_rgb")

    @command(click.argument("color_name", type=str))
    def set_night_light_color(self, color_name):
        """Set night light color using color name (red, green, etc)."""
        if color_name not in color_map.keys():
            raise Exception(
                "Cannot find {color} in {colors}".format(
                    color=color_name, colors=color_map.keys()
                )
            )
        current_brightness = int_to_brightness(
            self._gateway.send("get_night_light_rgb")[0]
        )
        brightness_and_color = brightness_and_color_to_int(
            current_brightness, color_map[color_name]
        )
        return self._gateway.send("set_night_light_rgb", [brightness_and_color])

    @command(click.argument("color_name", type=str))
    def set_color(self, color_name):
        """Set gateway lamp color using color name (red, green, etc)."""
        if color_name not in color_map.keys():
            raise Exception(
                "Cannot find {color} in {colors}".format(
                    color=color_name, colors=color_map.keys()
                )
            )
        current_brightness = int_to_brightness(self._gateway.send("get_rgb")[0])
        brightness_and_color = brightness_and_color_to_int(
            current_brightness, color_map[color_name]
        )
        return self._gateway.send("set_rgb", [brightness_and_color])

    @command(click.argument("brightness", type=int))
    def set_brightness(self, brightness):
        """Set gateway lamp brightness (0-100)."""
        if 100 < brightness < 0:
            raise Exception("Brightness must be between 0 and 100")
        current_color = int_to_rgb(self._gateway.send("get_rgb")[0])
        brightness_and_color = brightness_and_color_to_int(brightness, current_color)
        return self._gateway.send("set_rgb", [brightness_and_color])

    @command(click.argument("brightness", type=int))
    def set_night_light_brightness(self, brightness):
        """Set night light brightness (0-100)."""
        if 100 < brightness < 0:
            raise Exception("Brightness must be between 0 and 100")
        current_color = int_to_rgb(self._gateway.send("get_night_light_rgb")[0])
        brightness_and_color = brightness_and_color_to_int(brightness, current_color)
        print(brightness, current_color)
        return self._gateway.send("set_night_light_rgb", [brightness_and_color])

    @command(
        click.argument("color_name", type=str), click.argument("brightness", type=int),
    )
    def set_light(self, color_name, brightness):
        """Set color (using color name) and brightness (0-100)."""
        if 100 < brightness < 0:
            raise Exception("Brightness must be between 0 and 100")
        if color_name not in color_map.keys():
            raise Exception(
                "Cannot find {color} in {colors}".format(
                    color=color_name, colors=color_map.keys()
                )
            )
        brightness_and_color = brightness_and_color_to_int(
            brightness, color_map[color_name]
        )
        return self._gateway.send("set_rgb", [brightness_and_color])


class SubDevice:
    """
    Base class for all subdevices of the gateway
    these devices are connected through zigbee.
    """

    _model = "unknown"

    @attr.s(auto_attribs=True)
    class props:
        """Defines properties of the specific device"""

    def __init__(self, gw: Gateway = None, dev_info: SubDeviceInfo = None,) -> None:
        self._gw = gw
        self.sid = dev_info.sid
        self._battery = None
        self._fw_ver = dev_info.fw_ver
        self._props = self.props()
        try:
            self.type = DeviceType(dev_info.type_id)
        except ValueError:
            self.type = DeviceType.Unknown

    def __repr__(self):
        return "<Subdevice %s: %s fw: %s bat: %s props: %s>" % (
            self.device_type,
            self.sid,
            self._fw_ver,
            self.get_battery(),
            self.status,
        )

    @property
    def status(self):
        """Return sub-device status as a dict containing all properties."""
        return attr.asdict(self._props)

    @property
    def device_type(self):
        """Return the device type name."""
        return self.type.name

    @property
    def model(self):
        """Return the device model."""
        return self._model

    @property
    def firmware_version(self):
        """Return the firmware version."""
        return self._fw_ver

    @property
    def battery(self):
        """Return the battery level."""
        return self._battery

    @command()
    def update(self):
        """Update the device-specific properties."""
        _LOGGER.debug(
            "Subdevice '%s' does not have a device specific update method defined",
            self.device_type,
        )

    @command()
    def send(self, command):
        """Send a command/query to the subdevice"""
        try:
            return self._gw.send(command, [self.sid])
        except Exception as ex:
            raise GatewayException(
                "Got an exception while sending command %s" % (command)
            ) from ex

    @command()
    def send_arg(self, command, arguments):
        """Send a command/query including arguments to the subdevice"""
        try:
            return self._gw.send(command, arguments, extra_parameters={"sid": self.sid})
        except Exception as ex:
            raise GatewayException(
                "Got an exception while sending "
                "command '%s' with arguments '%s'" % (command, str(arguments))
            ) from ex

    @command(click.argument("property"))
    def get_property(self, property):
        """Get the value of a property of the subdevice."""
        try:
            response = self._gw.send("get_device_prop", [self.sid, property])
        except Exception as ex:
            raise GatewayException(
                "Got an exception while fetching property %s" % (property)
            ) from ex

        if not response:
            raise GatewayException(
                "Empty response while fetching property '%s': %s" % (property, response)
            )

        return response

    @command(click.argument("properties", nargs=-1))
    def get_property_exp(self, properties):
        """Get the value of a bunch of properties of the subdevice."""
        try:
            response = self._gw.send(
                "get_device_prop_exp", [[self.sid] + list(properties)]
            ).pop()
        except Exception as ex:
            raise GatewayException(
                "Got an exception while fetching properties %s: %s" % (properties)
            ) from ex

        if len(list(properties)) != len(response):
            raise GatewayException(
                "unexpected result while fetching properties %s: %s"
                % (properties, response)
            )

        return response

    @command(click.argument("property"), click.argument("value"))
    def set_property(self, property, value):
        """Set a device property of the subdevice."""
        try:
            return self._gw.send("set_device_prop", {"sid": self.sid, property: value})
        except Exception as ex:
            raise GatewayException(
                "Got an exception while setting propertie %s to value %s"
                % (property, str(value))
            ) from ex

    @command()
    def unpair(self):
        """Unpair this device from the gateway."""
        return self.send("remove_device")

    @command()
    def get_battery(self):
        """Update the battery level and return the new value."""
        self._battery = self.send("get_battery").pop()
        return self._battery

    @command()
    def get_firmware_version(self) -> Optional[int]:
        """Returns firmware version"""
        try:
            self._fw_ver = self.get_property("fw_ver").pop()
        except Exception as ex:
            _LOGGER.info(
                "get_firmware_version failed, returning firmware version from discovery info: %s",
                ex,
            )
        return self._fw_ver

    @command()
    def uninstall_scripts(self, encoded_token):
        return dict(
            map(
                lambda action: (
                    action,
                    (
                        action_id[action](self.sid),
                        self._gw.x_del(action_id[action](self.sid)),
                    ),
                ),
                action_id.keys(),
            )
        )


class AqaraHT(SubDevice):
    """Subdevice AqaraHT specific properties and methods"""

    accessor = "get_prop_sensor_ht"
    properties = ["temperature", "humidity", "pressure"]
    _model = "lumi.weather.v1"

    @attr.s(auto_attribs=True)
    class props:
        """Device specific properties"""

        temperature: int = None  # in degrees celsius
        humidity: int = None  # in %
        pressure: int = None  # in hPa

    @command()
    def update(self):
        """Update all device properties"""
        values = self.get_property_exp(self.properties)
        try:
            self._props.temperature = values[0] / 100
            self._props.humidity = values[1] / 100
            self._props.pressure = values[2] / 100
        except Exception as ex:
            raise GatewayException(
                "One or more unexpected results while "
                "fetching properties %s: %s" % (self.properties, values)
            ) from ex


class SensorHT(SubDevice):
    """Subdevice SensorHT specific properties and methods"""

    accessor = "get_prop_sensor_ht"
    properties = ["temperature", "humidity", "pressure"]
    _model = "unknown"

    @attr.s(auto_attribs=True)
    class props:
        """Device specific properties"""

        temperature: int = None  # in degrees celsius
        humidity: int = None  # in %
        pressure: int = None  # in hPa

    @command()
    def update(self):
        """Update all device properties"""
        values = self.get_property_exp(self.properties)
        try:
            self._props.temperature = values[0] / 100
            self._props.humidity = values[1] / 100
            self._props.pressure = values[2] / 100
        except Exception as ex:
            raise GatewayException(
                "One or more unexpected results while "
                "fetching properties %s: %s" % (self.properties, values)
            ) from ex


class AqaraMagnet(SubDevice):
    """Subdevice AqaraMagnet specific properties and methods"""

    properties = ["unkown"]
    _model = "lumi.sensor_magnet.aq2"

    @attr.s(auto_attribs=True)
    class props:
        """Device specific properties"""

        status: str = None  # 'open' or 'closed'

    @command()
    def update(self):
        """Update all device properties"""
        values = self.get_property_exp(self.properties)
        self._props.status = values[0]


class AqaraPlug(SubDevice):
    """Subdevice AqaraPlug specific properties and methods"""

    accessor = "get_prop_plug"
    properties = ["power", "neutral_0", "load_power"]
    _model = "unknown"

    @attr.s(auto_attribs=True)
    class props:
        """Device specific properties"""

        status: str = None  # 'on' / 'off'
        power: int = None  # diffrent power consumption?? in ?unit?
        load_power: int = None  # power consumption in ?unit?

    @command()
    def update(self):
        """Update all device properties"""
        values = self.get_property_exp(self.properties)
        self._props.power = values[0]
        self._props.status = values[1]
        self._props.load_power = values[2]


class AqaraRelayTwoChannels(SubDevice):
    """Subdevice AqaraRelayTwoChannels specific properties and methods"""

    properties = ["load_power", "channel_0", "channel_1"]
    _model = "unknown"

    @attr.s(auto_attribs=True)
    class props:
        """Device specific properties"""

        status_ch0: str = None  # 'on' / 'off'
        status_ch1: str = None  # 'on' / 'off'
        load_power: int = None  # power consumption in ?unit?

    class AqaraRelayToggleValue(Enum):
        """Options to control the relay"""

        toggle = "toggle"
        on = "on"
        off = "off"

    class AqaraRelayChannel(Enum):
        """Options to select wich relay to control"""

        first = "channel_0"
        second = "channel_1"

    @command()
    def update(self):
        """Update all device properties"""
        values = self.get_property_exp(self.properties)
        self._props.load_power = values[0]
        self._props.status_ch0 = values[1]
        self._props.status_ch1 = values[2]

    @command(
        click.argument("channel", type=EnumType(AqaraRelayChannel)),
        click.argument("value", type=EnumType(AqaraRelayToggleValue)),
    )
    def toggle(self, channel, value):
        """Toggle Aqara Wireless Relay 2ch"""
        return self.send_arg("toggle_ctrl_neutral", [channel.value, value.value]).pop()


class AqaraSwitchOneChannel(SubDevice):
    """Subdevice AqaraSwitchOneChannel specific properties and methods"""

    properties = ["neutral_0", "load_power"]
    _model = "unknown"

    @attr.s(auto_attribs=True)
    class props:
        """Device specific properties"""

        status: str = None  # 'on' / 'off'
        load_power: int = None  # power consumption in ?unit?

    @command()
    def update(self):
        """Update all device properties"""
        values = self.get_property_exp(self.properties)
        self._props.status = values[0]
        self._props.load_power = values[1]


class AqaraSwitchTwoChannels(SubDevice):
    """Subdevice AqaraSwitchTwoChannels specific properties and methods"""

    properties = ["neutral_0", "neutral_1", "load_power"]
    _model = "unknown"

    @attr.s(auto_attribs=True)
    class props:
        """Device specific properties"""

        status_ch0: str = None  # 'on' / 'off'
        status_ch1: str = None  # 'on' / 'off'
        load_power: int = None  # power consumption in ?unit?

    @command()
    def update(self):
        """Update all device properties"""
        values = self.get_property_exp(self.properties)
        self._props.status_ch0 = values[0]
        self._props.status_ch1 = values[1]
        self._props.load_power = values[2]

class Cube(SubDevice):
    """Subdevice Cube specific properties and methods"""

    properties = []

    @command()
    def install_move_script(self, encoded_token):
        """Generate and install script which captures move event and sends miio package to device"""
        return self._gw.install_script(self.sid, build_move, encoded_token)

    @command()
    def install_rotate_script(self, encoded_token):
        """Generate and install script which captures rotate event and sends miio package to device"""
        return self._gw.install_script(self.sid, build_rotate, encoded_token)

    @command()
    def install_shake_script(self, encoded_token):
        """Generate and install script which captures shake in air event and sends miio package to device"""
        return self._gw.install_script(self.sid, build_shakeair, encoded_token)

    @command()
    def install_flip90_script(self, encoded_token):
        """Generate and install script which captures horizontal 90 flip and sends miio package to device"""
        return self._gw.install_script(self.sid, build_flip90, encoded_token)

    @command()
    def install_taptap_script(self, encoded_token):
        """Generate and install script which captures double tap on surface event and sends miio package to device"""
        return self._gw.install_script(self.sid, build_taptap, encoded_token)

    @command()
    def install_flip180_script(self, encoded_token):
        """Generate and install script which captures horizontal 180 flip and sends miio package to device"""
        return self._gw.install_script(self.sid, build_flip180, encoded_token)


class AqaraSquareButton(SubDevice):
    """Subdevice AqaraSquareButton specific properties and methods"""

    properties = []

    @command()
    def install_singlepress_script(self, encoded_token):
        """Generate and install script which captures single press event and sends miio package to device"""
        return self._gw.install_script(self.sid, build_singlepress, encoded_token)

    @command()
    def install_doublepress_script(self, encoded_token):
        """Generate and install script which captures double press event and sends miio package to device"""
        return self._gw.install_script(self.sid, build_doublepress, encoded_token)

    @command()
    def install_longpress_script(self, encoded_token):
        """Generate and install script which captures loooong press event and sends miio package to device"""
        return self._gw.install_script(self.sid, build_longpress, encoded_token)

    @command()
    def install_shake_script(self, encoded_token):
        """Generate and install script which captures shake in air event and sends miio package to device"""
        return self._gw.install_script(self.sid, build_shake, encoded_token)


class AqaraWallOutlet(SubDevice):
    """Subdevice AqaraWallOutlet specific properties and methods"""

    properties = ["channel_0", "load_power"]
    _model = "lumi.ctrl_86plug.aq1"

    @attr.s(auto_attribs=True)
    class props:
        """Device specific properties"""

        status: str = None  # 'on' / 'off'
        load_power: int = None  # power consumption in Watt

    @command()
    def update(self):
        """Update all device properties"""
        values = self.get_property_exp(self.properties)
        self._props.status = values[0]
        self._props.load_power = values[1]

    @command()
    def toggle(self):
        """Toggle Aqara Wall Outlet"""
        return self.send_arg("toggle_plug", ["channel_0", "toggle"]).pop()

    @command()
    def on(self):
        """Turn on Aqara Wall Outlet"""
        return self.send_arg("toggle_plug", ["channel_0", "on"]).pop()

    @command()
    def off(self):
        """Turn off Aqara Wall Outlet"""
        return self.send_arg("toggle_plug", ["channel_0", "off"]).pop()


class Cube(SubDevice):
    """Subdevice Cube specific properties and methods"""

    properties = []
    _model = "lumi.sensor_cube.v1"


class AqaraSquareButton(SubDevice):
    """Subdevice AqaraSquareButton specific properties and methods"""

    properties = []
    _model = "lumi.sensor_switch.aq3"


class SwitchOneChannel(SubDevice):
    """Subdevice SwitchOneChannel specific properties and methods"""

    properties = ["neutral_0"]
    _model = "lumi.ctrl_neutral1.v1"

    @attr.s(auto_attribs=True)
    class props:
        """Device specific properties"""

        status: str = None  # 'on' / 'off'

    @command()
    def update(self):
        """Update all device properties"""
        values = self.get_property_exp(self.properties)
        self._props.status = values[0]

    @command()
    def toggle(self):
        """Toggle Switch One Channel"""
        return self.send_arg("toggle_ctrl_neutral", ["channel_0", "toggle"]).pop()

    @command()
    def on(self):
        """Turn on Switch One Channel"""
        return self.send_arg("toggle_ctrl_neutral", ["channel_0", "on"]).pop()

    @command()
    def off(self):
        """Turn off Switch One Channel"""
        return self.send_arg("toggle_ctrl_neutral", ["channel_0", "off"]).pop()


class RemoteSwitchSingleV1(SubDevice):
    """Subdevice RemoteSwitchSingleV1 specific properties and methods"""

    properties = []
    _model = "lumi.sensor_86sw1.v1"


class RemoteSwitchSingle(SubDevice):
    """Subdevice RemoteSwitchSingle specific properties and methods"""

    properties = []
    _model = "lumi.remote.b186acn01"


class RemoteSwitchDouble(SubDevice):
    """Subdevice RemoteSwitchDouble specific properties and methods"""

    properties = []
    _model = "lumi.remote.b286acn01"
