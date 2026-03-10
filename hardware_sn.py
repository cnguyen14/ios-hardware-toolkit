"""
Export all hardware component information from a connected iOS device.

Reads the factory provisioning record (IORegistry name=product) plus other
IORegistry sources to produce a comprehensive hardware report.

Usage:
    uv run python hardware_sn.py            # Print to console
    uv run python hardware_sn.py -j         # Print JSON
    uv run python hardware_sn.py -o out.json # Save to file
    uv run python hardware_sn.py -u UDID    # Specific device
    uv run python hardware_sn.py --raw      # Include raw product dump
"""

import argparse
import asyncio
import json
import sys


def decode_bytes(v):
    if isinstance(v, bytes):
        stripped = v.strip(b"\x00")
        if not stripped:
            return None
        if all(32 <= b < 127 for b in stripped):
            return stripped.decode("ascii")
        return stripped.hex().upper()
    return v


def decode_bool(v):
    """Decode a single-byte boolean flag."""
    if isinstance(v, bytes):
        return bool(v[0]) if v else None
    if isinstance(v, int):
        return bool(v)
    return v


def decode_le_int(v):
    """Decode a little-endian integer from bytes."""
    if isinstance(v, bytes):
        stripped = v.strip(b"\x00")
        if not stripped:
            return None
        return int.from_bytes(stripped, "little")
    return v


# Panel serial prefix → manufacturer mapping (community-researched)
_PANEL_MANUFACTURER = {
    "G9N": "Samsung (Good)",
    "G9P": "Samsung (Poor)",
    "G9Q": "Samsung (Mid)",
    "GVC": "LG Display (Good)",
    "GH3": "LG Display (Poor)",
    "F5V": "BOE",
}


def detect_panel_manufacturer(raw_panel_serial: str | None) -> dict | None:
    """Detect display manufacturer from raw-panel-serial-number prefix."""
    if not raw_panel_serial:
        return None
    # Format: PREFIX_DIGITS... or PREFIX+...
    prefix = raw_panel_serial[:3]
    mfr = _PANEL_MANUFACTURER.get(prefix)
    # Extract manufacturing date from digits after prefix
    # After underscore: first digit = year suffix, next 2 = week number
    mfg_date = None
    parts = raw_panel_serial.split("_")
    if len(parts) >= 2 and len(parts[1]) >= 3:
        try:
            year_suffix = int(parts[1][0])
            week = int(parts[1][1:3])
            mfg_date = f"20{year_suffix:02d}-W{week:02d}"
        except (ValueError, IndexError):
            pass
    result = {"prefix": prefix}
    if mfr:
        result["manufacturer"] = mfr
    if mfg_date:
        result["manufacturing_date"] = mfg_date
    return result


