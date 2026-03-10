"""
iOS Hardware Monitor - Đọc syslog từ iDevices và trích xuất thông tin hardware.

Sử dụng pymobiledevice3 để:
1. Lấy device info cơ bản
2. Lấy hardware info trực tiếp (battery, IORegistry)
3. Stream & parse syslog realtime, filter hardware entries

Usage:
    uv run python ios_hardware_monitor.py info          # Device + hardware info
    uv run python ios_hardware_monitor.py syslog        # Stream hardware syslog
    uv run python ios_hardware_monitor.py syslog --all  # Stream ALL syslog (không filter)
    uv run python ios_hardware_monitor.py syslog --json output.json  # Xuất JSON
    uv run python ios_hardware_monitor.py syslog --categories thermal,battery
"""

import argparse
import asyncio
import json
import sys

from syslog_parser import (
    HardwareCategory,
    entry_to_dict,
    format_entry,
    parse_syslog_entry,
)


async def get_lockdown_client(udid: str | None = None):
    """Create a lockdown client via USB."""
    from pymobiledevice3.lockdown import create_using_usbmux

    return await create_using_usbmux(serial=udid)


def print_device_info(lockdown):
    """Print basic device information."""
    info = lockdown.all_values
    print("=" * 60)
    print("  iOS DEVICE INFORMATION")
    print("=" * 60)

    fields = [
        ("Device Name", "DeviceName"),
        ("Model", "ProductType"),
        ("iOS Version", "ProductVersion"),
        ("Build", "BuildVersion"),
        ("UDID", "UniqueDeviceID"),
        ("Serial", "SerialNumber"),
        ("WiFi MAC", "WiFiAddress"),
        ("Bluetooth MAC", "BluetoothAddress"),
        ("Hardware Model", "HardwareModel"),
        ("CPU Architecture", "CPUArchitecture"),
        ("Chip ID", "ChipID"),
        ("Board ID", "BoardId"),
        ("Device Class", "DeviceClass"),
        ("Device Color", "DeviceColor"),
        ("Total Disk", "TotalDiskCapacity"),
        ("Available Disk", "TotalDataAvailable"),
        ("Battery Level", "BatteryCurrentCapacity"),
        ("Battery Charging", "BatteryIsCharging"),
    ]

    for label, key in fields:
        value = info.get(key, "N/A")
        if key in ("TotalDiskCapacity", "TotalDataAvailable") and isinstance(value, (int, float)):
            value = f"{value / (1024**3):.1f} GB"
        if key == "BatteryCurrentCapacity" and isinstance(value, (int, float)):
            value = f"{value}%"
        print(f"  {label:20s}: {value}")

    print("=" * 60)


async def print_battery_info(lockdown):
    """Print detailed battery info via DiagnosticsService."""
    try:
        from pymobiledevice3.services.diagnostics import DiagnosticsService

        diag = DiagnosticsService(lockdown)
        battery = await diag.get_battery()

        print("\n" + "=" * 60)
        print("  BATTERY DETAILS")
        print("=" * 60)

        if isinstance(battery, dict):
            for key, value in sorted(battery.items()):
                if isinstance(value, bytes):
                    value = f"<{len(value)} bytes>"
                print(f"  {key:30s}: {value}")
        else:
            print(f"  {battery}")

        print("=" * 60)
    except Exception as e:
        print(f"\n[!] Cannot get battery info: {e}")


async def print_ioregistry_info(lockdown):
    """Print IORegistry hardware info."""
    try:
        from pymobiledevice3.services.diagnostics import DiagnosticsService

        diag = DiagnosticsService(lockdown)
        ioreg = await diag.ioregistry()

        print("\n" + "=" * 60)
        print("  IO REGISTRY (Hardware)")
        print("=" * 60)

        if isinstance(ioreg, dict):
            _print_dict_recursive(ioreg, max_depth=2)
        else:
            print(f"  {ioreg}")

        print("=" * 60)
    except Exception as e:
        print(f"\n[!] Cannot get IORegistry info: {e}")


def _print_dict_recursive(d: dict, indent: int = 2, max_depth: int = 3, current_depth: int = 0):
    """Print a nested dict with indentation, limited depth."""
    if current_depth >= max_depth:
        return
    for key, value in d.items():
        prefix = " " * indent
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            _print_dict_recursive(value, indent + 2, max_depth, current_depth + 1)
        elif isinstance(value, (list, tuple)) and len(value) > 5:
            print(f"{prefix}{key}: [{len(value)} items]")
        elif isinstance(value, bytes):
            print(f"{prefix}{key}: <{len(value)} bytes>")
        else:
            print(f"{prefix}{key}: {value}")


