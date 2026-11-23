"""Run only the two model-free modes of the linked Windows worker."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def identity(path):
    with path.open("rb") as stream:
        return {"sha256": hashlib.file_digest(stream, "sha256").hexdigest(), "bytes": path.stat().st_size}


def run(argv, cwd, log, env=None):
    process = subprocess.run([str(x) for x in argv], cwd=cwd, env=env, capture_output=True, timeout=120)
    log.with_suffix(".stdout.log").write_bytes(process.stdout)
    log.with_suffix(".stderr.log").write_bytes(process.stderr)
    require(process.returncode == 0, f"{log.name} returned {process.returncode}")
    return process.stdout.decode("utf-8", errors="replace")


def packed_state():
    # Two active positions arrive in reverse order. V is transposed.
    raw = struct.pack("<IiII", 0xaf143cd8, 0, 1, 2)
    raw += struct.pack("<iIiiIi", 1, 1, 0, 0, 1, 0) + struct.pack("<IIII", 1, 1, 0, 0)
    raw += struct.pack("<iQ2e", 1, 2, 2.0, 1.0) + struct.pack("<iII4e", 1, 2, 2, 4.0, 3.0, 6.0, 5.0)
    expected = b"HSSDKV1\x00" + struct.pack("<IiiiiIIII", 2, 7, 2, 0, 1, 1, 1, 0, 0)
    expected += struct.pack("<iQ2e", 1, 2, 1.0, 2.0) + struct.pack("<iII4e", 1, 2, 2, 3.0, 4.0, 5.0, 6.0)
    return raw, expected


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--build", type=Path, required=True)
    p.add_argument("--dumpbin", type=Path, required=True)
    p.add_argument("--cuobjdump", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    source = args.build.resolve()
    out = args.out.resolve()
    dump, cuda = args.dumpbin.resolve(), args.cuobjdump.resolve()
    out.mkdir()
    bindir = source / "bin"
    worker = bindir / "rtx-c4-worker.exe"
    library_names = ("llama.dll", "ggml.dll", "ggml-base.dll", "ggml-cpu.dll", "ggml-cuda.dll")
    built = [worker, *(bindir / name for name in library_names)]
    require(all(x.is_file() for x in built), "expected linked worker and all five DLLs")
    output = run([cuda, "--list-elf", bindir / "ggml-cuda.dll"], out, out / "cuda-elf")
    slices = re.findall(r"^ELF file\s+\d+:\s*(\S+)", output, re.M)
    require(slices and all(x.endswith(".sm_120a.cubin") for x in slices), "SM120a real ELF cubins")
    symbol_output = run([cuda, "--dump-elf-symbols", "--gpu-architecture", "sm_120a", bindir / "ggml-cuda.dll"],
                        out, out / "cuda-symbols")
    kernels = sorted(set(int(x) for x in re.findall(r"STO_ENTRY\s+_Z13mul_mat_vec_qIL9ggml_type8ELi([234])E", symbol_output)))
    require(kernels == [2, 3, 4], "expected native Q8_0 q2/q3/q4 entry points")
    native_exports = {
        "ggml-cuda.dll": ("hs248_set_arm", "hs_sd_pack4_audit"),
        "llama.dll": ("hs_sd_graph_audit", "hs_sd_native_draft_capability"),
    }
    for dll, names in native_exports.items():
        exports = run([dump, "/exports", bindir / dll], out, out / (Path(dll).stem + "-exports"))
        require(all(re.search(rf"\b{name}\b", exports) for name in names), f"native exports in {dll}")
    dependencies = {}
    system = Path(os.environ["SystemRoot"]) / "System32"
    lookup = [bindir, system, *(Path(s) for s in os.environ.get("PATH", "").split(os.pathsep) if s)]
    for artifact in built:
        text = run([dump, "/dependents", artifact], out, out / (artifact.stem + "-deps"))
        names = sorted(set(v.lower() for v in re.findall(r"^\s+([\w.+-]+\.dll)\s*$", text, re.M | re.I)))
        per_module = {}
        for name in names:
            if name.startswith(("api-ms-win-", "ext-ms-win-")):
                per_module[name] = {"resolution": "Windows API set"}
            else:
                path = next((x / name for x in lookup if (x / name).is_file()), None)
                require(path is not None, f"unresolved runtime import {artifact.name}: {name}")
                per_module[name] = {"resolution": "output" if path.parent == bindir else "system/toolchain",
                                    **identity(path)}
        dependencies[artifact.name] = per_module
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "-1"
    env["HS_PREFILL_PACK4"] = "0"
    fixture = json.loads(run([worker, "--fixtures"], out, out / "worker-fixtures", env))
    require(fixture["event"] == "CPU_FIXTURES_PASS" and fixture["cases"] == 20, "native worker CPU cases")
    raw, wanted = packed_state()
    state = out / "synthetic-state.bin"
    state.write_bytes(raw)
    check = json.loads(run([worker, "--state-fixture", state, "7", "2"], out, out / "worker-state", env))
    require(check == {"event": "CPU_STATE_PASS", "raw_bytes": len(raw), "canonical_bytes": len(wanted),
                      "sha256": hashlib.sha256(wanted).hexdigest()}, "synthetic active K/V canonical bytes")
    result = {
        "status": "PASS", "architecture": "sm_120a", "native_cuda_elf_count": len(slices),
        "stored_Q8_0_kernel_entry_widths": kernels, "exports": native_exports,
        "linked_artifacts": {x.name: identity(x) for x in built},
        "dynamic_direct_imports": dependencies, "worker_fixtures": fixture, "synthetic_state": check,
        "verifier_tools": {"cuobjdump": identity(cuda), "dumpbin": identity(dump)},
        "device_dispatch": "NOT_RUN", "model_numerical_qualification": "NOT_RUN", "GPU_calls": 0, "model_loads": 0,
    }
    (out / "BUILD_VERIFICATION.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: result[k] for k in ("status", "architecture", "native_cuda_elf_count",
                                             "stored_Q8_0_kernel_entry_widths", "worker_fixtures", "synthetic_state")}))


if __name__ == "__main__":
    main()
