"""Unit tests for toilet lid.

Response instance
>> status

Work: False
State: 1
Ambient Light: Yellow
Filter remaining: 100%
Filter remaining time: 180
"""
from unittest import TestCase

import pytest

from miio.toiletlid import (
    MODEL_TOILETLID_V1,
    AmbientLightColor,
    Toiletlid,
    ToiletlidStatus,
)

from .dummies import DummyDevice


class DummyToiletlidV1(DummyDevice, Toiletlid):
    def __init__(self, *args, **kwargs):
        self._model = MODEL_TOILETLID_V1
        self.state = {
            "is_on": False,
            "work_state": 1,
            "work_mode": "Vacant",
            "ambient_light": "Yellow",
            "filter_use_flux": "100",
            "filter_use_time": "180",
        }
        self.users = {}

        self.return_values = {
            "get_prop": self._get_state,
            "nozzle_clean": lambda x: self._set_state("work_state", [97]),
            "set_aled_v_of_uid": self.set_aled_v_of_uid,
            "get_aled_v_of_uid": self.get_aled_v_of_uid,
            "uid_mac_op": self.uid_mac_op,
            "get_all_user_info": self.get_all_user_info,
        }
        super().__init__(args, kwargs)

    def set_aled_v_of_uid(self, args):
        uid, color = args
        if uid:
            if uid not in self.users:
                raise ValueError("This user is not bind.")

            self.users.setdefault("ambient_light", AmbientLightColor(color).name)
        else:
            return self._set_state("ambient_light", [AmbientLightColor(color).name])

    def get_aled_v_of_uid(self, args):
        uid = args[0]
        if uid:
            if uid not in self.users:
                raise ValueError("This user is not b.")

            color = self.users.get("ambient_light")
        else:
            color = self._get_state(["ambient_light"])
        if not AmbientLightColor._member_map_.get(color[0]):
            raise ValueError(color)
        return AmbientLightColor._member_map_.get(color[0]).value

    def uid_mac_op(self, args):
        xiaomi_id, band_mac, alias, operating = args
        if operating not in ["bind", "unbind"]:
            raise ValueError("operating not bind or unbind, but %s" % operating)

        if operating == "bind":
            info = self.users.setdefault(
                xiaomi_id, {"rssi": -50, "set": "3-0-2-2-0-0-5-5"}
            )
            info.update(mac=band_mac, name=alias)
        elif operating == "unbind":
            self.users.pop(xiaomi_id)

    def get_all_user_info(self):
        users = {}
        for index, (xiaomi_id, info) in enumerate(self.users.items(), start=1):
            user_id = "user%s" % index
            users[user_id] = {"uid": xiaomi_id, **info}
        return users


@pytest.fixture(scope="class")
def toiletlidv1(request):
    request.cls.device = DummyToiletlidV1()
    # TODO add ability to test on a real device


@pytest.mark.usefixtures("toiletlidv1")
class TestToiletlidV1(TestCase):
    MOCK_USER = {
        "11111111": {
            "mac": "ff:ff:ff:ff:ff:ff",
            "name": "myband",
            "rssi": -50,
            "set": "3-0-2-2-0-0-5-5",
        }
    }

    def is_on(self):
        return self.device.status().is_on

    def state(self):
        return self.device.status()

    def test_status(self):
        self.device._reset_state()

        assert repr(self.state()) == repr(ToiletlidStatus(self.device.start_state))

        assert self.is_on() is False
        assert self.state().work_state == self.device.start_state["work_state"]
        assert self.state().ambient_light == self.device.start_state["ambient_light"]
        assert (
            self.state().filter_use_percentage
            == "%s%%" % self.device.start_state["filter_use_flux"]
        )
        assert (
            self.state().filter_remaining_time
            == self.device.start_state["filter_use_time"]
        )

    def test_set_ambient_light(self):
        for value, enum in AmbientLightColor._member_map_.items():
            self.device.set_ambient_light(enum)
            assert self.device.status().ambient_light == value

    def test_nozzle_clean(self):
        self.device.nozzle_clean()
        assert self.is_on() is True
        self.device._reset_state()

    def test_get_all_user_info(self):
        users = self.device.get_all_user_info()
        for _name, info in users.items():
            assert info["uid"] in self.MOCK_USER
            data = self.MOCK_USER[info["uid"]]
            assert info["name"] == data["name"]
            assert info["mac"] == data["mac"]

    def test_bind_xiaomi_band(self):
        for xiaomi_id, info in self.MOCK_USER.items():
            self.device.bind_xiaomi_band(xiaomi_id, info["mac"], info["name"])
        assert self.device.users == self.MOCK_USER

    def test_unbind_xiaomi_band(self):
        for xiaomi_id, info in self.MOCK_USER.items():
            self.device.unbind_xiaomi_band(xiaomi_id, info["mac"])
        assert self.device.users == {}
