"""Read archived equality/checkpoint metadata. No accelerator, replay or downloads."""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

import csv
import gzip
import hashlib
import io
import itertools
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT = HERE / "inputs"
PHASE = ["LOCAL_PRIMARY", "LOCAL_CONTINUATION"]


def load(name):
    data = (INPUT / name).read_bytes()
    return json.loads(gzip.decompress(data) if name.endswith(".gz") else data)


def runs(items):
    return [{"value": v, "start": g[0][0], "stop": g[-1][0]+1} for v, it in
            itertools.groupby(enumerate(items), key=lambda iv: iv[1]) for g in [list(it)]]


def evidence():
    manifest = json.loads((HERE / "INPUTS.json").read_bytes())
    for name, meta in manifest["local_files"].items():
        data = (INPUT / name).read_bytes()
        assert len(data) == meta["bytes"] and hashlib.sha256(data).hexdigest() == meta["sha256"], name
    # Native comparison: one full (model, weight descriptor, q, route) object.
    rtx = load("rtx_operands.json.gz")
    widths, cells = set(), defaultdict(list)
    ops = set()
    mats_example = defaultdict(set)
    models = sorted({d["model"] for d in rtx})
    for d in rtx:
        name = d["descriptor"]["weight"]["name"]
        assert (d["model"], name) not in ops
        ops.add((d["model"], name))
        scalar = {r["q"]: r["sha"] for r in d["routes"] if r["route"] == "scalar"}
        for r in d["routes"]:
            q = r["q"]
            widths.add(q)
            if r["route"] == "scalar":
                continue
            equal = r["sha"] == scalar[q]
            assert equal == r["scalar_equal"]
            cells[q, r["route"]].append(equal)
            if q == 8:
                mats_example[r["route"]].add(r["matmuls"])
    rates = [{"q": q, "route": k, "n": len(cells[q,k]), "different": cells[q,k].count(False)}
             for q in sorted(widths) for k in ("wide","tile","packed")]
    matmuls = {k: list(sorted(v)) for k,v in mats_example.items()}
    assert matmuls == {"wide":[1], "tile":[2], "packed":[1]}
    assert len(ops) == 16 and len(models) == 2
    # Vulkan before/after: retain every output position, input and arm.
    vk, references = {}, {}
    for stage in ("before", "after"):
        receipt = load("b570_"+stage+".json.gz")
        rows = defaultdict(dict)
        refs = {}
        for cell in receipt["cells"]:
            root, arm = cell["input_id"], cell["arm"]
            vv = sorted(cell["vectors"], key=lambda z:z["output_index"])
            assert [v["output_index"] for v in vv] == list(range(len(vv)))
            assert all(v["bitwise_equal"] == (v["actual_sha256"] == v["reference_sha256"]) for v in vv)
            assert cell["all_committed_full_vectors_equal"] == all(v["bitwise_equal"] for v in vv)
            assert root not in rows[arm]
            rows[arm][root] = [v["bitwise_equal"] for v in vv]
            refs[arm,root] = [v["reference_sha256"] for v in vv]
        references[stage] = refs
        vk[stage] = dict(rows)
    assert references["before"] == references["after"]
    # Same inputs, arms, vector lengths and indexing in both audits.
    arms = list(vk["before"])
    roots = list(vk["before"][arms[0]])
    vk_rows = []
    for a in arms:
        row = {"arm":a}
        for stage in ("before","after"):
            assert list(vk[stage][a]) == roots
            traces = []
            for r in roots:
                obs = vk[stage][a][r]
                assert len(obs) == 128
                # Intervals are half-open; exact output indices are recoverable.
                traces.append({"root":r,"n":len(obs),"unequal":[[i["start"],i["stop"]] for i in runs(obs) if not i["value"]]})
            row[stage] = {"traces":traces, "n":sum(t["n"] for t in traces),
                          "different":sum(b-a for t in traces for a,b in t["unequal"])}
        vk_rows.append(row)
    # #276 counts serve as an independent reconciliation, never as primary chart data.
    comparison = list(csv.DictReader(io.StringIO((INPUT/"paper276_counts.csv").read_text())))
    for r in rates:
        match, = [z for z in comparison if z["study"]=="RTX_historical_width" and z["width"]==str(r["q"]) and z["route"]==r["route"]]
        assert (int(match["total"]), int(match["mismatch"])) == (r["n"],r["different"])
    for r in vk_rows:
        for stage, k in (("before","B570_COMMITTED_REFERENCE_AUDIT-00"),("after","B570_COMBINED_COMMITTED_AUDIT-03")):
            match, = [z for z in comparison if z["study"] == k and z["route"] == r["arm"]]
            assert (int(match["total"]), int(match["mismatch"])) == (r[stage]["n"],r[stage]["different"])
    assert len(comparison) == len(rates) + len(vk_rows)*2
    # Continuation: derive all position, partition, ownership and state marks from
    # actual executions (not from the proposed input plan).
    ref = load("266_LOCAL_receipt.json.gz")
    case = []
    for i, phase in enumerate(PHASE):
        c = ref["calls"][i]
        t = c["trace"]
        assert c["phase"] == phase
        execution, = [g for g in ref["target_executions"] if g["phase"]==phase]
        stages = ["primary","continuation"]
        checkpoint, = [s["proof"] for s in ref["checkpoints"] if s["stage"] == stages[i]+"_commit"]
        tentative, = [s["proof"] for s in ref["checkpoints"] if s["stage"] == stages[i]+"_uncommitted"]
        own = sorted([v for v in ref["owned_vectors"] if v["step"]==i],key=lambda v:v["row"])
        assert [s["row"] for s in own] == list(range(execution["width"]))
        assert all(s["bytes"]==own[0]["bytes"] and s["bytes"]%4==0 for s in own)
        assert c["owned_frontier_sha256"] == own[c["owned_frontier_row"]]["sha256"]
        assert c["owned_frontier_row"] == t["frontier_row"]
        assert t["pending"] == checkpoint["pending_id"] == t["decisions"][t["frontier_row"]]
        assert t["keep"] == checkpoint["active_tokens"] == checkpoint["pending_position"] == checkpoint["positions"]["max"]+1
        n = execution["width"]
        assert n == len(t["proposals"])+1 and t["base"]==execution["position"] and not t["done"]
        assert t["accepted"] == sum(1 for _ in itertools.takewhile(lambda x:x[0]==x[1],zip(t["decisions"],t["proposals"])))
        step = {"phase":phase, "positions":list(range(t["base"],t["base"]+n)), "extent":execution["expected_extents"],
                "q":n,"keep":t["keep"],"pending_position":checkpoint["pending_position"], "pending_id":t["pending"],
                "seed":t["seed"], "kind":t["kind"],"rejected":t["rejected"],"accepted":t["accepted"],
                "frontier":t["frontier_row"],"k":t["k_eff"],"done":t["done"],"n_vocab":own[0]["bytes"]//4,
                "active":checkpoint["positions"],"tentative":tentative["positions"],"outer":{}}
        for pr in ("260","266"):
            for arm in ("SIMPLE","LOCAL"):
                rec = load(f"{pr}_{arm}_receipt.json.gz")
                assert rec["case_id"]=="positive" and rec["root"]==ref["root"] and rec["target_mode"]=="C"
                assert rec["draft_rows"]==0 and rec["prefill_pack4_enabled"] is False and rec["local_lowering"]==arm
                assert rec["calls"][i]["trace"] == t
                assert [z["sha256"] for z in rec["owned_vectors"] if z["step"]==i] == [s["sha256"] for s in own]
                eg = [g for g in rec["target_executions"] if g["phase"]==phase]
                ext = [e for g in eg for e in g["expected_extents"]]
                assert ext == step["extent"]
                widths_ = [g["width"] for g in eg]
                assert [r for g in eg for r in g["requested_rows"]] == list(range(n))
                if arm in step["outer"]:
                    assert widths_ == step["outer"][arm]
                step["outer"][arm] = widths_
                if i == 0 and pr == "266":
                    verified = load(f"266_{arm}_checked.json.gz")["primary_dispatch"]
                    assert verified["physical_projection_widths"]==widths_ and verified["row_extents"]==ext
                if arm=="LOCAL":
                    assert rec["calls"][i]["work"]["graphs_reused"]==0 and rec["calls"][i]["work"]["graphs_built"]==1
        step["runs"] = runs(step["extent"])
        assert [r["stop"]-r["start"] for r in step["runs"]] == step["outer"]["SIMPLE"]
        # Compare the inferred partition to actual per-layer / per-tile trace output.
        for arm in ("SIMPLE","LOCAL"):
            lines = [row["text"] for row in load("266_"+arm+"_view_lines.json.gz")]
            seen = []
            for ln in lines:
                prefix,*items = ln.split()
                v = dict((k,int(n)) for k,n in (item.split("=") for item in items))
                seen.append((prefix,v))
            if arm=="LOCAL":
                tiles = [v for k,v in seen if k=="TPDS_TILE" and v["base"]==t["base"]]
                assert [(v["begin"],v["width"],v["extent"]) for v in tiles] == [(e["start"], e["stop"]-e["start"],e["value"]) for e in step["runs"]]
                fields = [v for k,v in seen if k=="RTX164_ATTN" and v["position"]==t["base"] and v["rows"]==n and v["split"]==1]
                assert {v["layer"] for v in fields} == set(range(checkpoint["layers"]))
            else:
                for e in step["runs"]:
                    fields = [v for k,v in seen if k=="RTX164_ATTN" and v["position"]==t["base"]+e["start"]
                              and v["rows"]==e["stop"]-e["start"] and v["split"]==0 and v["first"]==v["last"]==e["value"]]
                    assert {v["layer"] for v in fields} == set(range(checkpoint["layers"]))
        case.append(step)
    f,s = case
    assert f["keep"]==s["positions"][0] and f["pending_id"]==s["seed"]
    assert f["q"] == s["q"] and max(f["extent"])==max(s["extent"]) and f["extent"]!=s["extent"]
    return {"fig1":{"rtx":{"widths":sorted(widths),"models":models,"operators":sorted({w for m,w in ops}),
                           "counts":rates,"q8_matmuls":matmuls},
                    "vulkan":{"roots":roots,"arms":vk_rows}},
            "fig2":{"root":ref["root"],"case":case,
                    "references":{"views":"266_{LOCAL,SIMPLE}_view_lines.json.gz",
                                  "receipts":["260_SIMPLE_receipt.json.gz","260_LOCAL_receipt.json.gz","266_SIMPLE_receipt.json.gz","266_LOCAL_receipt.json.gz"],
                                  "summary":"Input paths, commits and archive members are bound in INPUTS.json; arrows and schematic encodings in INTEGRATION_NOTES.md."}}}