# DeviceEnclosureColor → color name, keyed by ProductType prefix.
# Hex-based models (iPhone 6/6s/SE1) handled separately.
_HEX_COLORS = {
    "#3b3b3c": "Space Gray", "#e1e4e3": "Silver", "#e4e7e8": "Silver",
    "#d4c5b3": "Gold", "#e2c8b0": "Gold", "#ecc5c1": "Rose Gold",
}
_ENCLOSURE_COLORS = {
    # iPhone 7 / 7 Plus
    "iPhone9,1": {1: "Black", 2: "Silver", 3: "Gold", 4: "Rose Gold", 5: "Jet Black", 6: "(PRODUCT)RED"},
    "iPhone9,3": {1: "Black", 2: "Silver", 3: "Gold", 4: "Rose Gold", 5: "Jet Black", 6: "(PRODUCT)RED"},
    "iPhone9,2": {1: "Black", 2: "Silver", 3: "Gold", 4: "Rose Gold", 5: "Jet Black", 6: "(PRODUCT)RED"},
    "iPhone9,4": {1: "Black", 2: "Silver", 3: "Gold", 4: "Rose Gold", 5: "Jet Black", 6: "(PRODUCT)RED"},
    # iPhone 8 / 8 Plus
    "iPhone10,1": {1: "Space Gray", 2: "Silver", 3: "Gold", 6: "(PRODUCT)RED"},
    "iPhone10,4": {1: "Space Gray", 2: "Silver", 3: "Gold", 6: "(PRODUCT)RED"},
    "iPhone10,2": {1: "Space Gray", 2: "Silver", 3: "Gold", 6: "(PRODUCT)RED"},
    "iPhone10,5": {1: "Space Gray", 2: "Silver", 3: "Gold", 6: "(PRODUCT)RED"},
    # iPhone X
    "iPhone10,3": {1: "Space Gray", 2: "Silver"},
    "iPhone10,6": {1: "Space Gray", 2: "Silver"},
    # iPhone XS / XS Max
    "iPhone11,2": {1: "Space Gray", 2: "Silver", 4: "Gold"},
    "iPhone11,4": {1: "Space Gray", 2: "Silver", 4: "Gold"},
    "iPhone11,6": {1: "Space Gray", 2: "Silver", 4: "Gold"},
    # iPhone XR
    "iPhone11,8": {1: "Black", 2: "White", 6: "(PRODUCT)RED", 7: "Yellow", 8: "Coral", 9: "Blue"},
    # iPhone 11
    "iPhone12,1": {1: "Black", 2: "White", 6: "(PRODUCT)RED", 7: "Yellow", 11: "Purple", 12: "Green"},
    # iPhone 11 Pro / Pro Max
    "iPhone12,3": {1: "Space Gray", 2: "Silver", 4: "Gold", 12: "Midnight Green"},
    "iPhone12,5": {1: "Space Gray", 2: "Silver", 4: "Gold", 12: "Midnight Green"},
    # iPhone SE 2nd gen
    "iPhone12,8": {1: "Black", 2: "White", 6: "(PRODUCT)RED"},
    # iPhone 12 mini
    "iPhone13,1": {1: "Black", 2: "White", 6: "(PRODUCT)RED", 9: "Blue", 12: "Green", 17: "Purple"},
    # iPhone 12
    "iPhone13,2": {1: "Black", 2: "White", 6: "(PRODUCT)RED", 9: "Blue", 12: "Green", 17: "Purple"},
    # iPhone 12 Pro / Pro Max
    "iPhone13,3": {1: "Graphite", 2: "Silver", 3: "Gold", 9: "Pacific Blue"},
    "iPhone13,4": {1: "Graphite", 2: "Silver", 3: "Gold", 9: "Pacific Blue"},
    # iPhone 13 mini
    "iPhone14,4": {1: "Midnight", 2: "Starlight", 4: "Pink", 6: "(PRODUCT)RED", 9: "Blue", 18: "Green"},
    # iPhone 13
    "iPhone14,5": {1: "Midnight", 2: "Starlight", 4: "Pink", 6: "(PRODUCT)RED", 9: "Blue", 18: "Green"},
    # iPhone 13 Pro / Pro Max
    "iPhone14,2": {1: "Graphite", 2: "Silver", 3: "Gold", 9: "Sierra Blue", 18: "Alpine Green"},
    "iPhone14,3": {1: "Graphite", 2: "Silver", 3: "Gold", 9: "Sierra Blue", 18: "Alpine Green"},
    # iPhone SE 3rd gen
    "iPhone14,6": {1: "Midnight", 2: "Starlight", 6: "(PRODUCT)RED"},
    # iPhone 14 / 14 Plus
    "iPhone14,7": {1: "Midnight", 2: "Starlight", 6: "(PRODUCT)RED", 7: "Yellow", 9: "Blue", 17: "Purple"},
    "iPhone14,8": {1: "Midnight", 2: "Starlight", 6: "(PRODUCT)RED", 7: "Yellow", 9: "Blue", 17: "Purple"},
    # iPhone 14 Pro / Pro Max
    "iPhone15,2": {1: "Space Black", 2: "Silver", 3: "Gold", 17: "Deep Purple"},
    "iPhone15,3": {1: "Space Black", 2: "Silver", 3: "Gold", 17: "Deep Purple"},
    # iPhone 15 / 15 Plus
    "iPhone15,4": {1: "Black", 4: "Pink", 7: "Yellow", 9: "Blue", 18: "Green"},
    "iPhone15,5": {1: "Black", 4: "Pink", 7: "Yellow", 9: "Blue", 18: "Green"},
    # iPhone 15 Pro / Pro Max
    "iPhone16,1": {1: "Black Titanium", 2: "White Titanium", 5: "Natural Titanium", 9: "Blue Titanium"},
    "iPhone16,2": {1: "Black Titanium", 2: "White Titanium", 5: "Natural Titanium", 9: "Blue Titanium"},
    # iPhone 16 / 16 Plus
    "iPhone17,1": {1: "Black", 2: "White", 4: "Teal", 5: "Pink", 9: "Ultramarine"},
    "iPhone17,2": {1: "Black", 2: "White", 4: "Teal", 5: "Pink", 9: "Ultramarine"},
    # iPhone 16 Pro / Pro Max
    "iPhone17,3": {1: "Black Titanium", 2: "White Titanium", 4: "Desert Titanium", 9: "Natural Titanium"},
    "iPhone17,4": {1: "Black Titanium", 2: "White Titanium", 4: "Desert Titanium", 9: "Natural Titanium"},
    # iPhone 17 Pro / Pro Max
    "iPhone18,1": {1: "Cosmic Orange", 2: "Silver", 9: "Deep Blue"},
    "iPhone18,2": {1: "Cosmic Orange", 2: "Silver", 9: "Deep Blue"},
    # iPhone 17
    "iPhone18,3": {1: "Black", 2: "White", 4: "Lavender", 5: "Sage", 9: "Mist Blue"},
    # iPhone Air
    "iPhone18,4": {1: "Space Black", 2: "Cloud White", 4: "Sky Blue", 5: "Light Gold"},
}


