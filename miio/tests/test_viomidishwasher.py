from datetime import datetime, timedelta
from unittest import TestCase

import pytest

from miio import ViomiDishwasher
from miio.exceptions import DeviceException
from miio.viomidishwasher import (
    MODEL_DISWAHSER_M02,
    ChildLockStatus,
    MachineStatus,
    Program,
    ProgramStatus,
    SystemStatus,
    ViomiDishwasherStatus,
)

from .dummies import DummyDevice


class DummyViomiDishwasher(DummyDevice, ViomiDishwasher):
    def __init__(self, *args, **kwargs):
        self.model = MODEL_DISWAHSER_M02
        self.dummy_device_info = {
            "ap": {
                "bssid": "18:E8:FF:FF:F:FF",
                "primary": 6,
                "rssi": -58,
                "ssid": "ap",
            },
            "fw_ver": "2.1.0",
            "hw_ver": "esp8266",
            "ipflag": 1,
            "life": 93832,
            "mac": "44:FF:F:F:FF:FF",
            "mcu_fw_ver": "0018",
            "miio_ver": "0.0.8",
            "mmfree": 25144,
            "model": "viomi.dishwasher.m02",
            "netif": {
                "gw": "192.168.0.1",
                "localIp": "192.168.0.25",
                "mask": "255.255.255.0",
            },
            "token": "68ffffffffffffffffffffffffffffff",
            "uid": 0xFFFFFFFF,
            "wifi_fw_ver": "2709610",
        }

        self.device_info = None

        self.state = {
            "power": 1,
            "program": 2,
            "wash_temp": 55,
            "wash_status": 2,
            "wash_process": 3,
            "child_lock": 1,
            "run_status": 32 + 128 + 512,
            "left_time": 1337,
            "wash_done_appointment": 0,
            "freshdry_interval": 0,
        }
        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_wash_status": lambda x: self._set_state("wash_status", x),
            "set_program": lambda x: self._set_state("program", x),
            "set_wash_done_appointment": lambda x: self._set_state(
                "wash_done_appointment", [int(x[0].split(",")[0])]
            ),
            "set_freshdry_interval_t": lambda x: self._set_state(
                "freshdry_interval", x
            ),
            "set_child_lock": lambda x: self._set_state("child_lock", x),
            "miIO.info": self._get_device_info,
        }
        super().__init__(args, kwargs)

    def _get_device_info(self, _):
        """Return dummy device info."""
        return self.dummy_device_info


@pytest.fixture(scope="class")
def dishwasher(request):
    request.cls.device = DummyViomiDishwasher()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("dishwasher")
class TestViomiDishwasher(TestCase):
    def is_on(self):
        return self.device._is_on()

    def state(self):
        return self.device.status()

    def test_on(self):
        self.device.off()  # ensure off
        assert self.is_on() is False

        self.device.on()
        assert self.is_on() is True

    def test_off(self):
        self.device.on()  # ensure on
        assert self.is_on() is True

        self.device.off()
        assert self.is_on() is False

    def test_status(self):
        self.device._reset_state()

        assert repr(self.state()) == repr(
            ViomiDishwasherStatus(self.device.start_state)
        )

        assert self.state().power is True
        assert self.state().program == Program.Quick
        assert self.state().door_open is True
        assert self.state().child_lock is True
        assert self.state().program_progress == ProgramStatus.Rinse
        assert self.state().status == MachineStatus.Running
        assert self.device._is_running() is True
        assert SystemStatus.ThermistorError in self.state().errors
        assert SystemStatus.InsufficientWaterSoftener in self.state().errors
        self.assertIsInstance(self.state().air_refresh_interval, int)
        self.assertIsInstance(self.state().temperature, int)

    def test_child_lock(self):
        self.device.on()  # ensure on
        assert self.is_on() is True

        self.device.child_lock(ChildLockStatus.Enabled)
        assert self.state().child_lock is True

        self.device.child_lock(ChildLockStatus.Disabled)
        assert self.state().child_lock is False

    def test_program(self):
        self.device.on()  # ensure on
        assert self.is_on() is True

        self.device.start(Program.Intensive)
        assert self.state().program == Program.Intensive

    def test_schedule(self):
        self.device.on()  # ensure on
        assert self.is_on() is True

        too_short_time = datetime.now() + timedelta(hours=1)
        self.assertRaises(
            DeviceException, self.device.schedule, too_short_time, Program.Eco
        )

        self.device.stop()
        self.device.state["wash_process"] = 0

        enough_time = (datetime.now() + timedelta(hours=1)).replace(
            second=0, microsecond=0
        )
        self.device.schedule(enough_time, Program.Quick)
        self.assertIsInstance(self.state().schedule, datetime)
        assert self.state().schedule == enough_time

    def test_freshdry_interval(self):
        self.device.on()  # ensure on
        assert self.is_on() is True

        self.assertIsInstance(self.state().air_refresh_interval, int)

        self.device.airrefresh(8)
        assert self.state().air_refresh_interval == 8
