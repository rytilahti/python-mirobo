from typing import Tuple, List

import base64
import re

import click
from construct import (
    Struct, Const, Rebuild, this, len_, Adapter, Computed,
    Int16ul, Int32ul, Int16ub, Array, BitStruct, BitsInteger,
)
try:
    import heatshrink
except:
    heatshrink = None

from .click_common import command, format_output
from .device import Device, DeviceException


class ChuangmiIrException(DeviceException):
    pass


class ChuangmiIr(Device):
    """Main class representing Chuangmi IR Remote Controller."""

    PRONTO_RE = re.compile(r'^([\da-f]{4}\s?){3,}([\da-f]{4})$', re.IGNORECASE)

    @command(
        click.argument("key", type=int),
        default_output=format_output("Learning command into storage key {key}")
    )
    def learn(self, key: int=1):
        """Learn an infrared command.

        :param int key: Storage slot, must be between 1 and 1000000"""

        if key < 1 or key > 1000000:
            raise ChuangmiIrException("Invalid storage slot.")
        return self.send("miIO.ir_learn", {'key': str(key)})

    @command(
        click.argument("key", type=int),
        default_output=format_output("Reading infrared command from storage key {key}")
    )
    def read(self, key: int=1):
        """Read a learned command.

        Positive response (chuangmi.ir.v2):
        {'key': '1', 'code': 'Z6WPAasBAAA3BQAA4AwJAEA....AAABAAEBAQAAAQAA=='}

        Negative response (chuangmi.ir.v2):
        {'error': {'code': -5002, 'message': 'no code for this key'}, 'id': 5}

        Negative response (chuangmi.ir.v2):
        {'error': {'code': -5003, 'message': 'learn timeout'}, 'id': 17}

        :param int key: Slot to read from"""

        if key < 1 or key > 1000000:
            raise ChuangmiIrException("Invalid storage slot.")
        return self.send("miIO.ir_read", {'key': str(key)})

    def play_raw(self, command: str, frequency: int=38400):
        """Play a captured command.

        :param str command: Command to execute
        :param int frequency: Execution frequency"""
        return self.send("miIO.ir_play",
                         {'freq': frequency, 'code': command})

    def play_pronto(self, pronto: str, repeats: int=1):
        """Play a Pronto Hex encoded IR command.
        Supports only raw Pronto format, starting with 0000.

        :param str pronto: Pronto Hex string.
        :param int repeats: Number of extra signal repeats."""
        return self.play_raw(*self.pronto_to_raw(pronto, repeats))

    @classmethod
    def _parse_pronto(cls, pronto: str) -> Tuple[List['ProntoBurstPair'],
                                                 List['ProntoBurstPair'],
                                                 int]:
        """Parses Pronto Hex encoded IR command and returns a tuple containing
        a list of intro pairs, a list of repeat pairs and a signal carrier frequency"""
        try:
            pronto_data = Pronto.parse(bytearray.fromhex(pronto))
        except Exception as ex:
            raise ChuangmiIrException("Invalid Pronto command") from ex

        return pronto_data.intro, pronto_data.repeat, int(round(pronto_data.frequency))

    @classmethod
    def pronto_to_raw(cls, pronto: str, repeats: int = 1) -> Tuple[str, int]:
        """Takes a Pronto Hex encoded IR command and number of repeats
        and returns a tuple containing a string encoded IR signal accepted by
        controller and frequency.
        Supports only raw Pronto format, starting with 0000.

        :param str pronto: Pronto Hex string.
        :param int repeats: Number of extra signal repeats."""

        if repeats < 0:
            raise ChuangmiIrException('Invalid repeats value')

        intro_pairs, repeat_pairs, frequency = cls._parse_pronto(pronto)

        if len(intro_pairs) == 0:
            repeats += 1

        times = set()
        for pair in intro_pairs + repeat_pairs * (1 if repeats else 0):
            times.add(pair.pulse)
            times.add(pair.gap)

        times = sorted(times)
        times_map = {t: idx for idx, t in enumerate(times)}
        edge_pairs = []
        for pair in intro_pairs + repeat_pairs * repeats:
            edge_pairs.append({
                'pulse': times_map[pair.pulse],
                'gap': times_map[pair.gap],
            })

        signal_code = base64.b64encode(ChuangmiIrSignal.build({
            'times_index': times + [0] * (16 - len(times)),
            'edge_pairs': edge_pairs,
        })).decode()

        return signal_code, frequency

    @command(
        click.argument("command", type=str),
        default_output=format_output("Playing the supplied command")
    )
    def play(self, command: str):
        """Plays a command in one of the supported formats."""
        if ":" not in command:
            if self.PRONTO_RE.match(command):
                command_type = 'pronto'
            else:
                command_type = 'raw'
            command_args = []
        else:
            command_type, command, *command_args = command.split(":")

        if command_type == "raw":
            play_method = self.play_raw
            arg_types = [int]
        elif command_type == "pronto":
            play_method = self.play_pronto
            arg_types = [int]
        else:
            raise ChuangmiIrException("Invalid command type")

        if len(command_args) > len(arg_types):
            raise ChuangmiIrException("Invalid command arguments count")

        try:
            command_args = [t(v) for v, t in zip(command_args, arg_types)]
        except Exception as ex:
            raise ChuangmiIrException('Invalid command arguments') from ex

        return play_method(command, *command_args)


class ChuangmiRemote(ChuangmiIr):
    """Class representing new type of Chuangmi IR Remote Controller
    called Chuangmi Remote. The new controller uses different format for
    learned IR commands, which actually is the old format but with additional
    layer of compression.
    """

    @classmethod
    def pronto_to_raw(cls, pronto: str, repeats: int = 1) -> Tuple[str, int]:
        """Takes a Pronto Hex encoded IR command and number of repeats
        and returns a tuple containing a string encoded IR signal accepted by
        controller and frequency.
        Supports only raw Pronto format, starting with 0000.

        :raises ChuangmiIrException if heatshrink package is not installed

        :param str pronto: Pronto Hex string.
        :param int repeats: Number of extra signal repeats."""
        if heatshrink is None:
            raise ChuangmiIrException("Heatshrink library is missing")
        raw, frequency = super().pronto_to_raw(pronto, repeats)
        return base64.b64encode(
            heatshrink.encode('learn{}'.format(raw).encode())
        ).decode(), frequency


class ProntoPulseAdapter(Adapter):
    def _decode(self, obj, context, path):
        return int(obj * context._.modulation_period)

    def _encode(self, obj, context, path):
        raise RuntimeError('Not implemented')


ChuangmiIrSignal = Struct(
    Const(0xa567, Int16ul),
    'edge_count' / Rebuild(Int16ul, len_(this.edge_pairs) * 2 - 1),
    'times_index' / Array(16, Int32ul),
    'edge_pairs' / Array((this.edge_count + 1) // 2, BitStruct(
        'gap' / BitsInteger(4),
        'pulse' / BitsInteger(4),
    ))
)

ProntoBurstPair = Struct(
    'pulse' / ProntoPulseAdapter(Int16ub),
    'gap' / ProntoPulseAdapter(Int16ub),
)

Pronto = Struct(
    Const(0, Int16ub),
    '_ticks' / Int16ub,
    'modulation_period' / Computed(this._ticks * 0.241246),
    'frequency' / Computed(1000000 / this.modulation_period),
    'intro_len' / Int16ub,
    'repeat_len' / Int16ub,
    'intro' / Array(this.intro_len, ProntoBurstPair),
    'repeat' / Array(this.repeat_len, ProntoBurstPair),
)
