#!/usr/bin/env python3
"""Verify the exact distributed file set before local work."""
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent
rows=json.loads((R/'RELEASE_MANIFEST.json').read_text())['files']
for x in rows:
 p=R/x['path']
 if not p.is_file() or p.stat().st_size!=x['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=x['sha256']:
  raise SystemExit('Integrity check failed: '+x['path'])
print(f'PASS: {len(rows)} distributed files verified (manifest identity is bound by the Git commit).')
