# ios-hardware-toolkit

Extract comprehensive hardware information from iOS devices over USB. No jailbreak required.

## What it does

- **`hardware_sn.py`** — Dump all hardware serial numbers, chipset IDs, display info (manufacturer, TrueTone, nits), battery health, camera calibration status, CPU/GPU specs, device color, and 25+ component sections from a connected iPhone/iPad.
- **`sensor_test.py`** — Test Face ID (TrueDepth dot projector) and Proximity Sensor by monitoring syslog signals in real time.
- **`ios_hardware_monitor.py`** — Stream and filter iOS syslog by hardware category (thermal, battery, memory, WiFi, etc.) with auto-classification.

## Requirements

- Python 3.12+
- macOS (or Linux with usbmuxd)
- iOS device connected via USB cable
- Device must be **trusted** ("Trust This Computer")
- iOS 16+ requires **Developer Mode** enabled on device

## Setup

```bash
# Clone and install
git clone https://github.com/cnguyen14/ios-hardware-toolkit.git
cd ios-hardware-toolkit
uv sync
```

## Usage

### Hardware Export

```bash
# Print formatted table to console
uv run python hardware_sn.py

# Output as JSON
uv run python hardware_sn.py -j

# Save to file
uv run python hardware_sn.py -o report.json

# Include raw IORegistry product dump (113+ keys)
uv run python hardware_sn.py --raw

# Specific device by UDID
uv run python hardware_sn.py -u DEVICE_UDID
```

Example output:

```
COMPONENT                    KEY                      VALUE
==============================================================================
DEVICE                     product_name             iPhone 17 Pro Max
                           serial_number            XXXXXXXXXXXX
                           color                    Silver
                           image_url                https://statici.icloud.com/...
------------------------------------------------------------------------------
SOC                        chip_id                  33104
                           soc_generation           H18
------------------------------------------------------------------------------
CPU                        total_cores              6
                           e_cores                  4
                           p_cores                  2
------------------------------------------------------------------------------
BATTERY                    serial_number            XXXXXXXXXXXX
                           design_capacity_mah      5030
                           cycle_count              175
------------------------------------------------------------------------------
DISPLAY                    panel_manufacturer       LG Display (Poor)
                           max_nits                 3000
                           truetone_calibrated      True
...
```

**25 sections** extracted: Device, MLB, SoC, CPU, GPU, Chipsets, Battery, Cameras, Storage, Display (with TrueTone & backlight), ALS, Compass, Flash, Touch, Baseband, WiFi, Bluetooth, UWB, Audio, USB-C, Secure Enclave, Buttons, Capabilities, Physical Layout, Software Info.

### Sensor Test

```bash
# Test both sensors
uv run python sensor_test.py

# Test only proximity sensor
uv run python sensor_test.py proximity

# Test only Face ID
uv run python sensor_test.py faceid
```

### Syslog Monitor

```bash
# Stream hardware-related syslog entries
uv run python ios_hardware_monitor.py syslog

# Stream ALL syslog (unfiltered)
uv run python ios_hardware_monitor.py syslog --all

# Filter by category
uv run python ios_hardware_monitor.py syslog --categories thermal,battery

# Save to JSON
uv run python ios_hardware_monitor.py syslog --json output.json

# Show device info + battery details
uv run python ios_hardware_monitor.py info
```

## Display Panel Manufacturer Detection

The tool identifies display manufacturers from the `raw-panel-serial-number` prefix:

| Prefix | Manufacturer | Grade |
|--------|-------------|-------|
| `G9N` | Samsung | Good |
| `G9P` | Samsung | Poor |
| `G9Q` | Samsung | Mid |
| `GVC` | LG Display | Good |
| `GH3` | LG Display | Poor |
| `F5V` | BOE | — |

Manufacturing date is also decoded (year + ISO week).

## Device Color Resolution

Numeric `DeviceEnclosureColor` IDs are automatically resolved to marketing color names (e.g., "Natural Titanium", "Ultramarine", "Cosmic Orange") for all iPhones from iPhone 7 through iPhone 17 Pro Max and iPhone Air.

## Documentation

- [`HARDWARE_SN_GUIDE.md`](HARDWARE_SN_GUIDE.md) — Technical deep-dive: IORegistry map, all 30 accessible entries, key descriptions, data decoding, and limitations.
- [`iphone_enclosure_color_mapping.md`](iphone_enclosure_color_mapping.md) — Complete DeviceEnclosureColor → color name mapping for all iPhone models.

## How it works

```
┌──────────────┐     USB/usbmuxd      ┌───────────────────────┐
│  Host (Mac)  │ ◄──────────────────►  │    iOS Device          │
│              │                       │                        │
│  pymobile-   │   LockdownProtocol    │  lockdownd             │
│  device3     │ ◄──────────────────►  │    ├─► DiagnosticsRelay│
│              │                       │    │     └─► IORegistry │
│              │   OsTraceService      │    └─► syslogd         │
│              │ ◄──────────────────►  │                        │
└──────────────┘                       └───────────────────────┘
```

All data is read via Apple's own diagnostic services — no modification to the device, no jailbreak, no private APIs on device.

## License

MIT
