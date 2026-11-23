"""Verify the model-free RTX release and its frozen summary invariants."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_bytes())


def require(condition, label):
    if not condition:
        raise ValueError(label)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", required=True)
    parser.parse_args()
    files = read(ROOT / "MANIFEST.json")["files"]
    for entry in files:
        local = ROOT / entry["path"]
        with local.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        require(digest == entry["sha256"] and local.stat().st_size == entry["bytes"], entry["path"])

    expected = read(ROOT / "records" / "expected.json")
    require(expected["input"]["tokens"] == 757 and expected["shared_environment"]["HS_PREFILL_PACK4"] == "0"
            and expected["C4_flag_values"] == {"C1": "0", "C4": "1"}, "input and frozen arm settings")
    widths = {"C1": {"q1": 8550}, "C4": {"q4": 8325, "q2": 225}}
    for arm, entry in expected["trace"].items():
        require(sum(entry["kernels_by_phase"].values()) == entry["request_kernel_links"] == 246252,
                f"{arm} kernel accounting")
        require(entry["target_verify_q8_0_mmvq"] == widths[arm] and
                entry["cupti_dropped"] == entry["unassociated_request_records"] == 0, f"{arm} launch evidence")
        require(sum(entry["native_forward_spans"].values()) ==
                expected["dispatch"][arm]["target_calls"] + expected["dispatch"][arm]["draft_calls"] == 227,
                f"{arm} actual native spans")
        require(expected["dispatch"][arm]["pack4_prefill_dispatch_delta"][1] == 0, f"{arm} prefill admissions")
        numbers = expected["numerical"][arm]
        require(numbers["original_scalar_target"]["vectors"] == 174 and
                numbers["full_F32_elements"] == 339 * expected["vocab_size"] and
                len(numbers["successor_generations"]) == numbers["own_successor_links"] == 37, f"{arm} numerical counts")
    dispatch = dict(zip(expected["dispatch_fields"], expected["dispatch"]["C4"]["pack4_verify_dispatch_delta"]))
    require(dispatch["full4_tiles"] == widths["C4"]["q4"] and dispatch["tail_tiles"] == widths["C4"]["q2"],
            "native dispatch and CUPTI launch agreement")

    rows = read(ROOT / "records" / "kv-checkpoints.json")["checkpoints"]
    require(Counter(row["coverage"] for row in rows) == {"INTERMEDIATE": 75, "TERMINAL": 2, "INACTIVE_MARKER": 1}
            and len({(row["generation"], row["role"]) for row in rows}) == len(rows), "KV coverage")
    intermediates = [row for row in rows if row["coverage"] == "INTERMEDIATE"]
    require(sum(row["payload_bytes_each"] for row in intermediates) == expected["intermediate_bytes_per_arm"] ==
            5065667352, "full intermediate bytes per arm")
    for row in rows:
        if row["coverage"] != "INACTIVE_MARKER":
            require(row["historical_canonical_sha256"] ==
                    row["new_C1_canonical_sha256"] == row["new_C4_canonical_sha256"] and
                    row["C1_C4_raw_bytes"] == "BYTE_EQUAL" and row["finite"] == "FINITE", "KV comparison receipt")
    require(expected["historical_originals"] == "BLOCKED" and expected["historical_performance"]["requests"] == 864,
            "historical evidence boundary")
    print(json.dumps({"status": "PASS", "manifest_files": len(files), "intermediate_KV_per_arm": len(intermediates),
                      "actual_verify_launches": widths, "GPU_calls": 0}))


if __name__ == "__main__":
    main()
