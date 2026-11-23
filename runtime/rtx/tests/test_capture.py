"""Synthetic input and CUDA correlation checks. No GPU or benchmark data."""

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "capture"))
from run_pair import prompt_ids
from trace_review import bind, group, history


class CaptureTests(unittest.TestCase):
    def test_public_receipts(self):
        subprocess.run([sys.executable, ROOT / "verify.py", "--quick"], check=True)

    def test_local_input_rejects_digest_and_boolean(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "local.json"
            data = [9, 18, 27]
            path.write_text(json.dumps(data), encoding="utf-8")
            expected = {"tokens": 3, "sha256": hashlib.sha256(b"[9,18,27]").hexdigest()}
            self.assertEqual(prompt_ids(path, expected), data)
            path.write_text("[9,18,28]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA256"):
                prompt_ids(path, expected)
            path.write_text("[9,18,true]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "shape"):
                prompt_ids(path, expected)

    def test_correlation_requires_same_thread_and_launch_api(self):
        root = {"id": 1, "parent": 0, "kind": "request", "name": "synthetic", "pid": 1,
                "tid": 20, "start": 10, "end": 80}
        forward = {**root, "id": 2, "parent": 1, "kind": "forward", "name": "target_verify_s",
                   "start": 20, "end": 65}
        export = {**forward, "id": 3, "parent": 2, "kind": "kv_export", "name": "checkpoint",
                  "start": 30, "end": 60}
        scopes = {x["id"]: x for x in (root, forward, export)}
        links = defaultdict(set, {5: {3}})
        event = {"kind": "kernel", "corr": 5}
        api = {"kind": "driver", "api": "cuLaunchKernel", "pid": 1, "tid": 20, "start": 40, "end": 50, "result": 0}
        pair, reason = bind(event, links, {5: [api]}, scopes)
        self.assertIsNone(reason)
        self.assertEqual(group(list(history(pair[0], scopes)))[0], "kv_export")
        for wrong in ({"tid": 21}, {"start": 29}, {"api": "cuMemAlloc"}):
            pair, _ = bind(event, links, {5: [{**api, **wrong}]}, scopes)
            self.assertIsNone(pair)
        links[5].add(2)
        self.assertEqual(bind(event, links, {5: [api]}, scopes), (None, "ambiguous_external"))


if __name__ == "__main__":
    unittest.main()
