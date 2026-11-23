"""Independent HSSDKV1 reader and exact complete C1/C4 comparison."""

import hashlib
from pathlib import Path
import struct

import numpy as np

from trace_review import need, read


def new_items(arm_dir, expect):
    native = read(arm_dir / "request/native.json")
    found = {(int(g), role): obj for g, entries in native["checkpoints"].items() for role, obj in entries.items()}
    need(found.keys() == expect.keys(), "actual checkpoint keys differ from frozen coverage")
    store = (arm_dir / "objects").resolve()
    checked = {}
    for key, current in found.items():
        reference = expect[key]
        need(current["sha256"] == reference["historical_canonical_sha256"], f"frozen canonical identity at {key}")
        if reference["coverage"] == "INACTIVE_MARKER":
            need(key == (1, "draft") and current.get("initialized") is False and "payload" not in current,
                 "inactive draft marker")
            checked[key] = (current, None)
            continue
        need(current["bytes"] == reference["payload_bytes_each"] and
             current["pending_position"] == reference["pending_position"] and
             current["active_tokens"] == reference["active_positions"], f"metadata at {key}")
        path = Path(current["payload"]).resolve(strict=True)
        need(path.parent == store and path.name == current["sha256"] + ".kv" and path.stat().st_size == current["bytes"],
             f"bound complete checkpoint payload {key}")
        checked[key] = (current, path)
    return native, checked


def parse(data, receipt, role):
    """Decode the full canonical container including all active K and V values."""
    def unpack(fmt, at):
        size = struct.calcsize(fmt)
        need(at + size <= len(data), "canonical field truncated")
        return struct.unpack_from(fmt, data, at), at + size

    need(data[:8] == b"HSSDKV1\x00", "canonical container identity")
    (n, pending, position), off = unpack("<Iii", 8)
    need((n, pending, position) == tuple(receipt[k] for k in ("active_tokens", "pending_id", "pending_position")),
         "canonical header positions/pending")
    need(n == position and n > 0 and tuple(struct.unpack_from(f"<{n}i", data, off)) == tuple(range(n)),
         "all logical active positions")
    off += n * 4
    (transposed, layers, k_rq, v_rq), off = unpack("<IIII", off)
    need(transposed in (0, 1) and k_rq == v_rq == 0, "canonical F16 active layout")
    count, feature = (32, 1024) if role == "target" else (16, 512)
    need(layers == count, "canonical full layers")
    total = 0
    for kind in ("K", "V"):
        for layer in range(layers):
            (dtype,), off = unpack("<i", off)
            need(dtype == 1, f"F16 dtype at {kind}/{layer}")
            if kind == "V" and transposed:
                (scalar_bytes, columns), off = unpack("<II", off)
                need((scalar_bytes, columns) == (2, feature), "transposed V shape")
            else:
                (row_bytes,), off = unpack("<Q", off)
                need(row_bytes == feature * 2, f"full feature width at {kind}/{layer}")
            end = off + 2 * n * feature
            need(end <= len(data), f"incomplete tensor bytes at {kind}/{layer}")
            # IEEE binary16: an all-one exponent is Inf/NaN. Inspect every stored element.
            words = np.frombuffer(data, dtype="<u2", count=n * feature, offset=off)
            need(not np.any((words & 0x7C00) == 0x7C00), f"nonfinite canonical {kind}/{layer}")
            off = end
            total += n * feature
    need(off == len(data), "canonical trailing bytes")
    return {"layers": layers, "active_positions": n, "K_shape": [layers, n, feature],
            "V_shape": [layers, feature, n] if transposed else [layers, n, feature],
            "V_transposed": bool(transposed), "f16_values_checked": total, "finite": "FINITE"}


def check_complete(run, checkpoints, terminal_references, oracle):
    expected = {(r["generation"], r["role"]): r for r in checkpoints}
    current = {arm: new_items(run / arm, expected) for arm in ("C1", "C4")}
    for key, (left, a) in sorted(current["C1"][1].items()):
        generation, role = key
        right, b = current["C4"][1][key]
        if a is None:
            need(b is None and left == right, "inactive draft marker equality")
            continue
        need(b is not None and not a.samefile(b), f"independent capture files at {key}")
        one, two = a.read_bytes(), b.read_bytes()
        actual = hashlib.sha256(one).hexdigest()
        need(actual == hashlib.sha256(two).hexdigest() == left["sha256"] == right["sha256"] and one == two,
             f"raw canonical bytes differ at {key}")
        shape_one, shape_two = parse(one, left, role), parse(two, right, role)
        need(shape_one == shape_two and left["active_tokens"] == 757 + generation - 1 and
             all(expected[key][k] == value for k, value in shape_one.items()),
             f"pair/full-sequence shape at {key}")
        if generation == 128:
            origin = terminal_references[role]
            need(not origin.samefile(a) and not origin.samefile(b) and one == origin.read_bytes(),
                 "terminal canonical payload vs independently stored reference")
            for arm, path in (("C1", a), ("C4", b)):
                state = current[arm][0][role + "_endpoint"]
                need(Path(state["payload"]).samefile(path) and state["sha256"] == actual,
                     "terminal export and generation 128 alias")
    transitions = {}
    frozen_tx = oracle["transactions"]
    for arm in ("C1", "C4"):
        native, items = current[arm]
        tx = native["transactions"]
        need(len(tx) == 38 and tx == frozen_tx, "actual own successor transactions vs independent reference")
        hops = []
        for cur, nxt in zip(tx, tx[1:]):
            generation = cur["G"]
            successor = (nxt["seed"], nxt["base"])
            need((cur["pending"], cur["keep"]) == successor and all(
                (items[generation, role][0]["pending_id"], items[generation, role][0]["pending_position"]) == successor
                for role in ("target", "draft")
            ), "captured active state must feed exact own successor")
            hops.append({"generation": generation, "successor_cycle": nxt["cycle"]})
        transitions[arm] = hops
    return transitions
