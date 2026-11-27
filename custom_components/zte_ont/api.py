"""Minimal client for the web UI of ZTE F6005 (V6) GPON ONTs.

The ONT keeps a single, IP-based session (no cookies): every read logs in,
fetches the pages it needs and logs out again, so the web UI stays free.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import secrets
import string
from dataclasses import dataclass

import aiohttp

SCHEME = "https"
DEFAULT_HOST_HEADER = "192.168.1.1"
TIMEOUT = aiohttp.ClientTimeout(total=20)

# GPON ONU states as defined by ITU-T G.984.3 (O1..O7)
GPON_STATES = {
    1: "initial",
    2: "standby",
    3: "serial_number",
    4: "ranging",
    5: "operation",
    6: "popup",
    7: "emergency_stop",
}

_VAR_RE = re.compile(r'^\s*(?:var\s+)?(\w+)\s*=\s*"([^"]*)"\s*;', re.MULTILINE)
_NONCE_CHARS = string.ascii_letters + string.digits


class OntError(Exception):
    """Communication error."""


class OntAuthError(OntError):
    """Login rejected."""


class OntBusyError(OntError):
    """Another user is logged in to the web UI."""


@dataclass(slots=True)
class DeviceInfo:
    model: str
    hardware: str
    software: str
    bootloader: str
    serial: str


@dataclass(slots=True)
class OpticalData:
    state: int
    rx_power: float | None  # dBm, None = no optical input
    tx_power: float | None  # dBm, None = laser off
    voltage: float  # V
    bias_current: float  # mA
    temperature: float  # °C

    @property
    def state_name(self) -> str | None:
        return GPON_STATES.get(self.state)

    @property
    def los(self) -> bool:
        """Loss of signal: no light from the OLT."""
        return self.rx_power is None


@dataclass(slots=True)
class OntData:
    device: DeviceInfo
    optical: OpticalData


def _vars(html: str) -> dict[str, str]:
    return dict(_VAR_RE.findall(html))


def parse_devinfo(html: str) -> DeviceInfo:
    v = _vars(html)
    if v.get("pagename") != "devinfo":
        raise OntError("Unexpected devinfo page (session lost?)")
    return DeviceInfo(
        model=v.get("Model", ""),
        hardware=v.get("HardwareVer", ""),
        software=v.get("SoftwareVer", ""),
        bootloader=v.get("BootLoaderVer", ""),
        serial=v.get("PonSerialNum", ""),
    )


def parse_gponinfo(html: str) -> OpticalData:
    """Decode the raw values with the same formulas as the ONT's own page."""
    v = _vars(html)
    if v.get("pagename") != "gponinfo":
        raise OntError("Unexpected gponinfo page (session lost?)")
    try:
        state = int(v["ponStaIndex"])
        tx_raw = int(v["txpower"])
        rx_raw = int(v["rxpower"])
        voltage = int(v["voltage"]) / 50
        current = int(v["current"]) / 1000
        temperature = int(v["temperature"]) / 256
    except (KeyError, ValueError) as err:
        raise OntError(f"Cannot parse optical values: {err}") from err

    tx = round(tx_raw / 500 - 30, 2)
    rx = round(rx_raw / 500 - 40, 2)
    rx_power: float | None = rx
    if state == 1 and (rx < -38 or rx > -8):
        rx_power = None
    return OpticalData(
        state=state,
        rx_power=rx_power,
        tx_power=None if tx == -1 else tx,
        voltage=round(voltage, 2),
        bias_current=round(current, 2),
        temperature=round(temperature, 1),
    )


class ZteOnt:
    """Reads device and optical info from the ONT."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        username: str,
        password: str,
        host_header: str = DEFAULT_HOST_HEADER,
    ) -> None:
        self._session = session
        self.host = host
        self.port = port
        self._username = username
        self._password = password
        self._host_header = host_header or DEFAULT_HOST_HEADER
        self._lock = asyncio.Lock()
        self._device: DeviceInfo | None = None

    def _url(self, path: str) -> str:
        return f"{SCHEME}://{self.host}:{self.port}/{path}"

    async def _request(self, path: str, referer: str, data: str | None = None) -> str:
        headers = {
            # The ONT rejects any Host other than its own address
            "Host": self._host_header,
            "Referer": f"{SCHEME}://{self._host_header}/{referer}",
        }
        try:
            if data is None:
                resp = await self._session.get(
                    self._url(path), headers=headers, ssl=False,
                    allow_redirects=False, timeout=TIMEOUT,
                )
            else:
                headers["Origin"] = f"{SCHEME}://{self._host_header}"
                headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
                resp = await self._session.post(
                    self._url(path), headers=headers, data=data, ssl=False,
                    allow_redirects=False, timeout=TIMEOUT,
                )
            async with resp:
                return await resp.text(errors="replace")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise OntError(f"Cannot reach the ONT at {self.host}:{self.port}: {err}") from err

    async def _login(self) -> None:
        page = await self._request("login.html", "login.html")
        if "Bad Request" in page and "Access Error" in page:
            raise OntError("The ONT rejected the request (check the Host header option)")
        busy = re.search(r"XHasLogin\s*=\s*'1'", page) is not None
        cmt = hashlib.sha256(f"{self._username}97s{self._password}".encode()).hexdigest()
        nonce = "".join(secrets.choice(_NONCE_CHARS) for _ in range(32))
        reply = await self._request("goform/LoginForm", "login.html", f"cmt={cmt}&nonce={nonce}")
        if "loginStatus = ok" not in reply:
            if busy:
                raise OntBusyError("Someone else is logged in to the ONT web UI")
            raise OntAuthError("Login rejected by the ONT")

    async def _logout(self) -> None:
        try:
            await self._request("goform/LogoutForm", "gponinfo.html", "")
        except OntError:
            pass

    async def fetch(self) -> OntData:
        async with self._lock:
            await self._login()
            try:
                # Same navigation as a browser: devinfo first, then gponinfo
                self._device = parse_devinfo(await self._request("devinfo.html", "login.html"))
                optical = parse_gponinfo(await self._request("gponinfo.html", "devinfo.html"))
            finally:
                await self._logout()
            return OntData(device=self._device, optical=optical)
