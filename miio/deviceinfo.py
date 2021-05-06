from typing import Dict, Optional


class DeviceInfo:
    """Container of miIO device information.

    Hardware properties such as device model, MAC address, memory information, and
    hardware and software information is contained here.
    """

    def __init__(self, data):
        """Response of a Xiaomi Smart WiFi Plug.

        {'ap': {'bssid': 'FF:FF:FF:FF:FF:FF', 'rssi': -68, 'ssid': 'network'},
         'cfg_time': 0,
         'fw_ver': '1.2.4_16',
         'hw_ver': 'MW300',
         'life': 24,
         'mac': '28:FF:FF:FF:FF:FF',
         'mmfree': 30312,
         'model': 'chuangmi.plug.m1',
         'netif': {'gw': '192.168.xxx.x',
                   'localIp': '192.168.xxx.x',
                   'mask': '255.255.255.0'},
         'ot': 'otu',
         'ott_stat': [0, 0, 0, 0],
         'otu_stat': [320, 267, 3, 0, 3, 742],
         'token': '2b00042f7481c7b056c4b410d28f33cf',
         'wifi_fw_ver': 'SD878x-14.76.36.p84-702.1.0-WM'}
        """
        self.data = data

    def __repr__(self):
        return "%s v%s (%s) @ %s - token: %s" % (
            self.model,
            self.firmware_version,
            self.mac_address,
            self.ip_address,
            self.token,
        )

    @property
    def network_interface(self) -> Dict:
        """Information about network configuration.

        If unavailable, returns an empty dictionary.
        """
        return self.data.get("netif", {})

    @property
    def accesspoint(self):
        """Information about connected wlan accesspoint.

        If unavailable, returns an empty dictionary.
        """
        return self.data.get("ap", {})

    @property
    def model(self) -> Optional[str]:
        """Model string if available."""
        return self.data.get("model")

    @property
    def firmware_version(self) -> Optional[str]:
        """Firmware version if available."""
        return self.data.get("fw_ver")

    @property
    def hardware_version(self) -> Optional[str]:
        """Hardware version if available."""
        return self.data.get("hw_ver")

    @property
    def mac_address(self) -> Optional[str]:
        """MAC address if available."""
        return self.data.get("mac")

    @property
    def ip_address(self) -> Optional[str]:
        return self.network_interface.get("localIp")

    @property
    def token(self) -> Optional[str]:
        return self.data.get("token")

    @property
    def raw(self):
        """Raw data as returned by the device."""
        return self.data