def resolve_device_color(product_type: str, enclosure_color, device_color=None) -> str | None:
    """Resolve numeric DeviceEnclosureColor to marketing color name."""
    if enclosure_color is None:
        return None
    ec_str = str(enclosure_color)
    # Hex-based (iPhone 6/6s/SE1)
    if ec_str.startswith("#"):
        return _HEX_COLORS.get(ec_str, ec_str)
    # Numeric
    try:
        ec_int = int(ec_str)
    except (ValueError, TypeError):
        return ec_str
    model_map = _ENCLOSURE_COLORS.get(product_type)
    if model_map:
        return model_map.get(ec_int, f"Unknown ({ec_int})")
    return f"Color ID {ec_int}"


async def _ioregistry(diag, **kwargs):
    """Query IORegistry, return empty dict on failure."""
    try:
        return await diag.ioregistry(**kwargs) or {}
    except Exception:
        return {}


async def collect(udid: str | None = None, include_raw: bool = False) -> dict:
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.diagnostics import DiagnosticsService

    lockdown = await create_using_usbmux(serial=udid)
    diag = DiagnosticsService(lockdown)
    info = lockdown.all_values

    # ── Product entry: factory provisioning record ──
    product = await _ioregistry(diag, name="product")

    # ── Device enclosure color (all_values may return None on newer models) ──
    enclosure_color = info.get("DeviceEnclosureColor")
    if enclosure_color is None:
        try:
            lockdown2 = await create_using_usbmux(serial=udid)
            enclosure_color = await lockdown2.get_value(key="DeviceEnclosureColor")
        except Exception:
            pass

    result = {}

    # ══════════════════════════════════════════════════
    # 1. DEVICE IDENTITY
    # ══════════════════════════════════════════════════
    result["device"] = {
        "product_name": decode_bytes(product.get("product-name")),
        "product_description": decode_bytes(product.get("product-description")),
        "serial_number": info.get("SerialNumber"),
        "udid": info.get("UniqueDeviceID"),
        "product_type": info.get("ProductType"),
        "sub_product_type": decode_bytes(product.get("sub-product-type")),
        "fdr_product_type": decode_bytes(product.get("fdr-product-type")),
        "model_number": info.get("ModelNumber"),
        "hardware_model": info.get("HardwareModel"),
        "unique_model": decode_bytes(product.get("unique-model")),
        "compatible_device_fallback": decode_bytes(product.get("compatible-device-fallback")),
        "chrome_identifier": decode_bytes(product.get("chrome-identifier")),
        "ios_version": info.get("ProductVersion"),
        "build": info.get("BuildVersion"),
        "product_id": decode_bytes(product.get("product-id")),
        # Device color
        "color": resolve_device_color(
            info.get("ProductType", ""),
            enclosure_color,
            info.get("DeviceColor"),
        ),
        "color_id": enclosure_color,
        "image_url": (
            f"https://statici.icloud.com/fmipmobile/deviceImages-9.0/iPhone/"
            f"{info.get('ProductType')}-{info.get('DeviceColor')}-{enclosure_color}-0/"
            f"online-sourcelist__3x.png"
        ) if info.get("ProductType") and info.get("DeviceColor") and enclosure_color else None,
    }

    # ══════════════════════════════════════════════════
    # 2. MAIN LOGIC BOARD (MLB)
    # ══════════════════════════════════════════════════
    platform = await _ioregistry(diag, ioclass="IOPlatformExpertDevice")
    model_config = decode_bytes(platform.get("model-config")) or ""
    config_parts = {}
    if isinstance(model_config, str):
        for part in model_config.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                config_parts[k.strip()] = v.strip()

    result["mlb"] = {
        "serial_number": decode_bytes(platform.get("mlb-serial-number")),
        "regulatory_model": decode_bytes(platform.get("regulatory-model-number")),
        "platform": decode_bytes(platform.get("platform-name")),
        "model_config": model_config if model_config else None,
    }

    # ══════════════════════════════════════════════════
    # 3. SoC / ARM-IO
    # ══════════════════════════════════════════════════
    arm_io = await _ioregistry(diag, name="arm-io")
    result["soc"] = {
        "chip_id": info.get("ChipID"),
        "board_id": info.get("BoardId"),
        "die_id": info.get("DieID"),
        "chip_serial": decode_bytes(info.get("ChipSerialNo")),
        "platform": info.get("HardwarePlatform"),
        "graphics_featureset": decode_bytes(product.get("graphics-featureset-class")),
        "app_macho_architecture": decode_bytes(product.get("app-macho-architecture")),
        "soc_generation": decode_bytes(arm_io.get("soc-generation")),
        "chip_revision": decode_bytes(arm_io.get("chip-revision")),
        "fuse_revision": decode_bytes(arm_io.get("fuse-revision")),
        "die_count": decode_le_int(arm_io.get("die-count")),
    }

    # ══════════════════════════════════════════════════
    # 4. CPU
    # ══════════════════════════════════════════════════
    cpus = await _ioregistry(diag, name="cpus")
    if cpus:
        result["cpu"] = {
            "total_cores": decode_le_int(cpus.get("max_cpus")),
            "e_cores": decode_le_int(cpus.get("e-core-count")),
            "p_cores": decode_le_int(cpus.get("p-core-count")),
            "clusters": decode_le_int(cpus.get("cpu-cluster-count")),
        }

    # ══════════════════════════════════════════════════
    # 5. GPU
    # ══════════════════════════════════════════════════
    gpu = await _ioregistry(diag, ioclass="AGXAccelerator")
    if gpu:
        gpu_config = gpu.get("GPUConfigurationVariable", {})
        gpu_perf = gpu.get("PerformanceStatistics", {})
        result["gpu"] = {
            "cores": gpu_config.get("num_cores"),
            "generation": gpu_config.get("gpu_gen"),
            "variant": gpu_config.get("gpu_var"),
            "num_frags": gpu_config.get("num_frags"),
            "num_gps": gpu_config.get("num_gps"),
            "driver": gpu.get("CFBundleIdentifier"),
            "matched_device": gpu.get("IONameMatched"),
            "device_utilization": gpu_perf.get("Device Utilization %"),
            "recovery_count": gpu_perf.get("recoveryCount"),
            "alloc_system_memory": gpu_perf.get("Alloc system memory"),
        }

    # ══════════════════════════════════════════════════
    # 6. CHIPSET IDENTIFIERS (from product entry)
    # ══════════════════════════════════════════════════
    chipsets = {
        "baseband_chipset": decode_bytes(product.get("baseband-chipset")),
        "wifi_chipset": decode_bytes(product.get("wifi-chipset")),
        "bmu_chip_id": decode_bytes(product.get("bmu-chip-id")),
        "bmu_board_id": decode_bytes(product.get("bmu-board-id")),
        "bmu2_chip_id": decode_bytes(product.get("bmu2-chip-id")),
        "bmu2_board_id": decode_bytes(product.get("bmu2-board-id")),
    }
    result["chipsets"] = chipsets

    # ══════════════════════════════════════════════════
    # 7. BATTERY
    # ══════════════════════════════════════════════════
    battery = await diag.get_battery() or {}
    batt_data = battery.get("BatteryData", {})
    result["battery"] = {
        "serial_number": battery.get("Serial"),
        "manufacturer_data": decode_bytes(battery.get("ManufacturerData")),
        "design_capacity_mah": battery.get("DesignCapacity"),
        "nominal_capacity_mah": battery.get("NominalChargeCapacity"),
        "cycle_count": batt_data.get("CycleCount") or battery.get("CycleCount"),
        "temperature_c": round(battery.get("Temperature", 0) / 100, 1) if battery.get("Temperature") else None,
        "voltage_mv": battery.get("Voltage"),
        "gas_gauge_firmware": battery.get("GasGaugeFirmwareVersion"),
        "chem_id": batt_data.get("ChemID"),
    }

    # ══════════════════════════════════════════════════
    # 8. CAMERAS
    # ══════════════════════════════════════════════════
    cameras = None
    for gen in ["H16", "H15", "H14", "H13", "H12", "H11", "H10", "H9"]:
        cameras = await _ioregistry(diag, ioclass=f"Apple{gen}CamIn")
        if cameras:
            break
    if cameras:
        cam = {}
        cam_map = {
            "back_wide": "BackCameraModuleSerialNumString",
            "back_ultrawide": "BackSuperWideCameraModuleSerialNumString",
            "back_ultrawide_snum": "BackSuperWideCameraSNUM",
            "back_tele": "BackTeleCameraModuleSerialNumString",
            "back_tele_snum": "BackTeleCameraSNUM",
            "front": "FrontCameraModuleSerialNumString",
            "front_ir": "FrontIRCameraModuleSerialNumString",
            "faceid_dot_projector": "FrontIRStructuredLightProjectorSerialNumString",
            "jasper_snum": "JasperSNUM",
        }
        for key, ioreg_key in cam_map.items():
            val = cameras.get(ioreg_key)
            if val:
                cam[key] = decode_bytes(val)
        cam["isp_firmware"] = cameras.get("ISPFirmwareVersion")
        cam["isp_firmware_date"] = cameras.get("ISPFirmwareLinkDate")
        cam["calibration_cm"] = cameras.get("CmClValidationStatus")
        cam["calibration_pm"] = cameras.get("CmPMValidationStatus")
        cam["calibration_fc"] = cameras.get("FCClValidationStatus")
        cam["validation_status"] = cameras.get("ValidationStatus")
        cam["romeo_status"] = cameras.get("RomeoStatus")
        for prefix in ["Savage", "Yonkers"]:
            for suffix in ["ChipID", "UID", "Nonce", "SNUM"]:
                key_name = f"{prefix}{suffix}"
                val = cameras.get(key_name)
                if val:
                    cam[f"{prefix.lower()}_{suffix.lower()}"] = decode_bytes(val)
            dat = cameras.get(f"{prefix}DATFileStatus")
            if dat:
                cam[f"{prefix.lower()}_dat_status"] = dat
        result["cameras"] = cam

    # ══════════════════════════════════════════════════
    # 9. STORAGE (NVMe)
    # ══════════════════════════════════════════════════
    storage = await _ioregistry(diag, ioclass="IONVMeController")
    if storage:
        result["storage"] = {
            "serial_number": storage.get("Serial Number"),
            "model": storage.get("Model Number"),
            "vendor": storage.get("Vendor Name"),
            "firmware": storage.get("Firmware Revision"),
            "nvme_revision": storage.get("NVMe Revision Supported"),
            "chipset_name": storage.get("Chipset Name"),
            "interconnect": storage.get("Physical Interconnect"),
            "nand_status": storage.get("AppleNANDStatus"),
        }

    # ══════════════════════════════════════════════════
    # 10. DISPLAY
    # ══════════════════════════════════════════════════
    raw_panel = decode_bytes(product.get("raw-panel-serial-number"))
    panel_sn = None
    coverglass_sn = decode_bytes(product.get("coverglass-serial-number"))
    if raw_panel and "+" in raw_panel:
        panel_sn = raw_panel.split("+")[0]
    # Backlight + TrueTone data (merge into display section)
    backlight = await _ioregistry(diag, name="backlight")
    # IOMobileFramebuffer for runtime TrueTone state
    framebuffer = await _ioregistry(diag, ioclass="IOMobileFramebuffer")

    panel_info = detect_panel_manufacturer(raw_panel)
    result["display"] = {
        "panel_serial": panel_sn,
        "panel_manufacturer": panel_info.get("manufacturer") if panel_info else None,
        "panel_prefix": panel_info.get("prefix") if panel_info else None,
        "panel_manufacturing_date": panel_info.get("manufacturing_date") if panel_info else None,
        "coverglass_serial": coverglass_sn.split("+")[0] if coverglass_sn and "+" in coverglass_sn else coverglass_sn,
        "raw_panel_id": raw_panel,
        "oled": decode_bool(product.get("oled-display")),
        "gamut": decode_bytes(product.get("artwork-display-gamut")),
        "scale_factor": decode_bytes(product.get("artwork-scale-factor")),
        "corner_radius": int.from_bytes(product.get("display-corner-radius", b"")[:4], "little") if product.get("display-corner-radius") else None,
        "mirroring": decode_bool(product.get("display-mirroring")),
        "burnin_mitigation": decode_bool(product.get("supports-burnin-mitigation")),
        "island_notch_location": decode_bytes(product.get("island-notch-location")),
        "thin_bezel": decode_bool(product.get("thin-bezel")),
        "dynamic_displaymode": decode_bytes(product.get("artwork-dynamic-displaymode")),
        "framebuffer_id": decode_bytes(product.get("framebuffer-identifier")),
        # Backlight specs
        "max_nits": decode_le_int(backlight.get("max-nit-value")) if backlight else None,
        "user_max_nits": decode_le_int(backlight.get("user-accessible-max-nits")) if backlight else None,
        "edr_max_nits": decode_le_int(backlight.get("edr-max-nits")) if backlight else None,
        "edr_potential_headroom": decode_le_int(backlight.get("EDRPotentialHeadroom")) if backlight else None,
        "edr_reference_headroom": decode_le_int(backlight.get("EDRReferenceHeadroom")) if backlight else None,
        "panel_gamma": decode_bytes(backlight.get("panel-gamma")) if backlight else None,
        "aurora_aod": decode_bool(backlight.get("supports-aurora")) if backlight else None,
        "ammolite": decode_bool(backlight.get("supports-ammolite")) if backlight else None,
        "bright_dot_mitigation": decode_bool(backlight.get("use-bright-dot-mitigation")) if backlight else None,
        # TrueTone
        "truetone_calibrated": bool(backlight.get("truetone-strength")) if backlight else None,
        "truetone_strength": decode_bytes(backlight.get("truetone-strength")) if backlight else None,
        "truetone_cct_warning": decode_le_int(backlight.get("blr-cct-warning")) if backlight else None,
        "truetone_runtime_enabled": framebuffer.get("IOMFBTemperatureCompensationEnable") if framebuffer else None,
        # Factory calibration (from product)
        "factory_calibration_matrix": decode_bytes(product.get("primary-calibration-matrix")),
        "factory_backlight_compensation": decode_bytes(product.get("display-backlight-compensation")),
    }

    # ══════════════════════════════════════════════════
    # 12. COMPONENT SERIAL NUMBERS (from product)
    # ══════════════════════════════════════════════════
    result["ambient_light_sensor"] = {
        "serial_number": decode_bytes(product.get("ambient-light-sensor-serial-num")),
    }
    # ALS device tree details
    als = await _ioregistry(diag, name="als")
    if als:
        result["ambient_light_sensor"]["ce_model"] = decode_bytes(als.get("ce-model"))
        result["ambient_light_sensor"]["supports_float_lux"] = decode_bool(als.get("supports-float-lux"))

    result["compass"] = {
        "serial_number": decode_bytes(product.get("backglass-compass-serial-number")),
    }

    nova_sn = decode_bytes(product.get("nova-serial-num"))
    if nova_sn:
        result["flash_nova"] = {
            "serial_number": nova_sn,
        }

    # ══════════════════════════════════════════════════
    # 13. TOUCH CONTROLLER
    # ══════════════════════════════════════════════════
    touch = await _ioregistry(diag, ioclass="AppleMultitouchDevice")
    if touch:
        result["touch"] = {
            "multitouch_id": touch.get("Multitouch ID"),
            "family_id": touch.get("Family ID"),
            "scan_rate": touch.get("ScanRate"),
            "sensor_columns": touch.get("Sensor Columns"),
            "sensor_rows": touch.get("Sensor Rows"),
            "surface_width": touch.get("Sensor Surface Width"),
            "surface_height": touch.get("Sensor Surface Height"),
            "tap_to_wake": touch.get("SupportTapToWake"),
        }

    # ══════════════════════════════════════════════════
    # 14. BASEBAND / MODEM
    # ══════════════════════════════════════════════════
    bb_dt = await _ioregistry(diag, name="baseband")
    result["baseband"] = {
        "serial_number": decode_bytes(info.get("BasebandSerialNumber")),
        "chip_id": info.get("BasebandChipID"),
        "firmware": decode_bytes(info.get("BasebandFirmwareVersion")),
        "chipset": decode_bytes(product.get("baseband-chipset")),
        "compatible": decode_bytes(bb_dt.get("compatible")),
        "imeisv": decode_bytes(bb_dt.get("imeisv")),
    }

    # ══════════════════════════════════════════════════
    # 15. WIFI CHIP (centauri)
    # ══════════════════════════════════════════════════
    centauri = await _ioregistry(diag, name="centauri")
    result["wifi"] = {
        "mac_address": info.get("WiFiAddress"),
        "module_vendor": config_parts.get("wifi_module_vendor"),
        "chipset": decode_bytes(product.get("wifi-chipset")),
        "chip_id": decode_bytes(centauri.get("ChipID")) if centauri else None,
        "chip_revision": decode_bytes(centauri.get("ChipRevision")) if centauri else None,
        "ecid": centauri.get("ECID") if centauri else None,
        "hardware_healthy": centauri.get("WiFiHardwareHealthy") if centauri else None,
        "bt_hardware_healthy": centauri.get("BTHardwareHealthy") if centauri else None,
        "antenna_sku": decode_bytes(centauri.get("wifi-antenna-sku-info")) if centauri else None,
    }

    # ══════════════════════════════════════════════════
    # 16. BLUETOOTH CHIP (fillmore)
    # ══════════════════════════════════════════════════
    fillmore = await _ioregistry(diag, name="fillmore")
    bt_dt = await _ioregistry(diag, name="bluetooth")
    result["bluetooth"] = {
        "mac_address": info.get("BluetoothAddress"),
        "le": decode_bool(product.get("bluetooth-le")),
        "lea2": decode_bool(product.get("bluetooth-lea2")),
        "arch_type": decode_bytes(fillmore.get("arch-type")) if fillmore else None,
        "fillmore_mac": decode_bytes(fillmore.get("local-mac-address")) if fillmore else None,
        "transport_encoding": decode_bytes(bt_dt.get("transport-encoding")) if bt_dt else None,
    }

    # ══════════════════════════════════════════════════
    # 17. UWB (Ultra Wideband)
    # ══════════════════════════════════════════════════
    uwb = await _ioregistry(diag, name="uwb")
    if uwb:
        result["uwb"] = {
            "present": True,
        }

    # ══════════════════════════════════════════════════
    # 18. AUDIO
    # ══════════════════════════════════════════════════
    receiver_vendor = config_parts.get("receiver_1")
    builtin_mics = decode_bytes(product.get("builtin-mics"))
    audio_dev = await _ioregistry(diag, ioclass="AppleEmbeddedAudioDevice")
    audio_info = {}
    if receiver_vendor:
        audio_info["receiver_vendor"] = receiver_vendor
    if builtin_mics:
        audio_info["builtin_mics"] = decode_le_int(product.get("builtin-mics"))
    if audio_dev:
        audio_info["haptic_device"] = audio_dev.get("device UID")
        audio_info["manufacturer"] = audio_dev.get("device manufacturer")
    if audio_info:
        result["audio"] = audio_info

    # ══════════════════════════════════════════════════
    # 19. USB-C / ACCESSORY PORT
    # ══════════════════════════════════════════════════
    acc_port = await _ioregistry(diag, ioclass="IOAccessoryPort")
    hpm = await _ioregistry(diag, ioclass="AppleHPM")
    if acc_port or hpm:
        result["usb_port"] = {
            "transport_type": acc_port.get("IOAccessoryTransportType") if acc_port else None,
            "device_port": acc_port.get("IOAccessoryDevicePort") if acc_port else None,
            "hpm_driver": hpm.get("IONameMatched") if hpm else None,
        }

    # ══════════════════════════════════════════════════
    # 20. SECURE ENCLAVE (SEP)
    # ══════════════════════════════════════════════════
    sep = await _ioregistry(diag, name="sep")
    if sep:
        result["secure_enclave"] = {
            "firmware_loaded": decode_bool(sep.get("sepfw-loaded")),
            "boot_slot": decode_le_int(sep.get("sep-boot-slot")),
            "sika_support": decode_bool(sep.get("sika-support")),
            "aot_power": decode_bool(sep.get("aot-power")),
            "role": decode_bytes(sep.get("role")),
        }

    # ══════════════════════════════════════════════════
    # 21. BUTTONS
    # ══════════════════════════════════════════════════
    buttons = await _ioregistry(diag, name="buttons")
    if buttons:
        result["buttons"] = {
            "home_button_type": decode_le_int(buttons.get("home-button-type")),
            "opposed_power_vol": decode_bool(buttons.get("opposed-power-vol-buttons")),
        }

    # ══════════════════════════════════════════════════
    # 22. HARDWARE CAPABILITIES
    # ══════════════════════════════════════════════════
    capability_keys = {
        "builtin_battery": "builtin-battery",
        "gps_capable": "gps-capable",
        "esim_only": "esim-only",
        "nfc_express": "nfc-express",
        "low_power_express": "low-power-express",
        "low_power_wallet": "low-power-wallet-mode",
        "find_my": "find-my",
        "boot_chime": "has-boot-chime",
        "virtualization": "has-virtualization",
        "exclaves": "has-exclaves",
        "exclaves_enabled": "exclaves-enabled",
        "camera_button": "supports-camera-button",
        "recovery_os": "supports-recoveryos",
        "lotx": "supports-lotx",
        "personal_translator": "supports-personal-translator",
        "single_stage_boot": "single-stage-boot",
        "public_key_accelerator": "public-key-accelerator",
        "high_bandwidth_radio": "high-bandwidth-radio",
        "personal_hotspot": "personal-hotspot",
        "iap2_protocol": "iap2-protocol-supported",
        "carplay": "car-integration",
        "carplay_2": "carplay-2",
        "watch_companion": "watch-companion",
        "assistant": "assistant",
        "dictation": "dictation",
        "offline_dictation": "offline-dictation",
        "siri_gesture": "siri-gesture",
        "location_reminders": "location-reminders",
        "hearingaid_eq": "hearingaid-audio-equalization",
        "hearingaid_le_audio": "hearingaid-low-energy-audio",
        "sandman": "sandman-support",
        "ptp_large_files": "ptp-large-files",
        "hme_in_arkit": "hme-in-arkit",
        "pip": "ui-pip",
        "reachability": "ui-reachability",
    }
    caps = {}
    for key, product_key in capability_keys.items():
        val = product.get(product_key)
        if val is not None:
            caps[key] = decode_bool(val)
    if caps:
        result["capabilities"] = caps

    # ══════════════════════════════════════════════════
    # 23. PHYSICAL LAYOUT (button/camera positions)
    # ══════════════════════════════════════════════════
    layout_keys = {
        "side_button": "side-button-location",
        "volume_up_button": "volume-up-button-location",
        "volume_down_button": "volume-down-button-location",
        "ringer_button": "ringer-button-location",
        "camera_button": "camera-button-location",
        "front_cam_offset": "front-cam-offset-from-center",
        "front_cam_rotation": "front-cam-rotation-isp",
        "rear_cam_offset": "rear-cam-offset-from-center",
    }
    layout = {}
    for key, product_key in layout_keys.items():
        val = product.get(product_key)
        if val is not None:
            layout[key] = decode_bytes(val)
    if layout:
        result["physical_layout"] = layout

    # ══════════════════════════════════════════════════
    # 24. SOFTWARE & PROTOCOL INFO
    # ══════════════════════════════════════════════════
    sw_keys = {
        "artwork_device_idiom": "artwork-device-idiom",
        "artwork_device_subtype": "artwork-device-subtype",
        "partition_style": "partition-style",
        "activation_protocol_version": "activation-protocol-version",
        "lockdown_certtype": "lockdown-certtype",
        "udid_version": "udid-version",
        "itunes_min_ver": "itunes-min-ver",
        "mobiledevice_min_ver": "mobiledevice-min-ver",
        "ucrt_enforced": "ucrt-enforced",
        "allow_32bit_apps": "allow-32bit-apps",
        "hid_workgroup_interval": "hid-workgroup-interval",
        "rf_exposure_distance": "RF-exposure-separation-distance",
        "ui_background_quality": "ui-background-quality",
        "ui_weather_quality": "ui-weather-quality",
        "hme_refresh_rate": "hme-refresh-rate",
    }
    sw = {}
    for key, product_key in sw_keys.items():
        val = product.get(product_key)
        if val is not None:
            sw[key] = decode_bytes(val)
    if sw:
        result["software_info"] = sw

    # ══════════════════════════════════════════════════
    # 25. RAW PRODUCT DUMP (optional)
    # ══════════════════════════════════════════════════
    if include_raw and product:
        raw = {}
        for k, v in sorted(product.items()):
            decoded = decode_bytes(v)
            if decoded is not None:
                raw[k] = decoded
        result["_raw_product"] = raw

    # ── Clean: remove keys with None values, remove empty sections ──
    for section in list(result.keys()):
        if isinstance(result[section], dict):
            for k in list(result[section]):
                if result[section][k] is None:
                    del result[section][k]
            if not result[section]:
                del result[section]

    return result


