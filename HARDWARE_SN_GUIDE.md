# Extracting Hardware Information from iOS Devices

This document explains how to programmatically extract hardware component serial numbers, chipset details, and runtime hardware state from iDevices using `pymobiledevice3` and the iOS `DiagnosticsService`.

## Prerequisites

- Python 3.12+
- `pymobiledevice3` (v4.20+)
- iOS device connected via USB
- Device must be **trusted** ("Trust This Computer" prompt accepted)
- iOS 16+ requires **Developer Mode** enabled on the device

```bash
pip install pymobiledevice3
# or
uv add pymobiledevice3
```

## Architecture

```
┌──────────────┐     USB/usbmuxd      ┌──────────────────────┐
│  Host (Mac)  │ ◄──────────────────►  │    iOS Device         │
│              │                       │                       │
│  pymobile-   │   LockdownProtocol    │  lockdownd            │
│  device3     │ ◄──────────────────►  │    │                  │
│              │                       │    ├─► DiagnosticsRelay│
│              │   DiagnosticsRelay    │    │     │             │
│              │ ◄──────────────────►  │    │     ├─► IORegistry│
│              │                       │    │     └─► (kernel)  │
└──────────────┘                       └──────────────────────┘
```

1. **usbmuxd** — Apple's USB multiplexing daemon; handles the USB transport layer
2. **lockdownd** — Device-side daemon that authenticates the host and brokers service connections
3. **DiagnosticsRelay** (`com.apple.mobile.diagnostics_relay`) — A lockdown service that provides read access to IORegistry entries, battery data, and device diagnostics

## IORegistry Map — All Accessible Entries

There are **30 accessible IORegistry entries** grouped by query type. Each provides different hardware data.

### Query by Name (IODeviceTree entries)

| Name | Keys | Description |
|------|------|-------------|
| **`product`** | 113 | Factory provisioning record — component SNs, chipsets, capabilities |
| **`arm-io`** | 23 | SoC subsystem — generation, chip revision, die count |
| **`cpus`** | 7 | CPU topology — core count, cluster count, E/P cores |
| **`baseband`** | 36 | Modem — compatible string, IMEISV, thermal report |
| **`sep`** | 26 | Secure Enclave — firmware loaded, boot slot, SIKA support |
| **`als`** | 14 | Ambient Light Sensor — CE model, hotspot position |
| **`backlight`** | 80+ | Display backlight — max nits, EDR, TrueTone, Aurora, AOD |
| **`bluetooth`** | 7 | Bluetooth device tree — MAC address, transport encoding |
| **`buttons`** | 18 | Physical buttons — hold, volume, ringer, remap usages |
| **`fillmore`** | 6 | Bluetooth chip — architecture, MAC address |
| **`centauri`** | 15 | WiFi chip — ChipID, revision, ECID, health status |
| **`uwb`** | 4 | Ultra Wideband (U1/U2) — presence |
| **`uart`** | 13 | Debug serial port |

### Query by IOKit Class

| Class | Keys | Description |
|-------|------|-------------|
| **`IOPlatformExpertDevice`** | 26 | MLB serial, platform, model-config (vendors) |
| **`AppleSmartBattery`** | 57 | Battery serial, cycle count, voltage, temperature, capacity |
| **`AppleH16CamIn`** | 84 | Camera SNs, ISP firmware, validation, Savage/Yonkers secure chips |
| **`IOMobileFramebuffer`** | 115 | Display controller — Panel_ID, brightness, AOD, color mgmt |
| **`IONVMeController`** | 37 | Storage — SSD serial, model, firmware, vendor |
| **`AppleMultitouchDevice`** | 46 | Touch — Family ID, scan rate, sensor dimensions |
| **`AGXAccelerator`** | 30 | GPU — core count, generation, performance stats |
| **`AppleEmbeddedAudioDevice`** | 31 | Audio/Haptic — device UID, controls, streams |
| **`AppleARMIODevice` (pmgr)** | 75 | Power manager — voltage states, clusters, boost agents |
| **`AppleT8150PMGR`** | 19 | Power manager driver |
| **`AppleSPU`** | 17 | Always-On Processor — wake reasons, sensor endpoints |
| **`AppleSEPManager`** | 16 | Secure Enclave manager |
| **`AppleHPM`** | 16 | USB-C High Power Manager |
| **`IOHIDDevice` (BTM)** | 39 | Battery Thermal Manager |
| **`IOAccessoryPort`** | 14 | USB-C / accessory port info |
| **`IOTimeSyncClockManager`** | 13 | Time sync clocks |

