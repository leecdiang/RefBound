"""Compare a local capture pair with the frozen evidence and independent reference objects."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from kv_review import check_complete
from trace_review import identity, lines, need, read


RECORDS = Path(__file__).resolve().parents[1] / "records"


def compare_f32(case, sd_u, r_trace, expected, vocab):
    width = vocab * 4
    candidate = case / "vectors.f32"
    full = candidate.read_bytes()
    need(full == (sd_u / "vectors.f32").read_bytes(), "full F32 byte agreement with SD_U")
    need(identity(candidate)["sha256"] == expected["full_F32_sha256"], "frozen full F32 SHA256")
    need(len(full) == expected["full_F32_elements"] * 4 and
         np.isfinite(np.frombuffer(full, dtype="<f4")).all(), "complete finite F32 rows")
    picked = [row for row in lines(case / "vectors.jsonl") if row["name"].split("/")[0] in ("verify", "target-prefill")]
    reference = {row["name"]: row for row in lines(r_trace / "vectors.jsonl")}
    target = expected["original_scalar_target"]
    need(len(picked) == len({r["name"] for r in picked}) == target["vectors"], "scalar target row coverage")
    digest = hashlib.sha256()
    with (r_trace / "vectors.f32").open("rb") as oracle:
        for row in picked:
            ref = reference[row["name"]]
            need(row["bytes"] == ref["bytes"] == width and row["position"] == ref["position"], "owned target row")
            oracle.seek(ref["offset"])
            payload = full[row["offset"]:row["offset"] + width]
            need(len(payload) == width and payload == oracle.read(width), "full F32 row vs independent q1")
            digest.update(payload)
    need(digest.hexdigest() == target["combined_bytes_sha256"], "frozen scalar target SHA256")
    return len(full) // width


def check_trace(review, expected, arm):
    counts = review["mapped_request_gpu_records_by_phase"]
    need(review["status"] == "PASS" and
         review["dropped_records"] == expected["cupti_dropped"] and
         review["unmapped_request_or_unresolved_time_records"] == expected["unassociated_request_records"],
         f"{arm} loss and correlation receipt")
    need({phase: v["kernel"] for phase, v in counts.items() if v.get("kernel")} == expected["kernels_by_phase"]
         and counts["kv_export"]["memcpy"] == expected["kv_export_memcpy"]
         and review["forward_counts"] == expected["native_forward_spans"], f"{arm} phase coverage")
    need({"q" + width: n for width, n in review["q8_mmvq_widths_by_phase"]["target_verify_s"].items()}
         == expected["target_verify_q8_0_mmvq"], f"{arm} verify launch widths")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("run", "sd-u", "r-trace", "target-reference-kv", "draft-reference-kv"):
        parser.add_argument("--" + arg, type=Path, required=True)
    args = parser.parse_args()
    expected = read(RECORDS / "expected.json")
    checkpoints = read(RECORDS / "kv-checkpoints.json")["checkpoints"]
    refs = {"target": args.target_reference_kv, "draft": args.draft_reference_kv}
    for label, folder in (("SD_U", args.sd_u), ("R_TRACE", args.r_trace)):
        for name, wanted in expected["references"][label].items():
            need(identity(folder / name) == wanted, f"{label} frozen {name}")
    oracle = read(args.r_trace / "native.json")
    tx_digest = hashlib.sha256(json.dumps(oracle["transactions"], sort_keys=True, separators=(",", ":")).encode())
    need(tx_digest.hexdigest() == expected["transactions_sha256"], "reference transaction digest")
    successors = check_complete(args.run, checkpoints, refs, oracle)
    ids = read(args.run / "DEVICE_FREEZE.json")["new_ids"]
    for arm in ("C1", "C4"):
        run_arm = args.run / arm
        case = run_arm / "request"
        native = read(case / "native.json")
        review = read(run_arm / "TRACE_REVIEW.json")
        numerical = expected["numerical"][arm]
        need(native["request_id"] == review["request_id"] == ids[arm], f"{arm} receipt identity")
        need(native["target_pack4_requested"] == (arm == "C4") and
             all(native[k] == v for k, v in expected["dispatch"][arm].items()), f"{arm} native dispatch")
        check_trace(review, expected["trace"][arm], arm)
        need(successors[arm] == numerical["successor_generations"], f"{arm} own successor generations")
        frontier = Path(native["frontier_payload"]).resolve(strict=True)
        need(frontier.parent == (run_arm / "objects").resolve() and
             identity(frontier) == {"bytes": expected["vocab_size"] * 4, "sha256": numerical["terminal_frontier_sha256"]},
             f"{arm} terminal frontier")
        need(identity(case / "vectors.jsonl") == expected["references"]["SD_U"]["vectors.jsonl"], f"{arm} row index")
        count = compare_f32(case, args.sd_u, args.r_trace, numerical, expected["vocab_size"])
        print(json.dumps({"arm": arm, "status": "PASS", "F32_vectors": count,
                          "intermediate_KV": expected["intermediate_objects_per_arm"],
                          "own_successor_links": len(successors[arm])}))


if __name__ == "__main__":
    main()
