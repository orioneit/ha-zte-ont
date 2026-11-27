"""End-to-end tests against a fake ONT."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zte_ont.api import parse_gponinfo
from custom_components.zte_ont.const import CONF_HOST_HEADER, DOMAIN

from .fake_ont import GPONINFO


def _data(ont, password="admin", host_header="192.168.1.1"):
    return {CONF_HOST: "127.0.0.1", CONF_PORT: ont.port, CONF_USERNAME: "admin",
            CONF_PASSWORD: password, CONF_HOST_HEADER: host_header}


async def _setup(hass: HomeAssistant, ont) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="ONT Casa", unique_id="ZTEG00000001", data=_data(ont))
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def test_parse_real_values() -> None:
    # Values read from a real F6005 V6.0 (V6.0.10P2N19)
    d = parse_gponinfo(GPONINFO.format(state=5, tx=16097, rx=13354))
    assert d.state_name == "operation"
    assert d.rx_power == -13.29
    assert d.tx_power == 2.19
    assert d.voltage == 3.28
    assert d.bias_current == 20.69
    assert d.temperature == 76.0
    assert not d.los
    # O1 with no light from the OLT
    los = parse_gponinfo(GPONINFO.format(state=1, tx=16097, rx=0))
    assert los.state_name == "initial" and los.rx_power is None and los.los
    # Real reading from an F6005 with a broken fiber: O1, laser off, RX noise
    cut = parse_gponinfo(GPONINFO.format(state=1, tx=14500, rx=2048))
    assert cut.rx_power == -35.9 and cut.tx_power is None and cut.los


async def test_config_flow(hass: HomeAssistant, ont) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    bad = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "ONT", **_data(ont, "wrong")})
    assert bad["errors"] == {"base": "invalid_auth"}
    bad = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "ONT", **_data(ont, host_header="10.0.0.1")})
    assert bad["errors"] == {"base": "cannot_connect"}
    ok = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "ONT Casa", **_data(ont)})
    assert ok["type"] is FlowResultType.CREATE_ENTRY
    assert ok["title"] == "ONT Casa"
    assert ok["result"].unique_id == "ZTEG00000001"
    assert not ont.logged_in  # always logs out


async def test_entities(hass: HomeAssistant, ont) -> None:
    entry = await _setup(hass, ont)
    assert hass.states.get("sensor.ont_casa_gpon_state").state == "operation"
    assert hass.states.get("sensor.ont_casa_rx_power").state == "-13.29"
    assert hass.states.get("sensor.ont_casa_tx_power").state == "2.19"
    assert hass.states.get("sensor.ont_casa_temperature").state == "76.0"
    assert hass.states.get("binary_sensor.ont_casa_gpon_link").state == "on"
    assert hass.states.get("binary_sensor.ont_casa_loss_of_signal").state == "off"
    assert ont.logins == ont.logouts == 1

    # Fiber cut
    ont.state, ont.rx = 1, 0
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.ont_casa_gpon_state").state == "initial"
    assert hass.states.get("sensor.ont_casa_rx_power").state == "unknown"
    assert hass.states.get("binary_sensor.ont_casa_gpon_link").state == "off"
    assert hass.states.get("binary_sensor.ont_casa_loss_of_signal").state == "on"


async def test_busy_web_ui(hass: HomeAssistant, ont) -> None:
    entry = await _setup(hass, ont)
    ont.other_user = True
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.ont_casa_rx_power").state == "unavailable"
    # A busy web UI never triggers re-authentication
    assert not list(entry.async_get_active_flows(hass, {config_entries.SOURCE_REAUTH}))
    ont.other_user = False
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.ont_casa_rx_power").state == "-13.29"