### Query by Plane

| Plane | Description |
|-------|-------------|
| **`IODeviceTree`** | Full device tree (26 top-level children) |
| **`IOService`** | Service matching tree |
| **`IOPower`** | Power domain tree |
| **`IOAccessory`** | Accessory tree |
| **`CoreCapture`** | Packet capture tree |

## API Overview

All pymobiledevice3 APIs are **async** (v4.x+).

### Establishing a Connection

```python
import asyncio
from pymobiledevice3.lockdown import create_using_usbmux

async def main():
    lockdown = await create_using_usbmux()
    # Or specify a device by UDID
    lockdown = await create_using_usbmux(serial="<UDID>")

asyncio.run(main())
```

### Querying IORegistry

```python
from pymobiledevice3.services.diagnostics import DiagnosticsService

diag = DiagnosticsService(lockdown)

# Query by IOKit class name
result = await diag.ioregistry(ioclass="AppleSmartBattery")

# Query by IORegistry entry name
result = await diag.ioregistry(name="product")

# Query by IORegistry plane
result = await diag.ioregistry(plane="IODeviceTree")
```

## Detailed Entry Documentation

### `name=product` — Factory Provisioning Record

**The single most important data source.** Written to IODeviceTree during manufacturing. Contains all component serial numbers, hardware capability flags, chipset identifiers, and physical layout data. This is the same data source that tools like **3uTools** read.

#### Component Serial Numbers

| Key | Description |
|-----|-------------|
| `ambient-light-sensor-serial-num` | Ambient Light Sensor (ALS) serial |
| `backglass-compass-serial-number` | Compass/Magnetometer serial (mounted on back glass) |
| `coverglass-serial-number` | Cover glass serial (encoded, SN before first `+`) |
| `nova-serial-num` | Flash module (Nova) serial |
| `raw-panel-serial-number` | Full display panel ID (encoded, panel SN before first `+`) |
| `product-id` | Factory product hash (SHA-like, unique per unit) |

#### Chipset Identifiers

| Key | Description |
|-----|-------------|
| `baseband-chipset` | Qualcomm modem codename (e.g. `mav25`) |
| `wifi-chipset` | WiFi chip codename (e.g. `proxima`) |
| `bmu-chip-id` / `bmu-board-id` | Battery Management Unit #1 |
| `bmu2-chip-id` / `bmu2-board-id` | Battery Management Unit #2 |
| `graphics-featureset-class` | GPU generation (e.g. `APPLE10` = A18 GPU) |
| `app-macho-architecture` | CPU instruction set (e.g. `arm64e`) |

#### Display Properties

| Key | Description |
|-----|-------------|
| `oled-display` | Panel is OLED (`01` = true) |
| `artwork-display-gamut` | Color gamut (e.g. `P3`) |
| `artwork-scale-factor` | Retina scale (e.g. `03` = 3x) |
| `display-corner-radius` | Screen corner radius (pt, little-endian) |
| `display-mirroring` | Screen mirroring support |
| `supports-burnin-mitigation` | OLED burn-in protection |
| `island-notch-location` | Dynamic Island position |
| `thin-bezel` | Thin bezel design |
| `framebuffer-identifier` | Display framebuffer UUID |

#### Hardware Capabilities (Boolean Flags)

`01` = true, absent or `00` = false.

| Key | Description |
|-----|-------------|
| `builtin-battery` | Has built-in battery |
| `builtin-mics` | Number of microphones (value = count) |
| `gps-capable` | GPS hardware present |
| `esim-only` | eSIM only (no physical SIM tray) |
| `nfc-express` | NFC Express Mode |
| `low-power-express` / `low-power-wallet-mode` | Low Power Mode NFC/Wallet |
| `find-my` | Find My network support |
| `has-boot-chime` | Startup chime |
| `has-virtualization` | Hardware virtualization |
| `has-exclaves` / `exclaves-enabled` | Secure Enclave exclaves |
| `supports-camera-button` | Camera Control button (iPhone 16+) |
| `supports-recoveryos` | Dedicated Recovery OS partition |
| `supports-personal-translator` | On-device translation |
| `bluetooth-le` / `bluetooth-lea2` | BLE / LE Audio 2 |
| `high-bandwidth-radio` | High bandwidth cellular |
| `personal-hotspot` | Personal Hotspot |
| `car-integration` / `carplay-2` | CarPlay |
| `watch-companion` | Apple Watch pairing |
| `assistant` / `dictation` / `offline-dictation` | Siri & dictation |
| `hearingaid-audio-equalization` / `hearingaid-low-energy-audio` | Hearing aid |

