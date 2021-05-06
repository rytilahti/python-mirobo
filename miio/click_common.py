"""Click commons.

This file contains common functions for cli tools.
"""
import ast
import ipaddress
import json
import logging
import re
import sys
from functools import partial, wraps
from typing import Union

import click

import miio

from .exceptions import DeviceError

if sys.version_info < (3, 5):
    click.echo(
        "To use this script you need python 3.5 or newer, got %s" % (sys.version_info,)
    )
    sys.exit(1)


_LOGGER = logging.getLogger(__name__)


def validate_ip(ctx, param, value):
    if value is None:
        return None
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError as ex:
        raise click.BadParameter("Invalid IP: %s" % ex)


def validate_token(ctx, param, value):
    if value is None:
        return None
    token_len = len(value)
    if token_len != 32:
        raise click.BadParameter("Token length != 32 chars: %s" % token_len)
    return value


class ExceptionHandlerGroup(click.Group):
    """Add a simple group for catching the miio-related exceptions.

    This simplifies catching the exceptions from different click commands.

    Idea from https://stackoverflow.com/a/44347763
    """

    def __call__(self, *args, **kwargs):
        try:
            return self.main(*args, **kwargs)
        except miio.DeviceException as ex:
            _LOGGER.debug("Exception: %s", ex, exc_info=True)
            click.echo(click.style("Error: %s" % ex, fg="red", bold=True))


class EnumType(click.Choice):
    def __init__(self, enumcls, casesensitive=False):
        choices = enumcls.__members__

        if not casesensitive:
            choices = (_.lower() for _ in choices)

        self._enumcls = enumcls
        self._casesensitive = casesensitive

        super().__init__(list(sorted(set(choices))))

    def convert(self, value, param, ctx):
        if not self._casesensitive:
            value = value.lower()

        value = super().convert(value, param, ctx)

        if not self._casesensitive:
            return next(_ for _ in self._enumcls if _.name.lower() == value.lower())
        else:
            return next(_ for _ in self._enumcls if _.name == value)

    def get_metavar(self, param):
        word = self._enumcls.__name__

        # Stolen from jpvanhal/inflection
        word = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", word)
        word = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", word)
        word = word.replace("-", "_").lower().split("_")

        if word[-1] == "enum":
            word.pop()

        return ("_".join(word)).upper()


class LiteralParamType(click.ParamType):
    name = "literal"

    def convert(self, value, param, ctx):
        try:
            return ast.literal_eval(value)
        except ValueError:
            self.fail("%s is not a valid literal" % value, param, ctx)


class GlobalContextObject:
    def __init__(self, debug: int = 0, output: callable = None):
        self.debug = debug
        self.output = output


class DeviceGroupMeta(type):

    device_classes = set()

    def __new__(mcs, name, bases, namespace) -> type:
        commands = {}

        def _get_commands_for_namespace(namespace):
            commands = {}
            for _, val in namespace.items():
                if not callable(val):
                    continue
                device_group_command = getattr(val, "_device_group_command", None)
                if device_group_command is None:
                    continue
                commands[device_group_command.command_name] = device_group_command

            return commands

        # 1. Go through base classes for commands
        for base in bases:
            commands.update(getattr(base, "_device_group_commands", {}))

        # 2. Add commands from the current class
        commands.update(_get_commands_for_namespace(namespace))

        namespace["_device_group_commands"] = commands
        if "get_device_group" not in namespace:

            def get_device_group(dcls):
                return DeviceGroup(dcls)

            namespace["get_device_group"] = classmethod(get_device_group)

        cls = super().__new__(mcs, name, bases, namespace)
        mcs.device_classes.add(cls)
        return cls


