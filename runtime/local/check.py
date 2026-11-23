#!/usr/bin/env python3
"""Check the public trace and, optionally, locally held crossing payloads."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct

from readers.active_kv import parse
from readers.common import digest, hexsha, need

HERE = Path(__file__).resolve().parent
ARMS = ("R", "SIMPLE", "LOCAL")
STATE_ORDER = ("prefix", "primary_uncommitted", "primary_commit",
               "continuation_uncommitted", "continuation_commit")


def read(path):
    return json.loads(path.read_text())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def widths(receipt, phase):
    return [x.get("width", x.get("rows")) for x in receipt["target_executions"] if x["phase"] == phase]


def run_quick(case, histories, objects):
    expected_widths = {
        "noncrossing": (([1, 1, 1, 1], [1, 1, 1, 1]), ([4], [4]), ([4], [4])),
        "crossing": (([1, 1, 1, 1], [1, 1, 1, 1]), ([3, 1], [1, 3]), ([4], [4])),
    }
    for h in histories:
        for arm, (main, continuation) in zip(ARMS, expected_widths[h["id"]]):
            a, b = h["arms"][arm]["phases"]
            need(a["base"] == h["history_rows"] and b["base"] == a["keep"], "Same-arm continuation")
            need([a["physical_widths"], b["physical_widths"]] == [main, continuation], "Physical partition")
            need(not any(x for call in (a, b) for x in call["work"].get("P4", [])), "P4 off")
            if arm != "R":
                for call in (a, b):
                    widths = call["physical_widths"]
                    work = call["work"]
                    need(work["dot_calls"] == sum(385 if x == 1 else 449 for x in widths),
                         "Observed quantized projection calls")
                    need(work["native4_dispatches"] == 449 * sum(2 <= x <= 4 for x in widths),
                         "Observed few-column path")
                need(b["work"]["graphs_reused"] == (1 if h["id"] == "noncrossing" else 0), "Observed graph reuse")
        need(all(len(v) == 4 for v in h["extents"]), "Complete extent vectors")
    negative, positive = histories
    need(negative["extents"] == [[256] * 4] * 2, "Noncrossing geometry")
    need(positive["extents"] == [[256, 256, 256, 512], [256, 512, 512, 512]] and
         positive["cycle"] == 37, "Crossing extent-vector change at equal maximum")
    types = Counter(x["dtype"] for x in objects if "raw_sha256" in x)
    need(types == {"F32": 27, "F16": 15}, "Complete published object identities")
    pairs = Counter()
    for obj in objects:
        if "raw_sha256" in obj:
            need(obj["finite"] is True, "Recorded finite object")
            hexsha(obj["raw_sha256"])
            hexsha(obj["canonical_sha256"])
        for c in obj["checks"]:
            need(c["byte_equal"] is True and c["candidate_sha256"] == c["reference_sha256"],
                 "Recorded successful comparison")
            pairs[c["relation"]] += 1
    expected = case["matrix"]
    need(pairs == {
        "same_arm_historical_capture": expected["historical_same_arm_pairs"],
        "this_run_independent_q1_R": expected["reference_F32_pairs"] + expected["reference_KV_pairs"],
        "same_arm_retained_prefix": expected["own_retained_prefix_pairs"],
    } and sum(pairs.values()) == expected["full_byte_comparisons"], "Frozen qualification counts")
    return dict(mode="quick", status="PASS", object_identities=sum(types.values()),
                recorded_comparisons=sum(pairs.values()), historical_trace_histories=len(histories),
                raw_payloads_compared=0, GPU_requests=0)


def finite(payload, fmt):
    try:
        import numpy as np
    except ImportError:
        return all(math.isfinite(x[0]) for x in struct.iter_unpack(fmt, payload))
    dtype = {"<e": "<f2", "<f": "<f4"}[fmt]
    return bool(np.isfinite(np.frombuffer(payload, dtype=dtype)).all())


def contained(directory, name):
    path = (directory / name).resolve()
    need(path.is_relative_to(directory), "Receipt path escapes its request directory")
    return path


def greedy(payload):
    return max(enumerate(struct.iter_unpack("<f", payload)), key=lambda row: row[1][0])[0]


def run_capture_check(captures, case, positive, objects):
    """Check all saved raw/canonical objects and commit semantics, entirely on CPU."""
    profile = read(HERE / "evidence/STATE_PROFILE.json")
    need(profile["target_model_sha256"] == case["target"]["sha256"], "Target model family/profile")
    reference = {}
    counts = Counter()
    for arm in ARMS:
        root = (captures / arm).resolve()
        r = read(root / "RECEIPT.json")
        lowering = "LOCAL" if arm == "LOCAL" else "SIMPLE"
        need(r["variant"] == arm and r["local_lowering"] == lowering and r["stage"] == "qualification" and
             not r["prefill_pack4_enabled"] and r["root"] == positive["source_identity"] and
             digest(r["case_input"]) == positive["canonical_case_sha256"] and
             (r["target_rows"], r["draft_rows"]) == (261, 0), "Frozen replay contract")
        observed = positive["arms"][arm]["phases"]
        need(all(widths(r, p["phase"]) == p["physical_widths"] for p in observed), "Observed per-phase dispatch")
        need([x["stage"] for x in r["checkpoints"]] == list(STATE_ORDER), "All five checkpoints")
        checkpoint = {x["stage"]: x for x in r["checkpoints"]}
        owned = {(x["step"], x["row"]): x for x in r["owned_vectors"]}
        need(len(r["owned_vectors"]) == len(owned) == 8, "All requested score rows")
        captured = {}
        for row in (x for x in objects if x["arm"] == arm and "raw_sha256" in x):
            role = row["role"]
            if row["dtype"] == "F16":
                entry = checkpoint[role]
                proof = entry["proof"]
                active = row["shape"][0]
                need(proof.get("model_sha256") == profile["target_model_sha256"] and
                     proof["active_tokens"] == proof["pending_position"] == active, "Active KV metadata")
                raw = contained(root, entry["path"]).read_bytes()
                payload, meta = parse(raw, list(range(active)), profile)
                need(meta["raw_v_transposed"] == proof["raw_v_transposed"] and
                     len(raw) == proof["raw_native_bytes"] and sha(payload) == proof["active_KV_sha256"],
                     "Complete native KV and canonical hash")
                fmt = "<e"
            else:
                if role == "prefix-frontier.f32":
                    name = role
                else:
                    step, logical_row = map(int, role.removeprefix("owned/step").removesuffix(".f32").split("-row"))
                    name = owned[step, logical_row]["path"]
                raw = contained(root, name).read_bytes()
                need(len(raw) == 4 * case["execution"]["vocab"], "Full F32 vector")
                payload, fmt = raw, "<f"
            need(sha(payload) == row["canonical_sha256"] and finite(payload, fmt),
                 "Frozen complete canonical object or finite-value mismatch: " + arm + "/" + role)
            counts["frozen_canonical_hash_matches"] += 1
            counts["raw_serializer_hash_matches"] += sha(raw) == row["raw_sha256"]
            captured[role] = payload
            if arm == "R":
                reference[role] = payload
            else:
                need(payload == reference[role], "Full bytes against independent R: " + arm + "/" + role)
                counts["F32_pairs" if fmt == "<f" else "KV_pairs"] += 1
        for a, b in zip(STATE_ORDER, STATE_ORDER[1:]):
            n = min(len(captured[a]), len(captured[b]))
            need(captured[a][:n] == captured[b][:n], "Retained bytes across own trim/append")
            counts["retained_prefix_pairs"] += 1
        pending = greedy(captured["prefix-frontier.f32"])
        base = positive["history_rows"]
        need(len(r["calls"]) == 2, "Both own transactions")
        for step, call in enumerate(r["calls"]):
            trace = call["trace"]
            frozen = r["case_input"]["transaction" if step == 0 else "continuation"]
            scores = [captured[f"owned/step{step}-row{q}.f32"] for q in range(4)]
            decisions = [greedy(v) for v in scores]
            proposals = trace["proposals"]
            accepted = next((i for i, t in enumerate(proposals) if t != decisions[i]), len(proposals))
            label = "primary_commit" if step == 0 else "continuation_commit"
            need(trace["base"] == base == frozen["base"] and trace["seed"] == pending == frozen["seed"] and
                 len(proposals) == 3 and proposals == frozen["proposals"] and
                 trace["decisions"] == decisions and trace["accepted"] == accepted and
                 trace["keep"] == base + accepted + 1 and trace["pending"] == decisions[accepted] and
                 trace["frontier_row"] == accepted and call["owned_frontier_sha256"] == sha(scores[accepted]) and
                 trace["emitted"] == decisions[:accepted + 1] and not trace["done"], "Independent ownership/commit")
            base, pending = trace["keep"], trace["pending"]
            need(checkpoint[label]["proof"]["pending_id"] == pending, "Each arm's own committed pending")
        need((r["pending_position"], r["pending_id"]) == (base, pending) and base == 259, "Own final state")
    need((counts["F32_pairs"], counts["KV_pairs"], counts["frozen_canonical_hash_matches"],
          counts["retained_prefix_pairs"]) == (18, 10, 42, 12), "Complete saved-object readback")
    return dict(mode="saved_capture_readback", status="PASS", GPU_requests=0, **counts)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true", help="Use only the public metadata (default)")
    mode.add_argument("--captures", type=Path, help="Private directory containing R/SIMPLE/LOCAL request directories")
    args = p.parse_args()
    case = read(HERE / "evidence/CASE.json")
    histories = read(HERE / "evidence/TWO_HISTORIES.json")["histories"]
    objects = read(HERE / "evidence/CROSSING_OBJECTS.json")["objects"]
    print(json.dumps(run_quick(case, histories, objects), indent=2))
    if args.captures:
        print(json.dumps(run_capture_check(args.captures, case, histories[1], objects), indent=2))


if __name__ == "__main__":
    main()