#### Physical Layout

Binary-encoded structs for button/camera positions (proprietary format).

| Key | Description |
|-----|-------------|
| `side-button-location` | Power/Side button |
| `volume-up-button-location` / `volume-down-button-location` | Volume buttons |
| `ringer-button-location` | Ring/Silent switch |
| `camera-button-location` | Camera Control button (iPhone 16+) |
| `front-cam-offset-from-center` / `rear-cam-offset-from-center` | Camera offsets |

#### Device Identity

| Key | Description |
|-----|-------------|
| `product-name` / `product-description` | Marketing name |
| `sub-product-type` / `fdr-product-type` | Internal model identifiers |
| `unique-model` | Board model code |
| `compatible-device-fallback` | Previous-gen fallback model |
| `chrome-identifier` | DeviceKit chrome ID |

---

### `name=arm-io` — SoC Subsystem

| Key | Description | Example |
|-----|-------------|---------|
| `compatible` | SoC identifier | `arm-io,t8150` |
| `device_type` | Device type string | `t8150-io` |
| `soc-generation` | SoC generation codename | `H18` |
| `chip-revision` | Silicon revision | `11` |
| `fuse-revision` | Fuse revision | `01` |
| `die-count` | Number of dies | `01` |

---

### `name=cpus` — CPU Topology

| Key | Description | Example |
|-----|-------------|---------|
| `max_cpus` | Total CPU cores | `06` |
| `e-core-count` | Efficiency cores | `04` |
| `p-core-count` | Performance cores | `02` |
| `cpu-cluster-count` | Number of clusters | `02` |

---

### `ioclass=AGXAccelerator` — GPU

`GPUConfigurationVariable` sub-dict:

| Key | Description | Example |
|-----|-------------|---------|
| `num_cores` | GPU shader cores | `6` |
| `gpu_gen` | GPU generation | `18` |
| `gpu_var` | GPU variant | `P` |
| `num_frags` | Fragment processors | `6` |
| `num_gps` | Geometry processors | `3` |

`PerformanceStatistics` sub-dict:

| Key | Description |
|-----|-------------|
| `Device Utilization %` | Current GPU utilization |
| `Alloc system memory` | Total allocated GPU memory |
| `In use system memory` | Currently used GPU memory |
| `recoveryCount` | GPU recovery/reset count |

---

### `name=centauri` — WiFi Chip

| Key | Description | Example |
|-----|-------------|---------|
| `ChipID` | WiFi chip ID | `8230` |
| `ChipRevision` | Silicon revision | `B1` |
| `ECID` | Unique chip identifier | `4568954814247134778` |
| `WiFiHardwareHealthy` | WiFi hardware health | `True` |
| `BTHardwareHealthy` | BT hardware health (shared chip) | `True` |
| `wifi-antenna-sku-info` | Antenna SKU | (binary) |

---

### `name=fillmore` — Bluetooth Chip

| Key | Description | Example |
|-----|-------------|---------|
| `arch-type` | BT architecture | `bt1` |
| `compatible` | Chip identifier | `fillmore,bt` |
| `local-mac-address` | BT MAC (raw hex) | `84AC16001E30CCEC` |

---

### `name=backlight` — Display Backlight

| Key | Description | Example |
|-----|-------------|---------|
| `max-nit-value` | Max brightness (nits, LE int) | `3000` |
| `user-accessible-max-nits` | User-accessible max | `2404` → 580 nits |
| `edr-max-nits` | EDR/HDR max brightness | `4006` → 1600 nits |
| `EDRPotentialHeadroom` | EDR headroom multiplier | `08` → 8x |
| `EDRReferenceHeadroom` | EDR reference headroom | `0C` → 12x |
| `supports-aurora` | Always-On Display support | `01` |
| `supports-ammolite` | Ammolite display features | `01` |
| `use-bright-dot-mitigation` | Bright dot fix | `01` |
| `truetone-strength` | TrueTone calibration | (binary) |
| `backlight-marketing-table` | Brightness curve (402 bytes) | (binary) |
| `aml-*` | Auto-brightness tables/thresholds | (binary) |
| `tw-*` | TrueTone/white point tables | (binary) |

