import math

import pytest

from miio import Device
from miio.exceptions import DeviceInfoUnavailableException, PayloadDecodeException


@pytest.mark.parametrize("max_properties", [None, 1, 15])
def test_get_properties_splitting(mocker, max_properties):
    properties = [i for i in range(20)]

    send = mocker.patch("miio.Device.send")
    d = Device("127.0.0.1", "68ffffffffffffffffffffffffffffff")
    d.get_properties(properties, max_properties=max_properties)

    if max_properties is None:
        max_properties = len(properties)
    assert send.call_count == math.ceil(len(properties) / max_properties)


def test_default_timeout_and_retry(mocker):
    send = mocker.patch("miio.miioprotocol.MiIOProtocol.send")
    d = Device("127.0.0.1", "68ffffffffffffffffffffffffffffff")
    assert d._protocol._timeout == 5
    d.send(command="fake_command", parameters=[])
    send.assert_called_with("fake_command", [], 3, extra_parameters=None)


def test_timeout_retry(mocker):
    send = mocker.patch("miio.miioprotocol.MiIOProtocol.send")
    d = Device("127.0.0.1", "68ffffffffffffffffffffffffffffff", timeout=4)
    assert d._protocol._timeout == 4
    d.send("fake_command", [], 1)
    send.assert_called_with("fake_command", [], 1, extra_parameters=None)
    d.send("fake_command", [])
    send.assert_called_with("fake_command", [], 3, extra_parameters=None)

    class CustomDevice(Device):
        retry_count = 5
        timeout = 1

    d2 = CustomDevice("127.0.0.1", "68ffffffffffffffffffffffffffffff")
    assert d2._protocol._timeout == 1
    d2.send("fake_command", [])
    send.assert_called_with("fake_command", [], 5, extra_parameters=None)


def test_unavailable_device_info_raises(mocker):
    """Make sure custom exception is raised if the info payload is invalid."""
    send = mocker.patch("miio.Device.send", side_effect=PayloadDecodeException)
    d = Device("127.0.0.1", "68ffffffffffffffffffffffffffffff")

    with pytest.raises(DeviceInfoUnavailableException):
        d.info()

    assert send.call_count == 1


def test_model_autodetection(mocker):
    """Make sure info() gets called if the model is unknown."""
    info = mocker.patch("miio.Device.info")
    _ = mocker.patch("miio.Device.send")

    d = Device("127.0.0.1", "68ffffffffffffffffffffffffffffff")

    d.raw_command("cmd", {})

    info.assert_called()


def test_forced_model(mocker):
    """Make sure info() does not get called automatically if model is given."""
    info = mocker.patch("miio.Device.info")
    _ = mocker.patch("miio.Device.send")

    DUMMY_MODEL = "dummy.model"

    d = Device("127.0.0.1", "68ffffffffffffffffffffffffffffff", model=DUMMY_MODEL)
    d.raw_command("dummy", {})

    assert d.model == DUMMY_MODEL
    info.assert_not_called()
