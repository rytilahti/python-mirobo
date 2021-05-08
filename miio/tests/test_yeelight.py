from unittest import TestCase

import pytest

from miio import Yeelight
from miio.yeelight import YeelightException, YeelightMode, YeelightStatus

from .dummies import DummyDevice


class DummyLight(DummyDevice, Yeelight):
    def __init__(self, *args, **kwargs):
        self.state = {
            "power": "off",
            "bright": "100",
            "ct": "3584",
            "rgb": "16711680",
            "hue": "359",
            "sat": "100",
            "color_mode": "2",
            "name": "test name",
            "lan_ctrl": "1",
            "save_state": "1",
            "delayoff": "60",
            "music_on": "1",
            "flowing": "0",
            "flow_params": "",
            "active_mode": "1",
            "nl_br": "100",
            "bg_power": "off",
            "bg_bright": "100",
            "bg_lmode": "2",
            "bg_rgb": "16711680",
            "bg_hue": "359",
            "bg_sat": "100",
            "bg_ct": "3584",
            "bg_flowing": "0",
            "bg_flow_params": "",
        }

        self.return_values = {
            "get_prop": self._get_state,
            "set_power": lambda x: self._set_state("power", x),
            "set_bright": lambda x: self._set_state("bright", x),
            "set_ct_abx": lambda x: self._set_state("ct", x),
            "set_rgb": lambda x: self._set_state("rgb", x),
            "set_hsv": lambda x: self._set_state("hsv", x),
            "set_name": lambda x: self._set_state("name", x),
            "set_ps": lambda x: self.set_config(x),
            "toggle": self.toggle_power,
            "set_default": lambda x: "ok",
        }

        super().__init__(*args, **kwargs)

    def set_config(self, x):
        key, value = x
        config_mapping = {"cfg_lan_ctrl": "lan_ctrl", "cfg_save_state": "save_state"}

        self._set_state(config_mapping[key], [value])

    def toggle_power(self, _):
        if self.state["power"] == "on":
            self.state["power"] = "off"
        else:
            self.state["power"] = "on"


@pytest.fixture(scope="class")
def dummylight(request):
    request.cls.device = DummyLight()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("dummylight")
class TestYeelight(TestCase):
    def test_status(self):
        self.device._reset_state()
        status = self.device.status()  # type: YeelightStatus

        assert repr(status) == repr(YeelightStatus(self.device.start_state))

        assert status.name == self.device.start_state["name"]
        assert status.is_on is False
        assert status.brightness == 100
        assert status.color_temp == 3584
        assert status.color_mode == YeelightMode.ColorTemperature
        assert status.rgb is None
        assert status.developer_mode is True
        assert status.save_state_on_change is True

        # following are tested in set mode tests
        # assert status.rgb == 16711680
        # assert status.hsv == (359, 100, 100)

    def test_on(self):
        self.device.off()  # make sure we are off
        assert self.device.status().is_on is False

        self.device.on()
        assert self.device.status().is_on is True

    def test_off(self):
        self.device.on()  # make sure we are on
        assert self.device.status().is_on is True

        self.device.off()
        assert self.device.status().is_on is False

    def test_set_brightness(self):
        def brightness():
            return self.device.status().brightness

        self.device.set_brightness(50)
        assert brightness() == 50
        self.device.set_brightness(0)
        assert brightness() == 0
        self.device.set_brightness(100)

        with pytest.raises(YeelightException):
            self.device.set_brightness(-100)

        with pytest.raises(YeelightException):
            self.device.set_brightness(200)

    def test_set_color_temp(self):
        def color_temp():
            return self.device.status().color_temp

        self.device.set_color_temp(2000)
        assert color_temp() == 2000
        self.device.set_color_temp(6500)
        assert color_temp() == 6500

        with pytest.raises(YeelightException):
            self.device.set_color_temp(1000)

        with pytest.raises(YeelightException):
            self.device.set_color_temp(7000)

    def test_set_rgb(self):
        def rgb():
            return self.device.status().rgb

        self.device._reset_state()
        self.device._set_state("color_mode", [1])

        assert rgb() == (255, 0, 0)

        self.device.set_rgb((0, 0, 1))
        assert rgb() == (0, 0, 1)
        self.device.set_rgb((255, 255, 0))
        assert rgb() == (255, 255, 0)
        self.device.set_rgb((255, 255, 255))
        assert rgb() == (255, 255, 255)

        with pytest.raises(YeelightException):
            self.device.set_rgb((-1, 0, 0))

        with pytest.raises(YeelightException):
            self.device.set_rgb((256, 0, 0))

        with pytest.raises(YeelightException):
            self.device.set_rgb((0, -1, 0))

        with pytest.raises(YeelightException):
            self.device.set_rgb((0, 256, 0))

        with pytest.raises(YeelightException):
            self.device.set_rgb((0, 0, -1))

        with pytest.raises(YeelightException):
            self.device.set_rgb((0, 0, 256))

    @pytest.mark.skip("hsv is not properly implemented")
    def test_set_hsv(self):
        self.reset_state()
        hue, sat, val = self.device.status().hsv
        assert hue == 359
        assert sat == 100
        assert val == 100

        self.device.set_hsv()

    def test_set_developer_mode(self):
        def dev_mode():
            return self.device.status().developer_mode

        orig_mode = dev_mode()
        self.device.set_developer_mode(not orig_mode)
        new_mode = dev_mode()
        assert new_mode is not orig_mode
        self.device.set_developer_mode(not new_mode)
        assert new_mode is not dev_mode()

    def test_set_save_state_on_change(self):
        def save_state():
            return self.device.status().save_state_on_change

        orig_state = save_state()
        self.device.set_save_state_on_change(not orig_state)
        new_state = save_state()
        assert new_state is not orig_state
        self.device.set_save_state_on_change(not new_state)
        new_state = save_state()
        assert new_state is orig_state

    def test_set_name(self):
        def name():
            return self.device.status().name

        assert name() == "test name"
        self.device.set_name("new test name")
        assert name() == "new test name"

    def test_toggle(self):
        def is_on():
            return self.device.status().is_on

        orig_state = is_on()
        self.device.toggle()
        new_state = is_on()
        assert orig_state != new_state

        self.device.toggle()
        new_state = is_on()
        assert new_state == orig_state

    @pytest.mark.skip("cannot be tested easily")
    def test_set_default(self):
        self.fail()

    @pytest.mark.skip("set_scene is not implemented")
    def test_set_scene(self):
        self.fail()