---

### `name=als` — Ambient Light Sensor

| Key | Description | Example |
|-----|-------------|---------|
| `ce-model` | Sensor model ID | `04` |
| `ce-threshold` | Threshold value | `ff` |
| `supports-float-lux` | Float lux support | `01` |
| `hotspot-center-x` / `hotspot-center-y` | Sensor position | (LE int) |

---

### `name=baseband` — Modem (Device Tree)

| Key | Description | Example |
|-----|-------------|---------|
| `compatible` | Modem identifier | `baseband,n41` |
| `device_type` | Device type | `baseband` |
| `imeisv` | IMEI software version | `07` |
| `baseband-heb` | HEB revision | `9C` |
| `baseband-idc` | IDC revision | `A5` |
| `smc-thermal-report-version` | Thermal report version | `02` |
| `supports-cpms-via-spmi` | CPMS via SPMI support | `01` |

---

### `name=buttons` — Physical Buttons

| Key | Description | Example |
|-----|-------------|---------|
| `home-button-type` | Button type (0=mechanical, 2=haptic) | `02` |
| `opposed-power-vol-buttons` | Power/Volume on opposite sides | `01` |
| `button-names` | Button name list | (binary) |
| `diagnostic-mask-all` | Diagnostic button combo | (binary) |
| `stackshot-mask` | Stackshot trigger combo | (binary) |

---

### `name=sep` — Secure Enclave

| Key | Description | Example |
|-----|-------------|---------|
| `role` | SEP role | `SEP` |
| `sepfw-loaded` | Firmware loaded | `01` |
| `sep-boot-slot` | Boot slot | `02` |
| `sika-support` | SIKA (SEP IKA) support | `01` |
| `aot-power` | Always-on-time power | `01` |
| `iop-version` | IOP protocol version | `01` |

---

### `ioclass=AppleH16CamIn` — Camera System

The class name varies by SoC: `AppleH{N}CamIn` where N=13(A14), 14(A15), 15(A16/A17), 16(A18).

#### Serial Numbers

| Key | Description |
|-----|-------------|
| `BackCameraModuleSerialNumString` | Rear wide camera SN |
| `BackSuperWideCameraModuleSerialNumString` / `BackSuperWideCameraSNUM` | Rear ultra-wide SN |
| `BackTeleCameraModuleSerialNumString` / `BackTeleCameraSNUM` | Rear telephoto SN |
| `FrontCameraModuleSerialNumString` | Front TrueDepth SN |
| `FrontIRCameraModuleSerialNumString` | Front IR camera SN |
| `FrontIRStructuredLightProjectorSerialNumString` | Face ID dot projector SN |
| `JasperSNUM` | Jasper sensor SNUM |

#### Validation & Calibration

| Key | Description | Values |
|-----|-------------|--------|
| `CmClValidationStatus` | Rear camera calibration | `Pass` / `Fail` |
| `CmPMValidationStatus` | Rear PM validation | `Pass` / `Fail` |
| `FCClValidationStatus` | Front camera calibration | `Pass` / `Fail` |
| `ValidationStatus` | ISP secure validation | `Valid` / `Invalid` |
| `RomeoStatus` | Face ID dot projector status | `Valid` / `Invalid` |
| `SavageDATFileStatus` | Savage firmware status | `Pass` / `Fail` |
| `YonkersDATFileStatus` | Yonkers firmware status | `Pass` / `Fail` |

Note: `ValidationStatus: Invalid` can appear on devices with original parts — it reflects ISP secure validation state, not part replacement status.

#### Secure Camera Chips

| Prefix | Description | Keys |
|--------|-------------|------|
| `Savage` | Secure ISP | `ChipID`, `DeviceID`, `DeviceRev`, `FabRevision`, `UID`, `Nonce`, `SNUM`, `MNS`, `PubKey` |
| `Yonkers` | Secure Element | `ChipID`, `DeviceID`, `FabRevision`, `UID`, `Nonce`, `SNUM`, `MNS`, `EphemeralPubKey`, `Signature` |

---

### `ioclass=AppleSmartBattery` — Battery

