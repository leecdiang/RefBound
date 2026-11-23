"""Audit CUDA links using SQL/recursive ancestry against the original CUPTI export."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sqlite3


SQL = """
CREATE TABLE scopes(id INTEGER PRIMARY KEY, parent INTEGER, kind TEXT, name TEXT,
                    pid INTEGER, tid INTEGER, start INTEGER, end INTEGER);
CREATE TABLE ext(corr INTEGER, scope INTEGER, PRIMARY KEY(corr, scope)) WITHOUT ROWID;
CREATE TABLE api(corr INTEGER, kind TEXT, name TEXT, pid INTEGER, tid INTEGER, start INTEGER, end INTEGER, result INTEGER);
CREATE TABLE kernel(corr INTEGER, symbol TEXT, stream INTEGER, start INTEGER, end INTEGER);
CREATE INDEX api_corr ON api(corr);
"""
JOIN = """
WITH RECURSIVE
ancestry(leaf, id) AS (
    SELECT id,id FROM scopes
    UNION ALL
    SELECT ancestry.leaf,scopes.parent FROM ancestry JOIN scopes USING(id) WHERE scopes.parent > 0
),
captured AS (
    SELECT a.leaf AS scope FROM ancestry a JOIN scopes s ON a.id=s.id WHERE s.kind='request' AND s.name=?
),
forward AS (
    SELECT a.leaf AS scope, s.id, s.name FROM ancestry a JOIN scopes s ON a.id=s.id WHERE s.kind='forward'
)
SELECT k.corr,k.symbol,k.stream,k.start,k.end,e.scope,
       CASE WHEN s.kind='logits_export' THEN 'logits_export'
            WHEN s.kind='kv_export' THEN 'kv_export'
            WHEN s.kind='kv_persist' THEN 'kv_persist'
            ELSE COALESCE(f.name,s.name) END phase
FROM kernel k JOIN ext e ON k.corr=e.corr JOIN captured c ON c.scope=e.scope
JOIN scopes s ON s.id=e.scope LEFT JOIN forward f ON f.scope=e.scope
WHERE k.start > 0 AND k.end >= k.start
AND EXISTS (SELECT 1 FROM api a WHERE a.corr=k.corr AND a.pid=s.pid AND a.tid=s.tid
            AND s.start<=a.start AND a.start<=a.end AND a.end<=s.end
            AND a.result=0 AND a.name LIKE '%Launch%');
"""


def read(path):
    return json.loads(path.read_bytes())


def lines(path):
    with path.open(encoding="utf-8") as f:
        yield from map(json.loads, f)


def need(ok, detail):
    if not ok:
        raise ValueError(detail)


def check_arm(folder, request):
    db = sqlite3.connect(":memory:")
    try:
        # The API index is built once after streaming ingress.
        db.executescript(SQL[:SQL.index("CREATE INDEX")])
        for key in lines(folder / "cupti.scopes.jsonl"):
            db.execute("INSERT INTO scopes VALUES (?,?,?,?,?,?,?,?)",
                       tuple(key[k] for k in ("id", "parent", "kind", "name", "pid", "tid", "start", "end")))
        counts = Counter()
        for q in lines(folder / "cupti.activities.jsonl"):
            kind = q["kind"]
            counts[kind] += 1
            if kind == "external":
                db.execute("INSERT OR IGNORE INTO ext VALUES (?,?)", (q["corr"], q["scope"]))
            elif kind in ("driver", "runtime"):
                db.execute("INSERT INTO api VALUES (?,?,?,?,?,?,?,?)",
                           tuple(q[k] for k in ("corr", "kind", "api", "pid", "tid", "start", "end", "result")))
            elif kind == "kernel":
                db.execute("INSERT INTO kernel VALUES (?,?,?,?,?)",
                           tuple(q[k] for k in ("corr", "name", "stream", "start", "end")))
        db.execute("CREATE INDEX api_corr ON api(corr)")
        db.execute("CREATE INDEX scopes_parent ON scopes(parent)")
        primary = Counter(tuple(q[k] for k in ("corr", "name", "stream", "start", "end", "scope", "phase"))
                          for q in lines(folder / "MAPPED_ACTIVITY.jsonl") if q["kind"] == "kernel")
        independent = Counter(db.execute(JOIN, (request,)))
        need(independent and independent == primary, "SQL and primary exact request-kernel link multisets")
        proof = read(folder / "TRACE_REVIEW.json")
        need(proof["status"] == "PASS" and not proof["unmapped_request_or_unresolved_time_records"] and
             sum(counts.values()) == proof["original_activity_records"], "exact export totals and zero unresolved request records")
        phase_counts = Counter()
        q8_verify = Counter()
        final_digest = hashlib.sha256()
        for row, count in sorted(independent.items()):
            _, symbol, _, _, _, _, phase = row
            phase_counts[phase] += count
            if phase == "target_verify_s":
                motif = re.search(r"mul_mat_vec_qIL9ggml_type8ELi([1-4])E", symbol)
                if motif:
                    q8_verify[motif.group(1)] += count
            final_digest.update(json.dumps([row, count], separators=(",", ":")).encode() + b"\n")
        need(phase_counts == {phase: v["kernel"] for phase, v in proof["mapped_request_gpu_records_by_phase"].items()
                             if v.get("kernel")}, "kernel counts by phase")
        return {"request_id": request, "actual_kernel_links_confirmed": sum(independent.values()),
                "phase_kernel_counts": phase_counts, "verify_native_Q8_kernel_widths": q8_verify,
                "correlation_multiset_sha256": final_digest.hexdigest(), "analysis": "separate relational join"}
    finally:
        db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    frozen = read(a.run / "DEVICE_FREEZE.json")
    result = {arm: check_arm(a.run / arm, frozen["new_ids"][arm]) for arm in ("C1", "C4")}
    with a.out.open("x", encoding="utf-8", newline="\n") as writer:
        json.dump({"status": "PASS", "arms": result}, writer, indent=2)
        writer.write("\n")
    print(json.dumps({"status": "PASS", "links": {k: r["actual_kernel_links_confirmed"] for k, r in result.items()}}))
