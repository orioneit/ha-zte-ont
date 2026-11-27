# ZTE GPON ONT (F6005) for Home Assistant

[![hacs](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/orioneit/ha-zte-ont/actions/workflows/validate.yml/badge.svg)](https://github.com/orioneit/ha-zte-ont/actions/workflows/validate.yml)

Unofficial Home Assistant integration that monitors the fiber link of a **ZTE ZXHN F6005**
GPON ONT (the box Open Fiber installs in Italy) through its local web interface.

🇮🇹 [Versione italiana](#italiano)

> [!NOTE]
> Tested on F6005 V6.0, firmware V6.0.10P2N19. Not affiliated with ZTE or Open Fiber.

## Entities

| Entity | Notes |
|---|---|
| GPON state | O1…O7 (O5 = operation) |
| RX power | dBm, *unknown* when there is no light from the OLT |
| TX power | dBm |
| Temperature | °C |
| Voltage, laser bias current | diagnostic |
| GPON link | on in O5 |
| Loss of signal | on when no optical input |

Polled every 5 minutes (configurable, min. 60 s). Each read logs in and out again,
because the ONT allows a single web session.

## Reaching the ONT

The ONT answers on `https://192.168.1.1` on the router's WAN port and has no DHCP,
so Home Assistant needs a route to it. On OpenWrt, add a static interface
(e.g. `192.168.1.2/24`) on the WAN device and put it in the masqueraded WAN zone.

If the ONT is behind another router, forward a port (e.g. `8443` → `192.168.1.1:443`)
and use that router's address and port in the integration: the ONT rejects
requests with a different `Host`, so the integration always sends the address set in
**Host header** (default `192.168.1.1`).

## Installation

**HACS:** *Custom repositories* → `https://github.com/orioneit/ha-zte-ont` (category *Integration*) → install → restart.

**Manual:** copy `custom_components/zte_ont` to `config/custom_components/` and restart.

Then *Settings → Devices & services → Add integration → ZTE GPON ONT*.
Default credentials are on the label of the ONT; we recommend changing them.

MIT license.

---

<a name="italiano"></a>
## 🇮🇹 Italiano

Integrazione non ufficiale che controlla il collegamento in fibra dell'ONT **ZTE ZXHN F6005**
(quello installato da Open Fiber) tramite la sua interfaccia web locale: stato GPON,
potenza RX/TX, temperatura, tensione, corrente del laser, collegamento GPON e perdita di segnale.
Aggiornamento ogni 5 minuti (configurabile); a ogni lettura entra ed esce, perché l'ONT
accetta una sola sessione web.

**Raggiungere l'ONT:** risponde su `https://192.168.1.1` sulla porta WAN del router, senza DHCP.
Su OpenWrt aggiungi un'interfaccia statica (es. `192.168.1.2/24`) sul device WAN, nella zona WAN
con masquerading. Se l'ONT è dietro un altro router, inoltra una porta (es. `8443` → `192.168.1.1:443`)
e usa indirizzo e porta di quel router: l'integrazione invia sempre l'header Host configurato
(predefinito `192.168.1.1`).

**Installazione:** HACS → *Repository personalizzati* → `https://github.com/orioneit/ha-zte-ont`
(categoria *Integrazione*), poi *Impostazioni → Dispositivi e servizi → Aggiungi integrazione*.
