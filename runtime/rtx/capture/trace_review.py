"""Resolve CUPTI launch records by API correlation, Windows thread and scope ancestry."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re


GPU_KINDS = {"kernel", "memcpy", "memset"}
Q8_KERNEL = re.compile(r"mul_mat_vec_qIL9ggml_type8ELi([1-4])E")


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def read(path):
    return json.loads(path.read_bytes())


def lines(path):
    with path.open(encoding="utf-8") as reader:
        return [json.loads(line) for line in reader]


def identity(path):
    with path.open("rb") as f:
        return {"bytes": path.stat().st_size, "sha256": hashlib.file_digest(f, "sha256").hexdigest()}


def write(path, data):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, allow_nan=False)
        f.write("\n")


def history(scope, scopes):
    seen = set()
    while scope:
        need(scope["id"] not in seen, "cyclic CUPTI scope ancestry")
        seen.add(scope["id"])
        yield scope
        if not scope["parent"]:
            break
        parent = scopes[scope["parent"]]
        need((scope["pid"], scope["tid"]) == (parent["pid"], parent["tid"]) and
             parent["start"] <= scope["start"] <= scope["end"] <= parent["end"],
             "scope ancestry on different host thread or outside timestamps")
        scope = parent


def bind(activity, links, apis, scopes):
    corr = activity["corr"]
    ids = links[corr]
    if len(ids) != 1:
        return None, "missing_external" if not ids else "ambiguous_external"
    scope = scopes[next(iter(ids))]
    matches = [x for x in apis[corr] if (x["pid"], x["tid"]) == (scope["pid"], scope["tid"])
               and scope["start"] <= x["start"] <= x["end"] <= scope["end"]
               and x["result"] == 0]
    if activity["kind"] == "kernel":
        matches = [x for x in matches if "Launch" in x["api"]]
    if not matches:
        return None, "no_matching_successful_api_on_marked_thread"
    matches.sort(key=lambda x: (x["kind"] != "driver", x["start"]))
    return (scope, matches[0]), None


def group(chain):
    forward = next((x for x in chain if x["kind"] == "forward"), None)
    cycle = next((x["cycle"] for x in chain if x["kind"] == "cycle"), None)
    first = chain[0]
    if first["kind"] in {"kv_export", "kv_persist", "logits_export"}:
        return first["kind"], cycle, forward
    if forward:
        return forward["name"], cycle, forward
    return first["name"], cycle, None


def trace(arm_dir, arm, request_id, export):
    collection = arm_dir / "cupti.summary.json"
    summary = read(collection)
    scope_path = arm_dir / "cupti.scopes.jsonl"
    activity_path = arm_dir / "cupti.activities.jsonl"
    buffer_index = arm_dir / "cupti.buffers.jsonl"
    buffer_file = arm_dir / "cupti.buffers.bin"
    need(summary["native_request_completed"] and not summary["collector_error"] and summary["dropped"] == 0,
         "CUPTI recorder completion/loss receipt")
    idx = lines(buffer_index)
    offset = 0
    for i, x in enumerate(idx, 1):
        need(x["buffer"] == i and x["offset"] == offset and x["dropped"] == 0, "raw CUPTI buffer index")
        offset += x["bytes"]
    need(offset > 0 and offset == buffer_file.stat().st_size == summary["raw_buffer_bytes"] and
         len(idx) == summary["raw_buffer_count"], "original CUPTI buffer coverage")
    rows = lines(activity_path)
    marks = lines(scope_path)
    scopes = {x["id"]: x for x in marks}
    need(len(scopes) == summary["scope_count"] and set(scopes) == set(range(1, len(marks) + 1)) and
         len(scopes) == len(marks) and len(rows) == summary["activity_records"], "CUPTI export completeness")
    requests = [x for x in marks if x["kind"] == "request"]
    need(len(requests) == 1 and requests[0]["name"] == request_id, "one frozen traced request")
    req = requests[0]
    need(all(x["pid"] == summary["worker_pid"] and 0 < x["start"] <= x["end"] for x in marks),
         "scope worker identity and timestamp")
    thread_ids = {tid: i for i, tid in enumerate(sorted({x["tid"] for x in marks}), 1)}
    for mark in marks:
        list(history(mark, scopes))

    links, apis = defaultdict(set), defaultdict(list)
    for event in rows:
        if event["kind"] == "external":
            need(event["scope"] in scopes, "CUPTI refers to an unknown scoped ID")
            links[event["corr"]].add(event["scope"])
        if event["kind"] in ("runtime", "driver"):
            apis[event["corr"]].append(event)

    by_stage, widths, out_of_request, unmapped = defaultdict(Counter), defaultdict(Counter), Counter(), Counter()
    unmatched_inside = []
    spans = {}
    for mark in marks:
        if mark["kind"] == "forward":
            _, cycle, _ = group(list(history(mark, scopes)))
            spans[mark["id"]] = {"scope_id": mark["id"], "phase": mark["name"], "label": mark["label"],
                                 "cycle": cycle, "submit_width": mark["width"], "kernels": 0,
                                 "q8_kernel_widths": {}, "first_kernel": None}

    with export.open("x", encoding="utf-8", newline="\n") as out:
        for event in rows:
            kind = event["kind"]
            if kind not in GPU_KINDS:
                continue
            mapped, reason = bind(event, links, apis, scopes)
            if mapped is None:
                unmapped[(kind, reason)] += 1
                if not event["start"] or req["start"] <= event["start"] <= req["end"] or any(
                    req["start"] <= api["start"] <= req["end"] for api in apis[event["corr"]]
                ):
                    unmatched_inside.append({"kind": kind, "corr": event["corr"], "reason": reason,
                                             "symbol": event.get("name"), "start": event["start"]})
                continue
            scope, api = mapped
            chain = list(history(scope, scopes))
            current_req = next((x for x in chain if x["kind"] == "request"), None)
            phase, cycle, forward = group(chain)
            if not current_req:
                out_of_request[kind] += 1
                continue
            need(current_req["id"] == req["id"] and 0 < event["start"] <= event["end"], "GPU interval/request ID")
            by_stage[phase][kind] += 1
            item = {"request_id": request_id, "worker_pid": api["pid"], "thread_id": api["tid"],
                    "phase": phase, "cycle": cycle, "scope": scope["id"], "api": api["api"],
                    "api_kind": api["kind"], "api_start": api["start"], "api_end": api["end"], **event}
            out.write(json.dumps(item, separators=(",", ":")) + "\n")
            if kind != "kernel":
                continue
            q = Q8_KERNEL.search(event["name"])
            width = q.group(1) if q else None
            if width:
                widths[phase][width] += 1
            if forward and phase not in ("kv_export", "kv_persist", "logits_export"):
                span = spans[forward["id"]]
                span["kernels"] += 1
                if width:
                    span["q8_kernel_widths"][width] = span["q8_kernel_widths"].get(width, 0) + 1
                if span["first_kernel"] is None:
                    span["first_kernel"] = {"correlation_id": event["corr"], "api": api["api"], "name": event["name"],
                                            "stream": event["stream"], "scope": scope["id"],
                                            "thread_ordinal": thread_ids[api["tid"]]}
    expected = {"target_prefill_s": 24, "target_verify_s": 38, "draft_prefill_s": 24, "draft_sync_s": 38,
                "draft_propose_s": 103}
    metrics = {
        "arm": arm, "request_id": request_id, "cupti_api_version": summary["version"], "dropped_records": summary["dropped"],
        "closed_original_activity_buffers": len(idx), "original_activity_records": len(rows),
        "mapped_request_gpu_records_by_phase": by_stage, "outside_request_mapped": out_of_request,
        "outside_and_inside_unmapped": [{"kind": k, "reason": reason, "count": count}
                                        for (k, reason), count in sorted(unmapped.items())],
        "unmapped_request_or_unresolved_time_records": len(unmatched_inside),
        "first_unmatched": unmatched_inside[:12], "q8_mmvq_widths_by_phase": widths,
        "forward_spans": list(spans.values()),
        "files_retained_locally": {p.name: identity(p) for p in (collection, scope_path, activity_path, buffer_index,
                                                                buffer_file, export)},
    }
    observed = Counter(x["phase"] for x in spans.values())
    complete = (not unmatched_inside and expected == observed and all(s["kernels"] > 0 for s in spans.values()) and
                by_stage["kv_export"]["memcpy"] > 0 and not by_stage["kv_persist"])
    selected_widths = widths["target_verify_s"]
    changed = (selected_widths["2"] > 0 and selected_widths["4"] > 0) if arm == "C4" else (
        selected_widths["1"] > 0 and selected_widths["2"] == selected_widths["3"] == selected_widths["4"] == 0)
    metrics["status"] = "PASS" if complete and changed else "FAIL"
    metrics["forward_counts"] = observed
    return metrics


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--arm-dir", type=Path, required=True)
    p.add_argument("--arm", choices=("C1", "C4"), required=True)
    p.add_argument("--request-id", required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    a = p.parse_args()
    a.out_dir.mkdir()
    result = trace(a.arm_dir, a.arm, a.request_id, a.out_dir / "MAPPED_ACTIVITY.jsonl")
    write(a.out_dir / "TRACE_REVIEW.json", result)
    print(json.dumps({k: result[k] for k in ("status", "unmapped_request_or_unresolved_time_records", "forward_counts",
                                             "q8_mmvq_widths_by_phase")}))
    raise SystemExit(0 if result["status"] == "PASS" else 2)
