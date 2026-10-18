"""GPU-temperature control for the confirmed T10 CHA_FAN on this B85M-G.

Only pwm1 is controlled. CPU fan pwm2 and existing BIOS curves are preserved.
systemd watchdog restarts a stalled controller; ExecStopPost restores firmware mode.
"""
import ctypes as C
import json
import os
from pathlib import Path
import signal
import socket
import sys
import time

GPU_UUID = b"GPU-8cfbc08d-0090-bc29-db9a-b2a2f7261ca5"
STATE = Path('/var/lib/t10-quiet-fan/original.json')
CURVE = [(45, 115), (55, 125), (65, 145), (72, 170), (78, 210), (82, 255)]


def hardware():
    assert Path('/sys/class/dmi/id/board_name').read_text().strip() == 'B85M-G'
    root = next(p for p in Path('/sys/class/hwmon').glob('hwmon*')
                if (p / 'name').read_text().strip() == 'nct6791')
    assert (root / 'pwm1_temp_sel').read_text().strip() == '2'
    assert (root / 'pwm2_temp_sel').read_text().strip() == '7'
    return root


def notify(message):
    address = os.environ.get('NOTIFY_SOCKET')
    if not address:
        return
    if address.startswith('@'):
        address = '\0' + address[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
        sock.sendto(message.encode(), address)


def nvml():
    lib = C.CDLL('libnvidia-ml.so.1')
    definitions = {
        'nvmlInit_v2': [], 'nvmlShutdown': [],
        'nvmlDeviceGetHandleByUUID': [C.c_char_p, C.POINTER(C.c_void_p)],
        'nvmlDeviceGetTemperature': [C.c_void_p, C.c_uint, C.POINTER(C.c_uint)],
        'nvmlDeviceGetPowerManagementLimit': [C.c_void_p, C.POINTER(C.c_uint)],
        'nvmlDeviceSetPowerManagementLimit': [C.c_void_p, C.c_uint],
    }
    for name, args in definitions.items():
        function = getattr(lib, name)
        function.argtypes, function.restype = args, C.c_int
    check(lib.nvmlInit_v2())
    dev = C.c_void_p()
    check(lib.nvmlDeviceGetHandleByUUID(GPU_UUID, C.byref(dev)))
    return lib, dev


def check(value):
    if value:
        raise RuntimeError(f'NVML error {value}')


def duty(temp):
    if temp <= CURVE[0][0]:
        return CURVE[0][1]
    for (t0, p0), (t1, p1) in zip(CURVE, CURVE[1:]):
        if temp <= t1:
            return round(p0 + (p1 - p0) * (temp - t0) / (t1 - t0))
    return 255


def restore():
    if not STATE.exists():
        return
    root = hardware()
    state = json.loads(STATE.read_text())
    failed = os.environ.get('SERVICE_RESULT', 'success') != 'success'
    if failed:
        # Continue airflow during a failed restart. Do not depend on NVML here.
        (root / 'pwm1').write_text('255')
        (root / 'pwm1_enable').write_text('1')
        print('Failed controller: CHA_FAN left at full duty until restart', flush=True)
    else:
        (root / 'pwm1_enable').write_text(str(state['pwm1_enable']))
        print('Restored CHA_FAN firmware automatic mode', flush=True)


def main():
    root = hardware()
    STATE.parent.mkdir(mode=0o755, exist_ok=True)
    if not STATE.exists():
        state = {k: int((root / k).read_text()) for k in
                 ['pwm1_enable', 'pwm1', 'pwm1_mode', 'pwm1_temp_sel',
                  'pwm2_enable', 'pwm2', 'pwm2_mode', 'pwm2_temp_sel']}
        assert state['pwm1_enable'] == 5 and state['pwm2_enable'] == 5
        STATE.write_text(json.dumps(state, indent=2))
        STATE.chmod(0o644)
    lib, dev = nvml()
    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    current = int((root / 'pwm1').read_text())
    (root / 'pwm1_enable').write_text('1')
    notify('READY=1')
    last = time.monotonic()
    last_down = last
    low_rpm_count = 0
    derated = False
    try:
        while running:
            raw = C.c_uint()
            check(lib.nvmlDeviceGetTemperature(dev, 0, C.byref(raw)))
            temp = raw.value
            assert 0 < temp < 110
            rpm = int((root / 'fan1_input').read_text())
            low_rpm_count = low_rpm_count + 1 if rpm < 500 else 0
            desired = duty(temp)
            if temp >= 80 or low_rpm_count >= 3:
                desired = 255
                check(lib.nvmlDeviceSetPowerManagementLimit(dev, 100000))
                if not derated:
                    print(f'Protection: temp={temp} rpm={rpm}; fan full and cap 100 W', flush=True)
                derated = True
            elif derated and temp <= 70 and rpm >= 1000:
                check(lib.nvmlDeviceSetPowerManagementLimit(dev, 100000))
                derated = False
                print('Protection recovered; fixed cap 100 W retained', flush=True)
            now = time.monotonic()
            if desired > current:
                current = desired
            elif desired < current and now - last_down >= 5:
                current = max(desired, current - 5)
                last_down = now
            current = max(115, min(255, current))
            (root / 'pwm1').write_text(str(current))
            notify(f'WATCHDOG=1\nSTATUS=GPU {temp} C; CHA_FAN {rpm} RPM; duty {current}/255; protection {derated}')
            if now - last >= 15:
                print(json.dumps({'gpu_temp_c': temp, 'cha_fan_rpm': rpm, 'pwm': current,
                                  'power_protection': derated}), flush=True)
                last = now
            time.sleep(1)
    except BaseException:
        (root / 'pwm1').write_text('255')
        try:
            lib.nvmlDeviceSetPowerManagementLimit(dev, 100000)
        except Exception:
            pass
        raise
    finally:
        lib.nvmlShutdown()


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--restore':
        restore()
    else:
        main()
