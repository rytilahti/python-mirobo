python-miio
===========

|Chat| |PyPI version| |PyPI downloads| |Build Status| |Coverage Status| |Docs| |Black|

This library (and its accompanying cli tool) can be used to interface with devices using Xiaomi's `miIO <https://github.com/OpenMiHome/mihome-binary-protocol/blob/master/doc/PROTOCOL.md>`__ and MIoT protocols.


Getting started
---------------

If you already have a token for your device and the device type, you can directly start using `miiocli` tool.
If you don't have a token for your device, refer to `Getting started <https://python-miio.readthedocs.io/en/latest/discovery.html>`__ section of `the manual <https://python-miio.readthedocs.io>`__ for instructions how to obtain it.

The `miiocli` is the main way to execute commands from command line.
You can always use `--help` to get more information about the available commands.
For example, executing it without any extra arguments will print out options and available commands::

    $ miiocli --help
    Usage: miiocli [OPTIONS] COMMAND [ARGS]...

    Options:
      -d, --debug
      -o, --output [default|json|json_pretty]
      --help                          Show this message and exit.

    Commands:
      airconditioningcompanion
      ..

You can get some information from any miIO/MIoT device, including its device model, using the `info` command::

    miiocli device --ip <ip> --token <token> info

    Model: some.device.model1
    Hardware version: esp8285
    Firmware version: 1.0.1_0012
    Network: {'localIp': '<ip>', 'mask': '255.255.255.0', 'gw': '<ip>'}
    AP: {'rssi': -73, 'ssid': '<nnetwork>', 'primary': 11, 'bssid': '<bssid>'}

Each different device type is supported by their corresponding module (e.g., `vacuum` or `fan`).
You can get the list of available commands for any given module by passing `--help` argument to it::

    $ miiocli vacuum --help

    Usage: miiocli vacuum [OPTIONS] COMMAND [ARGS]...

    Options:
      --ip TEXT       [required]
      --token TEXT    [required]
      --id-file FILE
      --help          Show this message and exit.

    Commands:
      add_timer                Add a timer.
      ..

API usage
---------
All functionality is accessible through the `miio` module::

    from miio import Vacuum

    vac = Vacuum("<ip address>", "<token>")
    vac.start()

Each separate device type inherits from `miio.Device`
(and in case of MIoT devices, `miio.MiotDevice`) which provides common API.

Please refer to `API documentation <https://python-miio.readthedocs.io/en/latest/api/miio.html>`__ for more information.


Troubleshooting
---------------
You can find some solutions for the most common problems can be found in `Troubleshooting <https://python-miio.readthedocs.io/en/latest/troubleshooting.html>`__ section.

If you have any questions, or simply want to join up for a chat, check `our Matrix room <https://matrix.to/#/#python-miio-chat:matrix.org>`__.

Contributing
------------

We welcome all sorts of contributions from patches to add improvements or fixing bugs to improving the documentation.
To ease the process of setting up a development environment we have prepared `a short guide <https://python-miio.readthedocs.io/en/latest/new_devices.html>`__ for getting you started.


Supported devices
-----------------

-  Xiaomi Mi Robot Vacuum V1, S5, M1S, S7
-  Xiaomi Mi Home Air Conditioner Companion
-  Xiaomi Mi Smart Air Conditioner A (xiaomi.aircondition.mc1, mc2, mc4, mc5)
-  Xiaomi Mi Air Purifier 2, 3H, 3C, Pro (zhimi.airpurifier.m2, mb3, mb4, v7)
-  Xiaomi Mi Air (Purifier) Dog X3, X5, X7SM (airdog.airpurifier.x3, airdog.airpurifier.x5, airdog.airpurifier.x7sm)
-  Xiaomi Mi Air Humidifier
-  Xiaomi Aqara Camera
-  Xiaomi Aqara Gateway (basic implementation, alarm, lights)
-  Xiaomi Mijia 360 1080p
-  Xiaomi Mijia STYJ02YM (Viomi)
-  Xiaomi Mijia 1C STYTJ01ZHM (Dreame)
-  Xiaomi Mi Smart WiFi Socket
-  Xiaomi Chuangmi Plug V1 (1 Socket, 1 USB Port)
-  Xiaomi Chuangmi Plug V3 (1 Socket, 2 USB Ports)
-  Xiaomi Smart Power Strip V1 and V2 (WiFi, 6 Ports)
-  Xiaomi Philips Eyecare Smart Lamp 2
-  Xiaomi Philips RW Read (philips.light.rwread)
-  Xiaomi Philips LED Ceiling Lamp
-  Xiaomi Philips LED Ball Lamp (philips.light.bulb)
-  Xiaomi Philips LED Ball Lamp White (philips.light.hbulb)
-  Xiaomi Philips Zhirui Smart LED Bulb E14 Candle Lamp
-  Xiaomi Philips Zhirui Bedroom Smart Lamp
-  Huayi Huizuo Lamps
-  Xiaomi Universal IR Remote Controller (Chuangmi IR)
-  Xiaomi Mi Smart Pedestal Fan V2, V3, SA1, ZA1, ZA3, ZA4, 1C, P5, P8, P9, P10, P11
-  Xiaomi Rosou SS4 Ventilator (leshow.fan.ss4)
-  Xiaomi Mi Air Humidifier V1, CA1, CA4, CB1, MJJSQ, JSQ, JSQ1, JSQ001
-  Xiaomi Mi Water Purifier (Basic support: Turn on & off)
-  Xiaomi Mi Water Purifier D1, C1 (Triple Setting)
-  Xiaomi PM2.5 Air Quality Monitor V1, B1, S1
-  Xiaomi Smart WiFi Speaker
-  Xiaomi Mi WiFi Repeater 2
-  Xiaomi Mi Smart Rice Cooker
-  Xiaomi Smartmi Fresh Air System VA2 (zhimi.airfresh.va2), VA4 (zhimi.airfresh.va4),
   A1 (dmaker.airfresh.a1), T2017 (dmaker.airfresh.t2017)
