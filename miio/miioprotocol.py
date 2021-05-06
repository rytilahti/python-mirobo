"""miIO protocol implementation.

This module contains the implementation of routines to send handshakes, send commands
and discover devices (MiIOProtocol).
"""
import binascii
import codecs
import datetime
import logging
import socket
from typing import Any, Dict, List

import construct

from .exceptions import DeviceError, DeviceException, RecoverableError
from .protocol import Message

_LOGGER = logging.getLogger(__name__)


class MiIOProtocol:
    def __init__(
        self,
        ip: str = None,
        token: str = None,
        start_id: int = 0,
        debug: int = 0,
        lazy_discover: bool = True,
        timeout: int = 5,
    ) -> None:
        """Create a :class:`Device` instance.

        :param ip: IP address or a hostname for the device
        :param token: Token used for encryption
        :param start_id: Running message id sent to the device
        :param debug: Wanted debug level
        """
        self.ip = ip
        self.port = 54321
        if token is None:
            token = 32 * "0"
        if token is not None:
            self.token = bytes.fromhex(token)
        self.debug = debug
        self.lazy_discover = lazy_discover

        self._timeout = timeout
        self._discovered = False
        self._device_ts = None  # type: datetime.datetime
        self.__id = start_id
        self._device_id = None

    def send_handshake(self, *, retry_count=3) -> Message:
        """Send a handshake to the device.

        This returns some information, such as device type and serial,
        as well as device's timestamp in response.

        The handshake must also be done regularly to enable communication
        with the device.

        :raises DeviceException: if the device could not be discovered after retries.
        """
        try:
            m = MiIOProtocol.discover(self.ip, is_broadcast=False)
        except DeviceException as ex:
            if retry_count > 0:
                return self.send_handshake(retry_count=retry_count - 1)

            raise ex

        if m is None:
            _LOGGER.debug("Unable to discover a device at address %s", self.ip)
            raise DeviceException("Unable to discover the device %s" % self.ip)

        header = m.header.value
        self._device_id = header.device_id
        self._device_ts = header.ts
        self._discovered = True

        if self.debug > 1:
            _LOGGER.debug(m)
        _LOGGER.debug(
            "Discovered %s with ts: %s, token: %s",
            binascii.hexlify(self._device_id).decode(),
            self._device_ts,
            codecs.encode(m.checksum, "hex"),
        )

        return m

    @staticmethod
    def discover(addr: str = None, is_broadcast: bool = True, timeout: int = 5) -> Any:
        """Scan for devices in the network. This method is used to discover supported
        devices by sending a handshake message to the broadcast address on port 54321.
        If the target IP address is given and is_broadcast is False, the handshake 
        will be send as a unicast packet. 
        If is_broadcast is True, then addr can optionally specify the target network
        to send the broadcast to. This is necessary for Windows platforms.

        :param str addr: Target IP address or network
        :param bool is_broadcast: True to broadcast, False to unicast
        :param int timeout: Time to wait for discovering new devices
        """
        seen_addrs = []  # type: List[str]
        if is_broadcast:
            if not addr:
                addr = "<broadcast>"
            is_broadcast = True
            _LOGGER.info("Sending discovery to %s with timeout of %ss..", addr, timeout)
        # magic, length 32
        helobytes = bytes.fromhex(
            "21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        )

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(timeout)
        for _ in range(3):
            s.sendto(helobytes, (addr, 54321))
        while True:
            try:
                data, addr = s.recvfrom(1024)
                m = Message.parse(data)  # type: Message
                _LOGGER.debug("Got a response: %s", m)
                if not is_broadcast:
                    return m

                if addr[0] not in seen_addrs:
                    _LOGGER.info(
                        "  IP %s (ID: %s) - token: %s",
                        addr[0],
                        binascii.hexlify(m.header.value.device_id).decode(),
                        codecs.encode(m.checksum, "hex"),
                    )
                    seen_addrs.append(addr[0])
            except socket.timeout:
                if is_broadcast:
                    _LOGGER.info("Discovery done")
                return  # ignore timeouts on discover
            except Exception as ex:
                _LOGGER.warning("error while reading discover results: %s", ex)
                break

    def send(
        self,
        command: str,
        parameters: Any = None,
        retry_count: int = 3,
        *,
        extra_parameters: Dict = None
    ) -> Any:
        """Build and send the given command. Note that this will implicitly call
        :func:`send_handshake` to do a handshake, and will re-try in case of errors
        while incrementing the `_id` by 100.

        :param str command: Command to send
        :param dict parameters: Parameters to send, or an empty list
        :param retry_count: How many times to retry in case of failure, how many handshakes to send
        :param dict extra_parameters: Extra top-level parameters
        :raises DeviceException: if an error has occurred during communication.
        """

        if not self.lazy_discover or not self._discovered:
            self.send_handshake()

        request = self._create_request(command, parameters, extra_parameters)

        send_ts = self._device_ts + datetime.timedelta(seconds=1)
        header = {
            "length": 0,
            "unknown": 0x00000000,
            "device_id": self._device_id,
            "ts": send_ts,
        }

        msg = {"data": {"value": request}, "header": {"value": header}, "checksum": 0}
        m = Message.build(msg, token=self.token)
        _LOGGER.debug("%s:%s >>: %s", self.ip, self.port, request)
        if self.debug > 1:
            _LOGGER.debug(
                "send (timeout %s): %s",
                self._timeout,
                Message.parse(m, token=self.token),
            )

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(self._timeout)

        try:
            s.sendto(m, (self.ip, self.port))
        except OSError as ex:
            _LOGGER.error("failed to send msg: %s", ex)
            raise DeviceException from ex

        try:
            data, addr = s.recvfrom(1024)
            m = Message.parse(data, token=self.token)

            header = m.header.value
            payload = m.data.value

            self.__id = payload["id"]
            self._device_ts = header.ts

            if self.debug > 1:
                _LOGGER.debug("recv from %s: %s", addr[0], m)

            _LOGGER.debug(
                "%s:%s (ts: %s, id: %s) << %s",
                self.ip,
                self.port,
                header.ts,
                payload["id"],
                payload,
            )
            if "error" in payload:
                self._handle_error(payload["error"])

            try:
                return payload["result"]
            except KeyError:
                return payload
        except construct.core.ChecksumError as ex:
            raise DeviceException(
                "Got checksum error which indicates use "
                "of an invalid token. "
                "Please check your token!"
            ) from ex
        except OSError as ex:
            if retry_count > 0:
                _LOGGER.debug(
                    "Retrying with incremented id, retries left: %s", retry_count
                )
                self.__id += 100
                self._discovered = False
                return self.send(
                    command,
                    parameters,
                    retry_count - 1,
                    extra_parameters=extra_parameters,
                )

            _LOGGER.error("Got error when receiving: %s", ex)
            raise DeviceException("No response from the device") from ex

        except RecoverableError as ex:
            if retry_count > 0:
                _LOGGER.debug(
                    "Retrying to send failed command, retries left: %s", retry_count
                )
                return self.send(
                    command,
                    parameters,
                    retry_count - 1,
                    extra_parameters=extra_parameters,
                )

            _LOGGER.error("Got error when receiving: %s", ex)
            raise DeviceException("Unable to recover failed command") from ex

    @property
    def _id(self) -> int:
        """Increment and return the sequence id."""
        self.__id += 1
        if self.__id >= 9999:
            self.__id = 1
        return self.__id

    @property
    def raw_id(self):
        return self.__id

    def _handle_error(self, error):
        """Raise exception based on the given error code."""
        if "code" in error and error["code"] == -30001:
            raise RecoverableError(error)
        raise DeviceError(error)

    def _create_request(
        self, command: str, parameters: Any, extra_parameters: Dict = None
    ):
        """Create request payload."""
        request = {"id": self._id, "method": command}

        if parameters is not None:
            request["params"] = parameters
        else:
            request["params"] = []

        if extra_parameters is not None:
            request = {**request, **extra_parameters}

        return request
