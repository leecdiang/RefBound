"""Run one local C1/C4 qualification pair. Outputs contain private payloads."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from trace_review import identity, need, read, trace, write


PACKAGE = Path(__file__).resolve().parents[1]
GIB = 1024 ** 3
DISK_CAP = 18 * GIB
DISK_RESERVE = 8 * GIB
WORKER_SECONDS = 220
MAX_TEMPERATURE_C = 84
MAX_VRAM_MIB = 12288


def prompt_ids(path, expected):
    ids = read(path)
    need(isinstance(ids, list) and len(ids) == expected["tokens"] and
         all(type(x) is int and 0 <= x < 128256 for x in ids), "fixed input shape")
    packed = json.dumps(ids, separators=(",", ":")).encode("ascii")
    need(hashlib.sha256(packed).hexdigest() == expected["sha256"], "fixed input SHA256")
    return ids


def smi(*arguments):
    return subprocess.check_output(["nvidia-smi", *arguments, "--format=csv,noheader,nounits"],
                                   text=True, timeout=10).strip()


def quiet(expected):
    name, driver, memory, utilization, temperature, recovery = gpu_fields(
        "name,driver_version,memory.free,utilization.gpu,temperature.gpu,gpu_recovery_action")
    need(name.removeprefix("NVIDIA ") == expected["hardware"] and driver == expected["driver"],
         "qualified GPU and driver")
    need(recovery == "None" and 0 < float(temperature) <= MAX_TEMPERATURE_C, "GPU recovery or temperature gate")
    need(int(memory) >= 10752 and int(utilization) == 0, "idle device with at least 10.5 GiB free VRAM")
    need(not smi("--query-compute-apps=pid"), "no external or unobservable CUDA compute processes")


def gpu_fields(fields):
    devices = list(csv.reader(smi("--query-gpu=" + fields).splitlines(), skipinitialspace=True))
    need(len(devices) == 1 and len(devices[0]) == len(fields.split(",")), "one independently visible NVIDIA GPU")
    return devices[0]


def env_for(expected, arm, cuda_bin):
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith(("HS_", "GGML_", "CUDA_"))}
    env.update(expected["shared_environment"])
    env["HS_SD_TARGET_PACK4"] = expected["C4_flag_values"][arm]
    env["CUDA_VISIBLE_DEVICES"] = "0"
    env["PATH"] = str(cuda_bin) + os.pathsep + env["PATH"]
    return env


def run_arm(args, expected, arm, ids, initial_free):
    case = args.out / arm
    request = case / "request"
    request.mkdir(parents=True)
    run_id = args.out.name + "-" + arm
    spec = {"request_id": run_id, "request_dir": str(request), "arm": "SD_C",
            "stage": "qualification", "capture": True, "k_max": 3, "prompt_ids": ids,
            "prompt_ids_sha256": expected["input"]["sha256"]}
    with (case / "request-input.local.jsonl").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(spec) + "\n")
        stream.write('{"command":"stop"}\n')
    command = [args.capture_bin / "rtx-c4-worker.exe", args.target, args.draft,
               case / "native.jsonl", case / "objects", "BC"]
    readings = {"samples": 0, "owned_pid_observed": False, "peak_used_mib": 0, "peak_temperature_c": 0.0}
    started = time.monotonic()
    with (case / "request-input.local.jsonl").open("rb") as stdin, \
            (case / "stdout.jsonl").open("xb") as stdout, (case / "stderr.log").open("xb") as stderr:
        process = subprocess.Popen(command, cwd=args.capture_bin, stdin=stdin, stdout=stdout, stderr=stderr,
                                   env=env_for(expected, arm, args.cuda_bin))
        deadline = time.monotonic() + WORKER_SECONDS
        try:
            while process.poll() is None:
                remaining = shutil.disk_usage(args.out).free
                need(remaining >= DISK_RESERVE and initial_free - remaining < DISK_CAP, "disk stop limit")
                need(time.monotonic() < deadline, "worker time limit")
                owned_or_empty = smi("--query-compute-apps=pid").splitlines()
                need(all(pid == str(process.pid) for pid in owned_or_empty), "external or unobservable compute process")
                used, temperature, recovery = gpu_fields("memory.used,temperature.gpu,gpu_recovery_action")
                used, temperature = int(used), float(temperature)
                need(recovery == "None" and 0 <= used <= MAX_VRAM_MIB and 0 < temperature <= MAX_TEMPERATURE_C,
                     "GPU recovery, memory or temperature stop limit")
                readings["samples"] += 1
                readings["owned_pid_observed"] |= bool(owned_or_empty)
                readings["peak_used_mib"] = max(readings["peak_used_mib"], used)
                readings["peak_temperature_c"] = max(readings["peak_temperature_c"], temperature)
                time.sleep(1)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=15)
            readings["owned_seconds"] = round(time.monotonic() - started, 3)
            readings["returncode"] = process.returncode
            write(case / "DEVICE_RESOURCES.json", readings)
        need(process.returncode == 0, f"{arm} worker failed. See the local logs.")
    need(readings["owned_pid_observed"], f"{arm} owned worker absent from all compute process samples")
    native = read(request / "native.json")
    for key, value in expected["dispatch"][arm].items():
        need(native[key] == value, f"{arm} dispatch mismatch: {key}")
    need(identity(request / "vectors.f32") == expected["references"]["SD_U"]["vectors.f32"],
         f"{arm} frozen F32 payload mismatch")
    result = trace(case, arm, run_id, case / "MAPPED_ACTIVITY.jsonl")
    write(case / "TRACE_REVIEW.json", result)
    need(result["status"] == "PASS", f"{arm} capture association")
    return run_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("capture-bin", "cuda-bin", "input", "target", "draft", "out", "lock"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--exclusive-window", action="store_true", required=True,
                        help="Confirm the device and output volume are reserved for this pair.")
    args = parser.parse_args()
    for name, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, name, value.resolve())
    expected = read(PACKAGE / "records" / "expected.json")
    need(os.name == "nt" and args.out.name.isascii() and args.out.name.replace("-", "").isalnum(),
         "Windows and a fresh alphanumeric run ID (hyphens allowed)")
    need(not args.out.exists() and args.out.parent.is_dir(), "fresh run directory")
    need(args.lock.parent.is_dir() and not args.lock.is_relative_to(args.out), "lock outside the output")
    ids = prompt_ids(args.input, expected["input"])
    for role in ("target", "draft"):
        model = expected["models"][role]
        need(identity(getattr(args, role)) == {key: model[key] for key in ("bytes", "sha256")},
             f"{role} model identity")
    binaries = {name: identity(args.capture_bin / name) for name in expected["observed_capture_binaries"]}
    cupti = args.capture_bin / "cupti64_2025.2.1.dll"
    need(identity(cupti) == expected["observed_cupti_library"], "pinned CUPTI runtime")
    with args.lock.open("x", encoding="ascii") as lock:
        lock.write(str(os.getpid()))
    try:
        free = shutil.disk_usage(args.out.parent).free
        need(free >= DISK_CAP + DISK_RESERVE, "26 GiB free on the output volume")
        args.out.mkdir()
        write(args.out / "BUILD_IDENTITIES.json", {"worker_and_backend": binaries, "CUPTI": identity(cupti)})
        ids_by_arm = {}
        for arm in ("C1", "C4"):
            for _ in range(3):
                quiet(expected)
                time.sleep(1)
            ids_by_arm[arm] = run_arm(args, expected, arm, ids, free)
        write(args.out / "DEVICE_FREEZE.json", {"new_ids": ids_by_arm})
        quiet(expected)
    finally:
        if args.lock.read_text(encoding="ascii") == str(os.getpid()):
            args.lock.unlink()
    print("Captured one local pair. Run verify_capture.py to check the numerical objects.")


if __name__ == "__main__":
    main()
