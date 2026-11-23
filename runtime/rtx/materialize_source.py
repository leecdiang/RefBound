"""Restore the public base and precisely scoped native C4 additions."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile


def identity(path):
    with path.open("rb") as stream:
        return {"sha256": hashlib.file_digest(stream, "sha256").hexdigest(), "bytes": path.stat().st_size}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    out = args.out.resolve()
    contract = json.loads((here / "PROFILE.json").read_bytes())
    upstream = contract["upstream"]
    archive = args.upstream_archive.resolve()
    require(identity(archive) == {k: upstream[k] for k in ("bytes", "sha256")}, "pinned upstream archive hash/size")
    patch = here / contract["patch"]["path"]
    require(identity(patch) == {k: contract["patch"][k] for k in ("bytes", "sha256")}, "native patch hash/size")
    out.mkdir(parents=True)
    source = out / "source"
    source.mkdir()
    seen = set()
    prefix = "llama.cpp-" + upstream["commit"]
    with tarfile.open(archive, "r:gz") as container:
        for member in container:
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and path.parts and path.parts[0] == prefix and
                    all(x not in {"..", "."} and ":" not in x and "\\" not in x for x in path.parts) and
                    (member.isfile() or member.isdir()), "unsupported upstream archive member")
            if member.isfile():
                relative = PurePosixPath(*path.parts[1:]).as_posix()
                require(relative.lower() not in seen, "duplicate upstream path")
                seen.add(relative.lower())
                destination = source.joinpath(*path.parts[1:])
                destination.parent.mkdir(parents=True, exist_ok=True)
                with container.extractfile(member) as f, destination.open("xb") as g:
                    shutil.copyfileobj(f, g)
    require(len(seen) == contract["historical_source_files"], "exact base member count")
    for rel, entry in contract["patch_files"].items():
        require(identity(source / rel) == entry["upstream"], f"base source identity: {rel}")
    apply = ["git", "-c", "core.autocrlf=false", "-c", "core.eol=lf", "apply"]
    subprocess.run([*apply, "--check", str(patch)], cwd=source, check=True)
    subprocess.run([*apply, str(patch)], cwd=source, check=True)
    for rel, entry in contract["patch_files"].items():
        require(identity(source / rel) == entry["native"], f"patched source identity: {rel}")
    worker = out / "worker"
    worker.mkdir()
    for name, expected in contract["native_worker"].items():
        p = here / "native_src" / name
        require(identity(p) == expected, f"native worker identity: {name}")
        shutil.copyfile(p, worker / name)
    print(json.dumps({"status": "PASS", "files": len(seen), "patched_files": len(contract["patch_files"]),
                      "driver_files": len(contract["native_worker"]), "upstream": upstream["commit"]}))


if __name__ == "__main__":
    main()