-  Yeelight lights (basic support, we recommend using `python-yeelight <https://gitlab.com/stavros/python-yeelight/>`__)
-  Xiaomi Mi Air Dehumidifier
-  Xiaomi Tinymu Smart Toilet Cover
-  Xiaomi 16 Relays Module
-  Xiaomi Xiao AI Smart Alarm Clock
-  Smartmi Radiant Heater Smart Version (ZA1 version)
-  Xiaomi Mi Smart Space Heater
-  Xiaomiyoupin Curtain Controller (Wi-Fi) (lumi.curtain.hagl05)
-  Xiaomi Xiaomi Mi Smart Space Heater S (zhimi.heater.mc2)
-  Yeelight Dual Control Module (yeelink.switch.sw1)
-  Scishare coffee maker (scishare.coffee.s1102)
-  Qingping Air Monitor Lite (cgllc.airm.cgdn1)
-  Xiaomi Walkingpad A1 (ksmb.walkingpad.v3)


*Feel free to create a pull request to add support for new devices as
well as additional features for supported devices.*

Projects using this library
---------------------------

This library is used by various projects to support MiIO/MiOT devices.
If you are using this library for your project, feel free to open a PR to get it listed here!

Home Assistant (official)
^^^^^^^^^^^^^^^^^^^^^^^^^

Home Assistant uses this library to support several platforms out-of-the-box.
This list is incomplete as the platforms (in parentheses) may also support other devices listed above.

-  `Xiaomi Mi Robot Vacuum <https://home-assistant.io/components/vacuum.xiaomi_miio/>`__ (vacuum)
-  `Xiaomi Philips Light <https://home-assistant.io/components/light.xiaomi_miio/>`__ (light)
-  `Xiaomi Mi Air Purifier and Air Humidifier <https://home-assistant.io/components/fan.xiaomi_miio/>`__ (fan)
-  `Xiaomi Smart WiFi Socket and Smart Power Strip <https://home-assistant.io/components/switch.xiaomi_miio/>`__ (switch)
-  `Xiaomi Universal IR Remote Controller <https://home-assistant.io/components/remote.xiaomi_miio/>`__ (remote)
-  `Xiaomi Mi Air Quality Monitor (PM2.5) <https://home-assistant.io/components/sensor.xiaomi_miio/>`__ (sensor)
-  `Xiaomi Aqara Gateway Alarm <https://home-assistant.io/components/alarm_control_panel.xiaomi_miio/>`__ (alarm_control_panel)
-  `Xiaomi Mi WiFi Repeater 2 <https://www.home-assistant.io/components/device_tracker.xiaomi_miio/>`__ (device_tracker)

Home Assistant (custom)
^^^^^^^^^^^^^^^^^^^^^^^

-  `Xiaomi Mi Home Air Conditioner Companion <https://github.com/syssi/xiaomi_airconditioningcompanion>`__
-  `Xiaomi Mi Smart Pedestal Fan <https://github.com/syssi/xiaomi_fan>`__
-  `Xiaomi Mi Smart Rice Cooker <https://github.com/syssi/xiaomi_cooker>`__
-  `Xiaomi Raw Sensor <https://github.com/syssi/xiaomi_raw>`__
-  `Xiaomi MIoT Devices <https://github.com/ha0y/xiaomi_miot_raw>`__

Other projects
^^^^^^^^^^^^^^

-  `Your project here? Feel free to open a PR! <https://github.com/rytilahti/python-miio/pulls>`__

.. |Chat| image:: https://img.shields.io/matrix/python-miio-chat:matrix.org
   :target: https://matrix.to/#/#python-miio-chat:matrix.org
.. |PyPI version| image:: https://badge.fury.io/py/python-miio.svg
   :target: https://badge.fury.io/py/python-miio
.. |PyPI downloads| image:: https://img.shields.io/pypi/dw/python-miio
   :target: https://pypi.org/project/python-miio/
.. |Build Status| image:: https://img.shields.io/azure-devops/build/python-miio/608e6099-f1ed-403c-9158-8fdcb2a0e477/1
   :target: https://dev.azure.com/python-miio/python-miio/
.. |Coverage Status| image:: https://coveralls.io/repos/github/rytilahti/python-miio/badge.svg?branch=master
   :target: https://coveralls.io/github/rytilahti/python-miio?branch=master
.. |Docs| image:: https://readthedocs.org/projects/python-miio/badge/?version=latest
   :alt: Documentation status
   :target: https://python-miio.readthedocs.io/en/latest/?badge=latest
.. |Black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
