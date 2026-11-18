#!/usr/bin/env python3
"""Optional acquisition only. Fetch pinned Git objects; never run downloaded code.

The drawing program does not import this file, use gh, or require network access.
"""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

import base64
import concurrent.futures
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
OUT = HERE / "inputs"
REPO = "leecdiang/HeteroSpec"
ROOT = f"repos/{REPO}/"
PINS = {
    163: "10a70566ce01ab707dbdcc57d8270c1434088f07",
    171: "371223b696bb805030c29f04e39eb17b57fb2ebb",
    257: "7deb9aa28a934878837d3d74be8ed14bc374809a",
    260: "9398a857e8cbfc8fbe3f35b1f7b6876b65a533d1",
    266: "0cac675cc757f195b74893da53af2161c2599c97",
    268: "997be15f9388f904055a3b09f409818e13483365",
    276: "8224998c5aa3032476d669990e6ae20e10cd1fb0",
}
B = "benchmarks/b570_llama_companion_v1/host_execution/"
A = "benchmarks/a5000_local_boundary_20261117/"
H = "reviews/taco_mainline_freeze_20261117_v1/"
sources = {
    "rtx": (171, "benchmarks/rtx_operator_frontier_v1/execution/evidence/operands.json.gz"),
    "before": (163, B + "COMMITTED_REFERENCE_AUDIT-00.json"),
    "after": (163, B + "COMBINED_COMMITTED_AUDIT-03.json"),
    "vulkan_report": (163, B + "RESULTS.md"),
    "core": (257, "benchmarks/three_platform_closeout_20261116/prefill_p4/results_a5000_20261116/formal/RAW_TEXT.tar.xz"),
    "local": (260, A + "results/RAW_TEXT.tar.xz"),
    "confirm": (266, "benchmarks/a5000_confirmation_execution_20261117/results/TEXT_EVIDENCE.tar.xz"),
    "setup": (260, A + "setup_local.py"),
    "handoff": (268, H + "source/A_source_map.json"),
    "crossbinding": (268, H + "source/A_cpu_method_checks_round2.json"),
    "paper_counts": (276, "papers/taco/20261118_visual_reconstruction/data/mechanism_counts.csv"),
}
records = {}
sha256 = lambda b: hashlib.sha256(b).hexdigest()


def api(route):
    return json.loads(subprocess.check_output(["gh", "api", ROOT + route]))


def fetch(item):
    key, (pr, path) = item
    meta = api(f"contents/{path}?ref={PINS[pr]}")
    obj = meta if meta.get("encoding") == "base64" and meta.get("content") else api("git/blobs/" + meta["sha"])
    raw = base64.b64decode(obj["content"])
    blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    if blob != meta["sha"] or len(raw) != meta["size"]:
        raise ValueError(f"identity mismatch: {path}")
    return key, raw, {"pr": pr, "commit": PINS[pr], "path": path, "git_blob": blob,
                      "bytes": len(raw), "sha256": sha256(raw)}


def as_json(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode()


def compress(raw):
    bio = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=bio, mtime=0) as out:
        out.write(raw)
    return bio.getvalue()


def save(name, data, key, *, member=None, full=None, selection=None):
    (OUT / name).write_bytes(data)
    record = {"source": key, "bytes": len(data), "sha256": sha256(data)}
    if member:
        record.update(member=member, member_sha256=sha256(full))
    if selection:
        record["selection"] = selection
    records[name] = record