def print_table(data: dict):
    print("=" * 78)
    print(f"  {'COMPONENT':<28} {'KEY':<24} VALUE")
    print("=" * 78)
    for section, values in data.items():
        if not isinstance(values, dict) or not values:
            continue
        if section.startswith("_"):
            continue
        label = section.upper().replace("_", " ")
        first = True
        for k, v in values.items():
            display_v = str(v)
            col1 = f"  {label}" if first else "  "
            print(f"{col1:<28} {k:<24} {display_v}")
            first = False
        print("-" * 78)
    print("=" * 78)


async def main():
    parser = argparse.ArgumentParser(description="Export iOS hardware information")
    parser.add_argument("-u", "--udid", help="Device UDID")
    parser.add_argument("-j", "--json", action="store_true", help="Output as JSON")
    parser.add_argument("-o", "--output", help="Save JSON to file")
    parser.add_argument("--raw", action="store_true", help="Include raw product entry dump")
    args = parser.parse_args()

    data = await collect(args.udid, include_raw=args.raw)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Saved to {args.output}")
    elif args.json:
        print(json.dumps(data, indent=2, default=str))
    else:
        print_table(data)
        if args.raw and "_raw_product" in data:
            print(f"\n{'=' * 78}")
            print("  RAW PRODUCT ENTRY (all {0} keys)".format(len(data["_raw_product"])))
            print("=" * 78)
            for k, v in data["_raw_product"].items():
                print(f"  {k:<45} {v}")
            print("=" * 78)


if __name__ == "__main__":
    asyncio.run(main())
