import string
from unittest import TestCase

import pytest

from miio import IHCooker, ihcooker

from .dummies import DummyDevice

# V1 state from @EUA
# ['waiting', '02537465616d2f626f696c000000000002', '0013000000', '0100010000000000', '001b0a04', '00000001000000020000000300000004000000050000a4e000000dcc00000000', '00', '0000e60a0017130f00']

# V2 state from @aquarat
# ['running', '01484f54504f540000000000000000000000000000000000000000000000000001', '00306300b9', '0200013b00000000', '000a1404', '0000000100000002000000030000000400000005000000000000000000000000', '01', '0000ea4a6330303400'


class DummyIHCookerV2(DummyDevice, IHCooker):
    def __init__(self, *args, **kwargs):
        self._model = ihcooker.MODEL_EXP1

        self.state = [
            "running",
            "08526963650000000000000000000000000000000000000000000000000000001e",
            "033c14083c",
            "000f000400000000",
            "000d1404",
            "0000000100000002000000030000000400000005000000180000001a0000001e",
            "01",
            "0306eb0a001d3c3c00",
        ]
        self.return_values = {
            "get_prop": self._get_state,
            "set_start": lambda profile: self._validate_profile(profile[0]),
            "set_menu1": lambda profile: self._validate_profile(profile[0]),
        }
        super().__init__(args, kwargs)

    def _get_state(self, vars):
        """Return wanted properties"""
        assert vars == ["all"], "Only get_props all is supported"
        return self.state

    @staticmethod
    def _validate_profile(profile):
        """Validates if profile is a valid string."""
        assert all(c in string.hexdigits for c in profile) and len(profile) == 358


class DummyIHCookerV1(DummyIHCookerV2):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self._model = ihcooker.MODEL_V1

        self.state = [
            "waiting",
            "02537465616d2f626f696c000000000002",
            "0013000000",
            "0100010000000000",
            "001b0a04",
            "00000001000000020000000300000004000000050000a4e000000dcc00000000",
            "00",
            "0000e60a0017130f00",
        ]


@pytest.fixture(scope="class")
def ihcooker_exp1(request):
    request.cls.device = DummyIHCookerV2()


@pytest.fixture(scope="class")
def ihcooker_v1(request):
    request.cls.device = DummyIHCookerV1()


@pytest.mark.usefixtures("ihcooker_exp1")
class TestIHCookerV2(TestCase):
    def state(self):
        return self.device.status()

    def test_recipe(self):
        recipe = ihcooker.CookProfile(self.device.model)
        self.device.start(recipe)

    def test_mode(self):
        self.assertEqual(ihcooker.OperationMode.Running, self.state().mode)

    def test_temperature(self):
        self.assertEqual(60, self.state().temperature)

    def test_target_temp(self):
        self.assertEqual(60, self.state().target_temp)

    def test_menu_text(self):
        self.assertEqual("Rice", self.state().recipe_name)

    def test_recipe_id(self):
        self.assertEqual(30, self.state().recipe_id)

    def test_stage(self):
        self.assertEqual(3, self.state().stage)

    def test_stage_mode(self):
        self.assertEqual(8, self.state().stage_mode)


@pytest.mark.usefixtures("ihcooker_v1")
class TestIHCookerv1(TestCase):
    def state(self):
        return self.device.status()

    def test_recipe(self):
        recipe = ihcooker.CookProfile(self.device.model)
        self.device.start(recipe)

    def test_mode(self):
        self.assertEqual(ihcooker.OperationMode.Waiting, self.state().mode)

    def test_temperature(self):
        self.assertEqual(19, self.state().temperature)

    def test_target_temp(self):
        self.assertEqual(0, self.state().target_temp)

    def test_menu_text(self):
        self.assertEqual("Steam/boil", self.state().recipe_name)

    def test_recipe_id(self):
        self.assertEqual(2, self.state().recipe_id)

    def test_stage(self):
        self.assertEqual(0, self.state().stage)

    def test_stage_mode(self):
        self.assertEqual(0, self.state().stage_mode)
