# AP Systems EasyPower — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)](https://www.home-assistant.io/)

A Home Assistant custom integration for **APsystems EZ1** (and compatible) micro-inverters via the **AP Systems cloud API** — the same API used by the official *AP EasyPower* mobile app.

> **No local network access required.** This integration communicates with the AP Systems cloud, so it works even if your inverter is behind a different router or network segment.

---

## Features

- Current AC power output (total + per channel)
- Energy production: today / this month / lifetime
- Last reported power (from statistic endpoint)
- Automatic token refresh — no manual re-authentication needed
- Full HACS support

## Supported Hardware

| Device | Channels | Tested |
|--------|----------|--------|
| EZ1-M-EU (600 W) | 2 | ✅ |
| EZ1-M (600 W) | 2 | likely |
| Other EZ1 variants | 2 | likely |

Other APsystems EZ-series inverters that use the same app should work as well. Please open an issue if your device is not listed.

---

## Installation

### Via HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add URL: `https://github.com/Meyblaubaer/apsystems-easypower-ha` — Category: **Integration**
3. Search for *AP Systems EasyPower* and install
4. Restart Home Assistant

### Manual

1. Copy `custom_components/apsystems_easypower/` into your HA `config/custom_components/` folder
2. Restart Home Assistant

---

## Configuration

1. Go to **Settings → Devices & Services → + Add Integration**
2. Search for *AP Systems EasyPower*
3. Enter your credentials:
   - **Username** — your APsystems account name (*Kontoname*, **not** your email address)
   - **Password** — your AP EasyPower app password

> **Note:** The username is the *Kontoname* shown in the AP EasyPower app, not your email address.

---

## Sensors

For each inverter the following sensors are created:

| Sensor | Unit | Description |
|--------|------|-------------|
| Current Power | W | Real-time AC output power |
| Power Channel 1 | W | Channel 1 real-time power |
| Power Channel 2 | W | Channel 2 real-time power |
| Energy Today | kWh | Energy produced today |
| Energy This Month | kWh | Energy produced this month |
| Energy Lifetime | kWh | Total lifetime energy production |
| Last Reported Power | W | Last power value from statistics |

---

## How It Works

The integration uses the same encrypted API as the official AP EasyPower Android app:

1. **Authentication** — credentials are RSA + AES encrypted (matching the APK encryption scheme) and sent to the AP Systems cloud login endpoint
2. **Data polling** — inverter data is fetched from the v2 REST API using a Bearer token, every 5 minutes
3. **Token refresh** — expired tokens are automatically detected and refreshed without user interaction

---

## Troubleshooting

**"Invalid username or password"** — Make sure you are using your *Kontoname* (account name), not your email address.

**Sensors show "Unavailable"** — The inverter may be offline (e.g., at night when there is no solar production). This is normal.

**"Could not connect"** — Check your internet connection. The AP Systems cloud API must be reachable.

Enable debug logging for more details:
```yaml
logger:
  default: warning
  logs:
    custom_components.apsystems_easypower: debug
```

---

## Contributing

Pull requests are welcome! Please open an issue first to discuss changes.

## License

MIT — see [LICENSE](LICENSE)