| Key | Description | Example |
|-----|-------------|---------|
| `Serial` | Battery serial number | `F8YHKZZ1UQT000161T` |
| `ManufacturerData` | Manufacturer string | `GWLHKA00MMW00010W4` |
| `DesignCapacity` | Factory capacity (mAh) | `4207` |
| `NominalChargeCapacity` | Current capacity (mAh) | `4254` |
| `CycleCount` | Charge cycle count | `80` |
| `Temperature` | Battery temp (centi-°C) | `3569` → 35.69°C |
| `Voltage` | Voltage (mV) | `4275` |
| `GasGaugeFirmwareVersion` | Gas gauge firmware | `209200029` |
| `AppleRawBatteryVoltage` | Raw voltage | `4282` |

`BatteryData` sub-dict contains: `ChemID`, `DateOfFirstUse`, `LifetimeData` (33 keys), `CellVoltage`, `Ra` tables (Ra00-Ra14), `Qmax`, `StateOfCharge`, `TrueRemainingCapacity`, and per-cell diagnostics.

---

### `ioclass=IONVMeController` — Storage

| Key | Description | Example |
|-----|-------------|---------|
| `Serial Number` | SSD serial | `0031e0521129a02e` |
| `Model Number` | SSD model | `APPLE SSD AP0512Z` |
| `Firmware Revision` | SSD firmware | `2914.80.` |
| `Vendor Name` | Manufacturer | `Apple` |
| `NVMe Revision Supported` | NVMe spec | `1.10` |
| `Chipset Name` | Controller type | `SSD Controller` |
| `Physical Interconnect` | Bus type | `Apple Fabric` |
| `AppleNANDStatus` | NAND health | `Ready` |

---

### `ioclass=AppleMultitouchDevice` — Touch Controller

| Key | Description | Example |
|-----|-------------|---------|
| `Multitouch ID` | Runtime touch ID | `504684633242206339` |
| `Family ID` | Touch controller family | `226` |
| `ScanRate` | Touch scan rate (Hz) | `120` |
| `Sensor Columns` / `Sensor Rows` | Touch grid | `18` x `37` |
| `Sensor Surface Width` / `Height` | Surface size | `6657` x `14473` |
| `SupportTapToWake` | Tap to Wake support | `True` |
| `MT Built-In` | Built-in device | `True` |

---

### `ioclass=IOPlatformExpertDevice` — MLB / Platform

| Key | Description | Example |
|-----|-------------|---------|
| `IOPlatformSerialNumber` | Device serial | `J6HL7KQ1WX` |
| `IOPlatformUUID` | Platform UUID | `102FA17D-43FD-...` |
| `mlb-serial-number` | MLB serial (bytes→ASCII) | `J85HM40028W0000WGU` |
| `regulatory-model-number` | FCC regulatory model | `A3257` |
| `platform-name` | SoC platform | `t8150` |
| `model-config` | Component vendors | `receiver_1=AAC;wifi_module_vendor=AMKOR;...` |

---

### `ioclass=AppleEmbeddedAudioDevice` — Audio / Haptics

| Key | Description | Example |
|-----|-------------|---------|
| `device UID` | Audio device UID | `Haptic Debug` |
| `device manufacturer` | Manufacturer | `Apple Inc.` |
| `device name` | Device name | `IOPHapticDebug` |
| `current state` | Audio state | `off` |
| `sample rate` | Sample rate | (large int) |
| `io buffer frame size` | Buffer size | `15840` |
| `controls` | Audio controls list | (complex struct) |

---

### `ioclass=IOAccessoryPort` — USB-C Port

| Key | Description | Example |
|-----|-------------|---------|
| `IOAccessoryTransportType` | Transport type | `2` (USB) |
| `IOAccessoryDevicePort` | Port number | `2` |
| `IOAccessoryPortManagerPrimaryPort` | Primary port | `2` |

---

### `ioclass=AppleHPM` — USB-C High Power Manager

| Key | Description | Example |
|-----|-------------|---------|
| `IONameMatched` | Driver matched | `usbc,cbtl1702,spmi` |
| `HPM RTPC Enabled` | Runtime power control | `True` |
| `RID` | Resistor ID | `0` |

---

### Lockdown Values (`lockdown.all_values`)