async def cmd_info(args):
    """Command: show device + hardware info."""
    lockdown = await get_lockdown_client(args.udid)
    print_device_info(lockdown)
    await print_battery_info(lockdown)

    if args.ioregistry:
        await print_ioregistry_info(lockdown)


async def cmd_syslog(args):
    """Command: stream syslog and filter hardware entries."""
    lockdown = await get_lockdown_client(args.udid)

    # Parse category filter
    category_filter = None
    if args.categories:
        try:
            category_filter = {
                HardwareCategory(c.strip().lower())
                for c in args.categories.split(",")
            }
        except ValueError as e:
            print(f"[!] Invalid category: {e}")
            valid = ", ".join(c.value for c in HardwareCategory if c != HardwareCategory.UNKNOWN)
            print(f"    Valid categories: {valid}")
            sys.exit(1)

    # JSON output setup
    json_entries = []
    json_file = args.json if hasattr(args, "json") else None

    print(f"\n[*] Starting syslog stream...")
    if not args.all:
        print(f"[*] Filtering: hardware-related entries only")
        if category_filter:
            print(f"[*] Categories: {', '.join(c.value for c in category_filter)}")
    print(f"[*] Press Ctrl+C to stop\n")

    try:
        await _stream_os_trace(lockdown, args, category_filter, json_entries, json_file)
    except Exception as e:
        print(f"\n[!] OsTraceService error: {e}")
        print("[*] Trying legacy SyslogService...")
        try:
            await _stream_syslog_legacy(lockdown, args, category_filter, json_entries, json_file)
        except Exception as e2:
            print(f"[!] Legacy syslog also failed: {e2}")
            sys.exit(1)

    # Write JSON output
    if json_file and json_entries:
        with open(json_file, "w") as f:
            json.dump(json_entries, f, indent=2, default=str)
        print(f"\n[*] Saved {len(json_entries)} entries to {json_file}")


async def _stream_os_trace(lockdown, args, category_filter, json_entries, json_file):
    """Stream syslog via OsTraceService (iOS 10+)."""
    from pymobiledevice3.services.os_trace import OsTraceService

    service = OsTraceService(lockdown)

    async for entry in service.syslog():
        process_name = entry.image_name or ""
        message = entry.message or ""
        level = entry.level.name if entry.level else ""
        timestamp = entry.timestamp

        if args.all:
            print(f"[{timestamp}] {process_name}[{entry.pid}] <{level}>: {message}")
            continue

        parsed = parse_syslog_entry(
            timestamp=timestamp,
            process=process_name,
            pid=entry.pid,
            message=message,
            level=level,
        )

        if parsed is None:
            continue

        if category_filter and parsed.category not in category_filter:
            continue

        print(format_entry(parsed))

        if json_file:
            json_entries.append(entry_to_dict(parsed))


async def _stream_syslog_legacy(lockdown, args, category_filter, json_entries, json_file):
    """Stream syslog via legacy SyslogService."""
    from pymobiledevice3.services.syslog import SyslogService
    from syslog_parser import parse_raw_syslog_line

    syslog_service = SyslogService(lockdown)

    async for line in syslog_service.watch():
        if args.all:
            print(line)
            continue

        parsed = parse_raw_syslog_line(line)
        if parsed is None:
            continue

        if category_filter and parsed.category not in category_filter:
            continue

        print(format_entry(parsed))

        if json_file:
            json_entries.append(entry_to_dict(parsed))


def main():
    parser = argparse.ArgumentParser(
        description="iOS Hardware Monitor - Read syslog & extract hardware info"
    )
    parser.add_argument("-u", "--udid", help="Device UDID (auto-detect if omitted)")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # info command
    info_parser = subparsers.add_parser("info", help="Show device & hardware info")
    info_parser.add_argument("--ioregistry", action="store_true", help="Include IORegistry dump")
    info_parser.set_defaults(func=cmd_info)

    # syslog command
    syslog_parser = subparsers.add_parser("syslog", help="Stream & parse syslog")
    syslog_parser.add_argument("--all", action="store_true", help="Show ALL syslog (no filter)")
    syslog_parser.add_argument(
        "--categories",
        help="Comma-separated categories: thermal,battery,memory,wifi,bluetooth,cellular,sensor,display,storage,cpu,gps",
    )
    syslog_parser.add_argument("--json", help="Output JSON file path")
    syslog_parser.set_defaults(func=cmd_syslog)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
