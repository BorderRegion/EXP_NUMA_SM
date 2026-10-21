#!/usr/bin/env python3
"""Offline, read-only preflight. No allocation, kernel, network, or process inspection."""
import argparse
import ctypes
import ctypes.util
import datetime as dt
import glob
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time


SYMBOLS = [
    "CU_DEVICE_ATTRIBUTE_LOCALITY_DOMAIN_COUNT",
    "CU_MEM_LOCATION_TYPE_DEVICE_LOCALITY_DOMAIN",
    "cuGreenCtxCreate", "cuDevSmResourceSplitByCount",
]
RESOURCE_GLOBS = ["*.cu", "*.ply", "*.splat", "*.pt", "*.pth",
                  "SOURCES_AND_SCOPE.md", "cuda_runtime.h", "nvcc"]


def command(argv):
    started = time.monotonic()
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=20)
        return {"argv": argv, "returncode": p.returncode,
                "stdout": p.stdout, "stderr": p.stderr,
                "wall_seconds": time.monotonic() - started}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"argv": argv, "error": str(e),
                "wall_seconds": time.monotonic() - started}


def driver_query():
    result = {"library": ctypes.util.find_library("cuda"),
              "allocation_or_kernel_executed": False}
    if not result["library"]:
        return result
    try:
        lib = ctypes.CDLL(result["library"])
        lib.cuDriverGetVersion.argtypes = [ctypes.POINTER(ctypes.c_int)]
        lib.cuInit.argtypes = [ctypes.c_uint]
        lib.cuGetErrorName.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
        version = ctypes.c_int()
        result["version_query_status"] = lib.cuDriverGetVersion(ctypes.byref(version))
        result["version_integer"] = version.value
        status = lib.cuInit(0)
        name = ctypes.c_char_p()
        lib.cuGetErrorName(status, ctypes.byref(name))
        result["init_status"] = status
        result["init_name"] = name.value.decode() if name.value else None
        if status != 0:
            return result
        lib.cuDeviceGetCount.argtypes = [ctypes.POINTER(ctypes.c_int)]
        lib.cuDeviceGet.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        lib.cuDeviceGetName.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
        lib.cuDeviceComputeCapability.argtypes = [ctypes.POINTER(ctypes.c_int),
                                                ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        total_mem = lib.cuDeviceTotalMem_v2
        total_mem.argtypes = [ctypes.POINTER(ctypes.c_size_t), ctypes.c_int]
        count = ctypes.c_int()
        result["count_status"] = lib.cuDeviceGetCount(ctypes.byref(count))
        result["devices"] = []
        for i in range(count.value):
            device = ctypes.c_int()
            get_status = lib.cuDeviceGet(ctypes.byref(device), i)
            if get_status:
                result["devices"].append({"ordinal": i, "get_status": get_status})
                continue
            buffer = ctypes.create_string_buffer(256)
            major, minor, size = ctypes.c_int(), ctypes.c_int(), ctypes.c_size_t()
            statuses = {
                "name": lib.cuDeviceGetName(buffer, 256, device.value),
                "compute_capability": lib.cuDeviceComputeCapability(
                    ctypes.byref(major), ctypes.byref(minor), device.value),
                "total_mem": total_mem(ctypes.byref(size), device.value),
            }
            result["devices"].append({"ordinal": i, "name": buffer.value.decode(),
                                       "compute_capability": [major.value, minor.value],
                                       "total_mem_bytes": size.value, "statuses": statuses})
        # No numerical CUdevice_attribute constants without official local CUDA headers.
        result["sm_count"] = None
        result["l2_bytes"] = None
        result["locality_domain_count"] = None
    except (OSError, AttributeError) as e:
        result["error"] = str(e)
    return result


def collect():
    started = time.monotonic()
    tool_names = ["nvidia-smi", "nvcc", "ptxas", "cuobjdump", "nvdisasm",
                  "nsys", "ncu", "vulkaninfo", "cmake", "ninja", "gcc", "g++", "python3"]
    paths = {name: shutil.which(name) for name in tool_names}
    result = {"schema_version": 1, "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
              "user_timezone": "Asia/Shanghai", "hostname": platform.node(),
              "platform": platform.platform(), "python": platform.python_version(),
              "tools": paths, "cuda_env": {k: os.environ.get(k) for k in ["CUDA_HOME", "CUDA_PATH"]},
              "gpu_device_nodes": glob.glob("/dev/nvidia*"),
              "dri_nodes": glob.glob("/dev/dri/*"), "network_used": False}
    result["os_release"] = Path("/etc/os-release").read_text()
    driver = Path("/proc/driver/nvidia/version")
    result["kernel_driver"] = driver.read_text() if driver.exists() else None
    result["proc_gpu_information"] = {
        str(p): p.read_text() for p in Path("/proc/driver/nvidia/gpus").glob("*/information")}
    result["driver_query"] = driver_query()
    # Query only device-level metrics. Deliberately omit other processes and their command lines.
    if paths["nvidia-smi"]:
        result["gpu_metrics"] = command([
            paths["nvidia-smi"],
            "--query-gpu=name,uuid,driver_version,memory.total,memory.free,memory.used,"
            "utilization.gpu,utilization.memory,temperature.gpu,display_active,compute_mode",
            "--format=csv,noheader,nounits"])
    result["compiler_version"] = command([paths["nvcc"], "--version"]) if paths["nvcc"] else None
    # Only search user project/data roots and conventional toolchain directories.
    roots = ["/home/ws/work", "/home/ws/文档/ChatGPT", "/home/ws/下载",
             "/home/ws/公共", "/usr/local", "/opt", "/usr/include",
             "/usr/lib/nvidia-cuda-toolkit", "/usr/lib/cuda", "/usr/share/doc"]
    existing = [p for p in roots if Path(p).is_dir()]
    args = ["rg", "--files", "--hidden", *existing,
            "-g", "!.git", "-g", "!node_modules", "-g", "!__pycache__",
            "-g", "!site-packages", "-g", "!.codex", "-g", "!.agents", "-g", "!.aws"]
    for pattern in RESOURCE_GLOBS:
        args += ["-g", pattern]
    discovered = command(args)
    result["resource_search"] = {"roots": roots, "existing_roots": existing, **discovered}
    # NVIDIA CUDA headers; /usr/include/linux/cuda.h is an unrelated Apple microcontroller ABI.
    header_candidates = [Path("/usr/include/cuda.h"),
                         Path("/usr/lib/nvidia-cuda-toolkit/include/cuda.h")]
    header_candidates += [Path(p) for p in glob.glob("/usr/local/cuda*/include/cuda.h")]
    header_candidates += [Path(p) for p in glob.glob("/opt/cuda*/include/cuda.h")]
    header_candidates += [Path(p) for p in glob.glob("/usr/local/cuda*/targets/*/include/cuda.h")]
    result["official_header_checks"] = {}
    for p in header_candidates:
        if p.is_file():
            content = p.read_text(errors="replace")
            result["official_header_checks"][str(p)] = {
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "symbols_present": {s: s in content for s in SYMBOLS}}
    result["wall_seconds"] = time.monotonic() - started
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = collect()
    data = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as out:
            out.write(data)
        print(json.dumps({"output": str(args.output), "driver": result["driver_query"],
                          "tools": result["tools"], "wall_seconds": result["wall_seconds"]},
                         ensure_ascii=False))
    else:
        print(data)


if __name__ == "__main__":
    main()