| Key | Description |
|-----|-------------|
| `SerialNumber` | Device serial number |
| `UniqueDeviceID` | UDID |
| `MLBSerialNumber` | MLB serial |
| `ChipID` / `BoardId` / `DieID` | SoC identifiers |
| `ChipSerialNo` | SoC serial (bytes→hex) |
| `BasebandChipID` / `BasebandSerialNumber` / `BasebandFirmwareVersion` | Modem info |
| `HardwareModel` / `HardwarePlatform` | Board/platform model |
| `WiFiAddress` / `BluetoothAddress` / `EthernetAddress` | MAC addresses |
| `FirmwareVersion` | iBoot version |
| `HasSiDP` | Silicon Device Provisioning |
| `InternationalMobileEquipmentIdentity` | IMEI |
| `IntegratedCircuitCardIdentity` | ICCID (SIM) |

### Lockdown Domains

| Domain | Description |
|--------|-------------|
| `com.apple.mobile.battery` | Battery level, charging state |
| `com.apple.mobile.internal` | CarrierBuild, IsInternal flags |
| `com.apple.disk_usage.factory` | Disk capacity, NAND info, usage breakdown |
| `com.apple.mobile.software_behavior` | Region behavior flags (shutter, NTSC, etc.) |

---

## IODeviceTree Structure

The full device tree (`plane=IODeviceTree`) has 26 top-level children:

```
device-tree
├── chosen          (secure-boot-hashes, manifest-properties, memory-map...)
├── aliases
├── memory
├── options
├── cpus            (cpu0-cpu5)
├── arm-io          (131 children: aic, pmgr, gpio, mcc, ...)
├── buttons
├── port-usb-c-1
├── port-inductive-1
├── backlight
├── core-brightness
├── baseband
├── product         (camera, facetime, maps, haptics, audio)
├── filesystems     (fstab, fstab-ephemeral-*)
├── fillmore        (Bluetooth chip)
├── iboot-syscfg    (manifest-entitlements) — locked, no data exposed
├── centauri        (WiFi chip)
└── ...
```

## Decoding Binary Values

Many values are stored as raw bytes. The decoding rules:

1. **Boolean flags** — Single byte: `\x01` = true, `\x00` = false
2. **Integers** — Little-endian byte order
3. **ASCII strings** — Null-terminated printable bytes (serial numbers)
4. **Hex identifiers** — Non-printable bytes displayed as uppercase hex
5. **Encoded structs** — Button positions, calibration matrices (proprietary)

```python
def decode_bytes(v):
    if isinstance(v, bytes):
        stripped = v.strip(b"\x00")
        if not stripped:
            return None
        if all(32 <= b < 127 for b in stripped):
            return stripped.decode("ascii")
        return stripped.hex().upper()
    return v
```

## Limitations

1. **MobileGestalt deprecated** on iOS 17.4+ — returns `MobileGestaltDeprecated`.
2. **Camera IORegistry class varies** by SoC: `AppleH{N}CamIn`. Try classes in reverse order.
3. **`raw-panel-serial-number`** — Concatenated string with `+` separators. Segment 0 is panel SN. First 3 chars encode display manufacturer (see table below).

### Display Panel Manufacturer Identification

The **first 3 characters** of `raw-panel-serial-number` identify the panel manufacturer:

| Prefix | Manufacturer | Quality Grade |
|--------|-------------|---------------|
| `G9N` | Samsung Display | Good |
| `G9P` | Samsung Display | Poor |
| `G9Q` | Samsung Display | Mid |
| `GVC` | LG Display | Good |
| `GH3` | LG Display | Poor |
| `F5V` | BOE | — |

**Manufacturing date** can also be decoded: after the `_` separator, digit 1 = year suffix (e.g., `5` = 2025), digits 2-3 = ISO week number. Example: `G9N_534...` → Samsung, week 34 of 2025.

> Note: These prefix mappings are community-researched (MacRumors, iFixit). Apple does not officially document them. BOE panels appear primarily on non-Pro models (iPhone 16/16 Plus onwards).
4. **Touch controller** — No traditional serial. Only `Multitouch ID` (runtime).
5. **WiFi/BT module serials** — Not exposed. Vendor from `model-config`, MAC from lockdown.
6. **Secure Enclave (SEP)** — Basic info accessible, but keys/certificates are not.
7. **Developer Mode** required on iOS 16+.
8. **Button/camera positions** — Binary structs, format not publicly documented.
9. **`iboot-syscfg`** — Entry exists in device tree but data is locked/not exposed.
10. **Parts and Service History** — Not accessible via any API. SEP validates component serials against SysCfg factory records at boot. Results only visible in Settings > General > About.
11. **`ValidationStatus: Invalid`** on camera does NOT mean part was replaced — it reflects ISP secure validation runtime state.
