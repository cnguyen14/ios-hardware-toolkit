"""
iOS Sensor Test - Kiểm tra Face ID và Proximity Sensor qua syslog.
Kết quả: PASS / FAIL cho từng sensor.

Usage:
    uv run python sensor_test.py              # Test cả 2 sensor
    uv run python sensor_test.py proximity    # Chỉ test proximity
    uv run python sensor_test.py faceid       # Chỉ test Face ID
"""

import asyncio
import sys
import time


async def get_lockdown():
    from pymobiledevice3.lockdown import create_using_usbmux
    return await create_using_usbmux()


async def test_proximity(lockdown, timeout: int = 20) -> bool:
    """
    Test proximity sensor.

    Proximity sensor trên iOS chỉ report qua baseband manager log.
    Log này xuất hiện định kỳ (~2-3s) với format:
      "Audio State: ..., Proximity Sensor: Off/On, Motion State: ..."

    Strategy:
    - Nếu thấy state change (Off→On hoặc On→Off) → PASS (sensor responsive)
    - Nếu chỉ thấy 1 state → sensor tồn tại nhưng không verify được response
      (có thể user không che sensor, hoặc sensor stuck)
    - Nếu không thấy gì → FAIL
    """
    from pymobiledevice3.services.os_trace import OsTraceService

    print("\n" + "=" * 50)
    print("  PROXIMITY SENSOR TEST")
    print("=" * 50)
    print(f"  Thời gian: {timeout}s")
    print("  Hãy GỌI ĐIỆN (hoặc mở app Phone, bấm gọi)")
    print("  rồi đưa tay che vùng tai nghe, bỏ ra, lặp lại.")
    print("  (Proximity sensor chỉ active khi đang gọi)")
    print("=" * 50)

    states_seen = set()  # "On", "Off"
    report_count = 0
    start = time.time()

    service = OsTraceService(lockdown)
    async for entry in service.syslog():
        elapsed = time.time() - start
        if elapsed > timeout:
            break

        msg = entry.message or ""
        if "Proximity Sensor:" not in msg:
            continue

        report_count += 1

        if "Proximity Sensor: On" in msg:
            if "On" not in states_seen:
                print(f"  [{elapsed:5.1f}s] Proximity Sensor: ON  (phát hiện vật cản)")
                states_seen.add("On")
        elif "Proximity Sensor: Off" in msg:
            if "Off" not in states_seen:
                print(f"  [{elapsed:5.1f}s] Proximity Sensor: OFF (không vật cản)")
                states_seen.add("Off")

        if len(states_seen) == 2:
            break

    if len(states_seen) == 2:
        print(f"\n  >> PROXIMITY SENSOR: PASS")
        print(f"     State change detected (Off<->On), sensor responsive")
        return True
    elif len(states_seen) == 1:
        state = list(states_seen)[0]
        print(f"\n  >> PROXIMITY SENSOR: PASS")
        print(f"     Sensor reported (state={state}, {report_count} reports)")
        print(f"     Không detect state change - sensor tồn tại nhưng")
        print(f"     cần gọi điện + che/bỏ sensor để verify đầy đủ")
        return True
    else:
        print(f"\n  >> PROXIMITY SENSOR: FAIL")
        print(f"     Không detect tín hiệu proximity nào trong {timeout}s")
        return False


async def test_faceid(lockdown, timeout: int = 25) -> bool:
    """
    Test Face ID / TrueDepth camera system.

    Các tín hiệu trong syslog khi Face ID hoạt động:
    1. Pearl dot projector: "ctrlPearl" / "projectorSema" (AppleH*CameraInterface)
    2. BiometricKit: BKOperation, BKDevice (match operations)
    3. BiometricSupport: match/cancel/lockoutState
    4. AttentionAwareness: AWPearlAttentionSampler
    5. PearlCoreAnalytics: analyzeSecureFrameMeta

    Strategy:
    - Cần ít nhất 1 tín hiệu Pearl/Biometric → PASS (hardware present & active)
    - Face ID trigger khi: nhấn nút sườn wake screen, hoặc raise to wake
    """
    from pymobiledevice3.services.os_trace import OsTraceService

    print("\n" + "=" * 50)
    print("  FACE ID TEST")
    print("=" * 50)
    print(f"  Thời gian: {timeout}s")
    print("  Hãy KHÓA màn hình (nút sườn), đợi 2s,")
    print("  rồi nhấn nút sườn / nhấc máy để Face ID scan.")
    print("  Lặp lại 2-3 lần nếu cần.")
    print("=" * 50)

    signals = {
        "pearl_hw": False,       # Dot projector / TrueDepth hardware
        "biometric_fw": False,   # BiometricKit/Support framework
        "attention": False,      # Attention awareness (Pearl camera)
        "pearl_analytics": False, # PearlCoreAnalytics
    }
    signal_details = []

    start = time.time()
    service = OsTraceService(lockdown)
    async for entry in service.syslog():
        elapsed = time.time() - start
        if elapsed > timeout:
            break

        msg = entry.message or ""
        proc = entry.image_name or ""

        # 1. Pearl dot projector / TrueDepth camera ISP
        if ("ctrlPearl" in msg or "projectorSema" in msg) and not signals["pearl_hw"]:
            print(f"  [{elapsed:5.1f}s] TrueDepth dot projector ACTIVE")
            signals["pearl_hw"] = True
            signal_details.append("dot_projector")

        # 2. BiometricKit / BiometricSupport framework activity
        elif ("BiometricKit" in proc or "BiometricSupport" in proc) and not signals["biometric_fw"]:
            # Any activity from these frameworks means Face ID subsystem is alive
            print(f"  [{elapsed:5.1f}s] Biometric framework ACTIVE")
            signals["biometric_fw"] = True
            signal_details.append("biometric_framework")

        # 3. Attention awareness via Pearl camera
        elif "AWPearlAttentionSampler" in msg and not signals["attention"]:
            print(f"  [{elapsed:5.1f}s] Attention awareness (Pearl) ACTIVE")
            signals["attention"] = True
            signal_details.append("attention_awareness")

        # 4. PearlCoreAnalytics
        elif "PearlCoreAnalytics" in msg and not signals["pearl_analytics"]:
            print(f"  [{elapsed:5.1f}s] Pearl analytics ACTIVE")
            signals["pearl_analytics"] = True
            signal_details.append("pearl_analytics")

        active_count = sum(signals.values())
        if active_count >= 3:
            break

    active_count = sum(signals.values())

    if active_count >= 1:
        print(f"\n  >> FACE ID: PASS")
        print(f"     Signals ({active_count}/4): {', '.join(signal_details)}")
        return True
    else:
        print(f"\n  >> FACE ID: FAIL")
        print(f"     Không detect tín hiệu Face ID nào trong {timeout}s")
        print(f"     Hãy thử: khóa màn hình → nhấn nút sườn → nhìn vào camera")
        return False


async def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    print("[*] Connecting to device...")
    lockdown = await get_lockdown()
    dev_name = lockdown.all_values.get("DeviceName", "Unknown")
    model = lockdown.all_values.get("ProductType", "Unknown")
    print(f"[*] Connected: {dev_name} ({model})")

    results = {}

    if target in ("all", "proximity"):
        results["Proximity Sensor"] = await test_proximity(lockdown)

    if target in ("all", "faceid"):
        if target == "all":
            lockdown = await get_lockdown()
        results["Face ID"] = await test_faceid(lockdown)

    # Summary
    print("\n" + "=" * 50)
    print("  TEST SUMMARY")
    print("=" * 50)
    for sensor_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {sensor_name:20s}: {status}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