class DeviceGroup(click.MultiCommand):
    class Command:
        def __init__(self, name, decorators, *, default_output=None, **kwargs):
            self.name = name
            self.decorators = list(decorators)
            self.decorators.reverse()
            self.default_output = default_output

            self.kwargs = kwargs

        def __call__(self, func):
            self.func = func
            func._device_group_command = self
            self.kwargs.setdefault("help", self.func.__doc__)

            def _autodetect_model_if_needed(func):
                def _wrap(self, *args, **kwargs):
                    skip_autodetect = func._device_group_command.kwargs.pop(
                        "skip_autodetect", False
                    )
                    if (
                        not skip_autodetect
                        and self._model is None
                        and self._info is None
                    ):
                        _LOGGER.debug("Unknown model, trying autodetection.")
                        self.info()
                    return func(self, *args, **kwargs)

                # TODO HACK to make the command visible to cli
                _wrap._device_group_command = func._device_group_command
                return _wrap

            func = _autodetect_model_if_needed(func)

            return func

        @property
        def command_name(self):
            return self.name or self.func.__name__.lower()

        def wrap(self, ctx, func):
            gco = ctx.find_object(GlobalContextObject)
            if gco is not None and gco.output is not None:
                output = gco.output
            elif self.default_output:
                output = self.default_output
            else:
                output = format_output("Running command {0}".format(self.command_name))

            # Remove skip_autodetect before constructing the click.command
            self.kwargs.pop("skip_autodetect", None)

            func = output(func)
            for decorator in self.decorators:
                func = decorator(func)
            return click.command(self.command_name, **self.kwargs)(func)

        def call(self, owner, *args, **kwargs):
            method = getattr(owner, self.func.__name__)
            return method(*args, **kwargs)

    DEFAULT_PARAMS = [
        click.Option(["--ip"], required=True, callback=validate_ip),
        click.Option(["--token"], required=True, callback=validate_token),
        click.Option(["--model"], required=False),
    ]

    def __init__(
        self,
        device_class,
        name=None,
        invoke_without_command=False,
        no_args_is_help=None,
        subcommand_metavar=None,
        chain=False,
        result_callback=None,
        result_callback_pass_device=True,
        **attrs
    ):

        self.commands = getattr(device_class, "_device_group_commands", None)
        if self.commands is None:
            raise RuntimeError(
                "Class {} doesn't use DeviceGroupMeta meta class."
                " It can't be used with DeviceGroup."
            )

        self.device_class = device_class
        self.device_pass = click.make_pass_decorator(device_class)

        attrs.setdefault("params", self.DEFAULT_PARAMS)
        attrs.setdefault("callback", click.pass_context(self.group_callback))
        if result_callback_pass_device and callable(result_callback):
            result_callback = self.device_pass(result_callback)

        super().__init__(
            name or device_class.__name__.lower(),
            invoke_without_command,
            no_args_is_help,
            subcommand_metavar,
            chain,
            result_callback,
            **attrs
        )

    def group_callback(self, ctx, *args, **kwargs):
        gco = ctx.find_object(GlobalContextObject)
        if gco:
            kwargs["debug"] = gco.debug
        ctx.obj = self.device_class(*args, **kwargs)

    def command_callback(self, miio_command, miio_device, *args, **kwargs):
        return miio_command.call(miio_device, *args, **kwargs)

    def get_command(self, ctx, cmd_name):
        if cmd_name not in self.commands:
            ctx.fail("Unknown command (%s)" % cmd_name)

        cmd = self.commands[cmd_name]
        return self.commands[cmd_name].wrap(
            ctx, self.device_pass(partial(self.command_callback, cmd))
        )

    def list_commands(self, ctx):
        return sorted(self.commands.keys())


def command(*decorators, name=None, default_output=None, **kwargs):
    return DeviceGroup.Command(
        name, decorators, default_output=default_output, **kwargs
    )


def format_output(
    msg_fmt: Union[str, callable] = "",
    result_msg_fmt: Union[str, callable] = "{result}",
):
    def decorator(func):
        @wraps(func)
        def wrap(*args, **kwargs):
            if msg_fmt:
                if callable(msg_fmt):
                    msg = msg_fmt(**kwargs)
                else:
                    msg = msg_fmt.format(**kwargs)
                if msg:
                    click.echo(msg.strip())
            kwargs["result"] = func(*args, **kwargs)
            if result_msg_fmt:
                if callable(result_msg_fmt):
                    result_msg = result_msg_fmt(**kwargs)
                else:
                    result_msg = result_msg_fmt.format(**kwargs)
                if result_msg:
                    click.echo(result_msg.strip())

        return wrap

    return decorator


def json_output(pretty=False):
    indent = 2 if pretty else None

    def decorator(func):
        @wraps(func)
        def wrap(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
            except DeviceError as ex:
                click.echo(json.dumps(ex.args[0], indent=indent))
                return

            get_json_data_func = getattr(result, "__json__", None)
            data_variable = getattr(result, "data", None)
            if get_json_data_func is not None:
                result = get_json_data_func()
            elif data_variable is not None:
                result = data_variable
            click.echo(json.dumps(result, indent=indent))

        return wrap

    return decorator
