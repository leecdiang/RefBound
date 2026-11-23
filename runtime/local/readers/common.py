"""The input checks and canonical JSON digest used by the frozen KV reader."""
import hashlib
import json


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(data.encode()).hexdigest()


def hexsha(value, label="sha256"):
    need(isinstance(value, str) and len(value) == 64 and
         all(c in "0123456789abcdef" for c in value), label)
    return value