def excerpt(raw, ranges):
    lines = raw.decode().splitlines()
    return [{"first": start, "last": end, "lines": lines[start-1:end]} for start, end in ranges]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        fetched = list(pool.map(fetch, sources.items()))
    raw = {key: data for key, data, _ in fetched}
    bindings = {key: meta for key, _, meta in fetched}
    save("rtx_operands.json.gz", raw["rtx"], "rtx")
    for stage in ("before", "after"):
        save("b570_" + stage + ".json.gz", compress(raw[stage]), stage,
             selection="gzip wrapper around the byte-identical entire source JSON")
    save("paper276_counts.csv", raw["paper_counts"], "paper_counts")
    save("source_map268.json", raw["handoff"], "handoff")
    save("vulkan_repair_lines.json", as_json(excerpt(raw["vulkan_report"], [(13, 13), (19, 26)])),
         "vulkan_report", selection="original-numbered lines; contextual intervention and arm definitions")
    save("core_binding268.json", raw["crossbinding"], "crossbinding")
    arcs = {k: tarfile.open(fileobj=io.BytesIO(raw[k])) for k in ("local", "confirm", "core")}
    for arm in ("SIMPLE", "LOCAL"):
        for key, suffix, ident in (("local", "260", f"a5l-formal-c1-r1-{arm}-measured"),
                                   ("confirm", "266", f"a261-qualification-b00-c1-{arm}-full_trace")):
            arc = arcs[key]
            path, = [p for p in arc.getnames() if p.endswith("/"+ident+"/RECEIPT.json")]
            for filename in (["RECEIPT"] if key == "local" else ["RECEIPT", "CHECKED"]):
                member = path.replace("RECEIPT.json", filename+".json")
                data = arc.extractfile(member).read()
                save(f"{suffix}_{arm}_{filename.lower()}.json.gz", compress(data), key, member=member,
                     full=data, selection="gzip wrapper around byte-identical member")
        ident = f"a261-qualification-b00-c1-{arm}-full_trace"
        trace, = [p for p in arcs["confirm"].getnames() if ident+"-candidate/" in p and p.endswith("stderr.log")]
        data = arcs["confirm"].extractfile(trace).read()
        rows = []
        for number, line in enumerate(data.decode().splitlines(), 1):
            if (re.match(r"^TPDS_TILE base=(253|255) ", line)
                or (line.startswith("RTX164_ATTN ") and line.split()[-1] in {"position=253","position=254","position=255","position=256"})):
                rows.append({"line": number, "text": line})
        save(f"266_{arm}_view_lines.json.gz", compress(as_json(rows)), "confirm", member=trace,
             full=data, selection="TPDS_TILE at base 253/255 and RTX164_ATTN with position 253..256; exact numbered source lines")
    # Store only the source spans needed to interpret the transaction graph.
    spans = [
        ("planner", "local", "host/candidate-04/source/src/inherited/phase_plan.hpp", [(29,52)]),
        ("adapter", "local", "host/candidate-04/source/src/inherited/resident_context.hpp", [(19,60)]),
        ("context", "local", "host/candidate-04/source/src/native.cpp", [(115,139),(155,155)]),
        ("consumer", "local", "host/candidate-04/source/src/transaction.hpp", [(9,41)]),
        ("replay", "local", "host/candidate-04/source/src/local_replay.inc", [(30,60),(61,103),(114,129)]),
        ("graph", "core", "./data/core_source/src/llama-graph.cpp",
         [(7,18),(501,515),(1574,1615),(1865,1905),(2762,2772),
          (2967,2979),(3026,3056),(3061,3112)]),
    ]
    for label, key, member, ranges in spans:
        data = arcs[key].extractfile(member).read()
        save("source_"+label+".json", as_json(excerpt(data, ranges)), key,
             member=member, full=data, selection=ranges)
    for arc in arcs.values():
        arc.close()
    rows = []
    for i,line in enumerate(raw["setup"].decode().splitlines(),1):
        if any(x in line.lower() for x in ("#257", "p4", "prefill_pack4", "archives")):
            rows.append({"line": i, "text": line})
    save("setup260_lines.json", as_json(rows), "setup", selection="original lines containing #257, p4, prefill_pack4 or archives")
    (HERE / "INPUTS.json").write_bytes(as_json({"repository": REPO, "sources": bindings, "local_files": records}))
    print(f"{len(records)} scoped files in {OUT}; {len(bindings)} verified pinned source objects")


if __name__ == "__main__":
    main()
