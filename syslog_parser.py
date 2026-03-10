"""
Module parse/decode syslog entries từ iOS devices.
Trích xuất và phân loại thông tin hardware từ syslog messages.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class HardwareCategory(Enum):
    THERMAL = "thermal"
    BATTERY = "battery"
    MEMORY = "memory"
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    CELLULAR = "cellular"
    SENSOR = "sensor"
    DISPLAY = "display"
    STORAGE = "storage"
    CPU = "cpu"
    AUDIO = "audio"
    CAMERA = "camera"
    GPS = "gps"
    UNKNOWN = "unknown"


# Mapping process names -> hardware category
PROCESS_CATEGORY_MAP = {
    "thermalmonitor": HardwareCategory.THERMAL,
    "thermald": HardwareCategory.THERMAL,
    "powerd": HardwareCategory.BATTERY,
    "powerlogd": HardwareCategory.BATTERY,
    "BatteryCenter": HardwareCategory.BATTERY,
    "wifid": HardwareCategory.WIFI,
    "Wi-Fi": HardwareCategory.WIFI,
    "bluetoothd": HardwareCategory.BLUETOOTH,
    "BlueTool": HardwareCategory.BLUETOOTH,
    "CommCenter": HardwareCategory.CELLULAR,
    "basebandd": HardwareCategory.CELLULAR,
    "locationd": HardwareCategory.GPS,
    "mediaserverd": HardwareCategory.AUDIO,
    "coreduetd": HardwareCategory.SENSOR,
    "backboardd": HardwareCategory.DISPLAY,
    "iohid": HardwareCategory.SENSOR,
    "SpringBoard": HardwareCategory.DISPLAY,
    "kernel": HardwareCategory.CPU,
}

# Keyword patterns for hardware detection
KEYWORD_PATTERNS = {
    HardwareCategory.THERMAL: [
        re.compile(r"thermal", re.IGNORECASE),
        re.compile(r"temperature", re.IGNORECASE),
        re.compile(r"CLTM", re.IGNORECASE),
        re.compile(r"throttl", re.IGNORECASE),
        re.compile(r"overheat", re.IGNORECASE),
        re.compile(r"thermal\s*state.*(?:Nominal|Fair|Serious|Critical)", re.IGNORECASE),
    ],
    HardwareCategory.BATTERY: [
        re.compile(r"battery", re.IGNORECASE),
        re.compile(r"charging", re.IGNORECASE),
        re.compile(r"power\s*source", re.IGNORECASE),
        re.compile(r"low\s*battery", re.IGNORECASE),
        re.compile(r"battery\s*level", re.IGNORECASE),
        re.compile(r"charge\s*state", re.IGNORECASE),
    ],
    HardwareCategory.MEMORY: [
        re.compile(r"jetsam", re.IGNORECASE),
        re.compile(r"memory\s*pressure", re.IGNORECASE),
        re.compile(r"mem\s*warn", re.IGNORECASE),
        re.compile(r"low\s*memory", re.IGNORECASE),
        re.compile(r"memorystatus", re.IGNORECASE),
    ],
    HardwareCategory.WIFI: [
        re.compile(r"wi-?fi", re.IGNORECASE),
        re.compile(r"SSID", re.IGNORECASE),
        re.compile(r"802\.11", re.IGNORECASE),
        re.compile(r"wifi\s*(dis)?connect", re.IGNORECASE),
        re.compile(r"RSSI", re.IGNORECASE),
    ],
    HardwareCategory.BLUETOOTH: [
        re.compile(r"bluetooth", re.IGNORECASE),
        re.compile(r"BT\s*(dis)?connect", re.IGNORECASE),
        re.compile(r"CoreBluetooth", re.IGNORECASE),
    ],
    HardwareCategory.CELLULAR: [
        re.compile(r"cellular", re.IGNORECASE),
        re.compile(r"signal\s*strength", re.IGNORECASE),
        re.compile(r"carrier", re.IGNORECASE),
        re.compile(r"baseband", re.IGNORECASE),
        re.compile(r"radio\s*tech", re.IGNORECASE),
    ],
    HardwareCategory.SENSOR: [
        re.compile(r"accelerometer", re.IGNORECASE),
        re.compile(r"gyro(scope)?", re.IGNORECASE),
        re.compile(r"proximity", re.IGNORECASE),
        re.compile(r"ambient\s*light", re.IGNORECASE),
        re.compile(r"barometer", re.IGNORECASE),
        re.compile(r"magnetometer", re.IGNORECASE),
        re.compile(r"motion", re.IGNORECASE),
    ],
    HardwareCategory.DISPLAY: [
        re.compile(r"orientation\s*change", re.IGNORECASE),
        re.compile(r"brightness", re.IGNORECASE),
        re.compile(r"display\s*(on|off|sleep|wake)", re.IGNORECASE),
    ],
    HardwareCategory.STORAGE: [
        re.compile(r"NAND", re.IGNORECASE),
        re.compile(r"disk\s*space", re.IGNORECASE),
        re.compile(r"storage", re.IGNORECASE),
        re.compile(r"flash\s*storage", re.IGNORECASE),
    ],
    HardwareCategory.CPU: [
        re.compile(r"watchdog\s*timeout", re.IGNORECASE),
        re.compile(r"cpu\s*usage", re.IGNORECASE),
        re.compile(r"process\s*crash", re.IGNORECASE),
        re.compile(r"EXC_CRASH", re.IGNORECASE),
    ],
    HardwareCategory.GPS: [
        re.compile(r"GPS", re.IGNORECASE),
        re.compile(r"location\s*(fix|update|accuracy)", re.IGNORECASE),
        re.compile(r"CLLocation", re.IGNORECASE),
    ],
}


@dataclass
class ParsedHardwareEntry:
    """Parsed syslog entry with hardware classification."""
    timestamp: Optional[datetime]
    process: str
    pid: Optional[int]
    message: str
    category: HardwareCategory
    level: str = ""
    raw_line: str = ""
    extracted_values: dict = field(default_factory=dict)


def classify_by_process(process_name: str) -> Optional[HardwareCategory]:
    """Classify a syslog entry by process name."""
    for proc, category in PROCESS_CATEGORY_MAP.items():
        if proc.lower() in process_name.lower():
            return category
    return None


def classify_by_keywords(message: str) -> Optional[HardwareCategory]:
    """Classify a syslog entry by keyword patterns in the message."""
    for category, patterns in KEYWORD_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(message):
                return category
    return None


def extract_thermal_values(message: str) -> dict:
    """Extract thermal-related values from a syslog message."""
    values = {}
    # Temperature values (e.g., "temperature: 32.5")
    temp_match = re.search(r"temperature[:\s]+(\d+\.?\d*)", message, re.IGNORECASE)
    if temp_match:
        values["temperature_c"] = float(temp_match.group(1))

    # Thermal state
    state_match = re.search(r"thermal\s*state[:\s]*(Nominal|Fair|Serious|Critical)", message, re.IGNORECASE)
    if state_match:
        values["thermal_state"] = state_match.group(1)

    # Throttling level
    throttle_match = re.search(r"throttl\w*[:\s]+(\d+)", message, re.IGNORECASE)
    if throttle_match:
        values["throttle_level"] = int(throttle_match.group(1))

    return values


def extract_battery_values(message: str) -> dict:
    """Extract battery-related values from a syslog message."""
    values = {}
    # Battery level percentage
    level_match = re.search(r"(?:battery|level|capacity)[:\s]+(\d+)%?", message, re.IGNORECASE)
    if level_match:
        values["battery_level"] = int(level_match.group(1))

    # Charging state
    if re.search(r"charging", message, re.IGNORECASE):
        values["charging"] = True
    if re.search(r"not\s*charging|discharging", message, re.IGNORECASE):
        values["charging"] = False

    # Voltage
    volt_match = re.search(r"voltage[:\s]+(\d+\.?\d*)", message, re.IGNORECASE)
    if volt_match:
        values["voltage_mv"] = float(volt_match.group(1))

    return values


def extract_memory_values(message: str) -> dict:
    """Extract memory-related values from a syslog message."""
    values = {}
    # Memory pressure level
    pressure_match = re.search(r"pressure\s*level[:\s]*(\w+)", message, re.IGNORECASE)
    if pressure_match:
        values["pressure_level"] = pressure_match.group(1)

    # Jetsam - killed process
    jetsam_match = re.search(r"jetsam\w*.*?(\w+)\[(\d+)\]", message, re.IGNORECASE)
    if jetsam_match:
        values["jetsam_killed_process"] = jetsam_match.group(1)
        values["jetsam_killed_pid"] = int(jetsam_match.group(2))

    # Memory usage in MB/KB
    mem_match = re.search(r"(\d+\.?\d*)\s*(MB|KB|GB|bytes)", message, re.IGNORECASE)
    if mem_match:
        values["memory_amount"] = float(mem_match.group(1))
        values["memory_unit"] = mem_match.group(2).upper()

    return values


def extract_wifi_values(message: str) -> dict:
    """Extract WiFi-related values."""
    values = {}
    ssid_match = re.search(r'SSID[:\s]+"?([^"\s]+)"?', message, re.IGNORECASE)
    if ssid_match:
        values["ssid"] = ssid_match.group(1)

    rssi_match = re.search(r"RSSI[:\s]+(-?\d+)", message, re.IGNORECASE)
    if rssi_match:
        values["rssi_dbm"] = int(rssi_match.group(1))

    return values


VALUE_EXTRACTORS = {
    HardwareCategory.THERMAL: extract_thermal_values,
    HardwareCategory.BATTERY: extract_battery_values,
    HardwareCategory.MEMORY: extract_memory_values,
    HardwareCategory.WIFI: extract_wifi_values,
}


def parse_syslog_entry(
    *,
    timestamp: Optional[datetime] = None,
    process: str = "",
    pid: Optional[int] = None,
    message: str = "",
    level: str = "",
    raw_line: str = "",
) -> Optional[ParsedHardwareEntry]:
    """
    Parse a syslog entry and classify it as hardware-related.
    Returns None if the entry is not hardware-related.
    """
    category = classify_by_process(process)
    if category is None:
        category = classify_by_keywords(message)
    if category is None:
        return None

    extracted = {}
    extractor = VALUE_EXTRACTORS.get(category)
    if extractor:
        extracted = extractor(message)

    return ParsedHardwareEntry(
        timestamp=timestamp,
        process=process,
        pid=pid,
        message=message,
        category=category,
        level=level,
        raw_line=raw_line,
        extracted_values=extracted,
    )


# Pattern for parsing raw syslog lines from idevicesyslog CLI output
# Format: "Mon DD HH:MM:SS hostname process[pid] <level>: message"
IDEVICESYSLOG_PATTERN = re.compile(
    r"(?P<timestamp>\w{3}\s+\d+\s+[\d:]+)\s+"
    r"(?P<hostname>\S+)\s+"
    r"(?P<process>[^\[]+)\[(?P<pid>\d+)\]\s*"
    r"(?:<(?P<level>\w+)>:\s*)?"
    r"(?P<message>.*)"
)


def parse_raw_syslog_line(line: str) -> Optional[ParsedHardwareEntry]:
    """Parse a raw syslog line from idevicesyslog CLI output."""
    match = IDEVICESYSLOG_PATTERN.match(line.strip())
    if not match:
        return None

    groups = match.groupdict()
    try:
        ts = datetime.strptime(groups["timestamp"], "%b %d %H:%M:%S")
        ts = ts.replace(year=datetime.now().year)
    except ValueError:
        ts = None

    return parse_syslog_entry(
        timestamp=ts,
        process=groups["process"].strip(),
        pid=int(groups["pid"]),
        message=groups["message"],
        level=groups.get("level", ""),
        raw_line=line.strip(),
    )


def format_entry(entry: ParsedHardwareEntry) -> str:
    """Format a parsed entry for display."""
    ts_str = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else "??:??:??"
    parts = [
        f"[{ts_str}]",
        f"[{entry.category.value.upper():10s}]",
        f"{entry.process}",
    ]
    if entry.pid:
        parts.append(f"[{entry.pid}]")
    parts.append(f": {entry.message}")

    if entry.extracted_values:
        vals = ", ".join(f"{k}={v}" for k, v in entry.extracted_values.items())
        parts.append(f"\n  >> Extracted: {vals}")

    return " ".join(parts)


def entry_to_dict(entry: ParsedHardwareEntry) -> dict:
    """Convert a ParsedHardwareEntry to a JSON-serializable dict."""
    return {
        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        "process": entry.process,
        "pid": entry.pid,
        "message": entry.message,
        "category": entry.category.value,
        "level": entry.level,
        "extracted_values": entry.extracted_values,
    }
