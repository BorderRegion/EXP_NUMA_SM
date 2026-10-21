#!/usr/bin/env python3
"""Extract byte-preserved git evidence from the five 2026-10-13 campaign packages.

Writes:
  experiments/rtx5080-20261013/<round>/...          (selected members)
  archive/manifests/rtx5080-<asset>.jsonl           (every member + optional git_path)
"""
import hashlib
import json
import os
import sys
import tarfile
import time
import zipfile

SRC = "/home/ws/文档/ChatGPT/EXP_NUMA"
REPO = "/home/ws/work/exp_numa_sm"
STAGE = "experiments/rtx5080-20261013"

# (key, asset filename, kind, archive path, prefix, git subdir, skip fn)
def skip_static(name):
    low = name.lower()
    return low.endswith(".bin") or low.endswith(".npz")

ASSETS = [
    dict(key="render-opportunity",
         asset="CAMPAIGN_PACKAGE_affinity_20261013T064931Z_b2cdc88d.tar.gz",
         kind="tar",
         path=f"{SRC}/artifacts/CAMPAIGN_PACKAGE_affinity_20261013T064931Z_b2cdc88d.tar.gz",
         prefix="EXP_NUMA/",
         subdir="render-opportunity/",
         skip=None),
    dict(key="render-scheduling-v2",
         asset="RTX5080_V2_LOCAL_REPORT_v2_20261013T072225Z.zip",
         kind="zip",
         path=f"{SRC}/affinity-render-5080/artifacts/RTX5080_V2_LOCAL_REPORT_v2_20261013T072225Z.zip",
         prefix="affinity-render-5080/",
         subdir="render-scheduling/v2_20261013T072225Z/",
         skip=None),
    dict(key="render-scheduling",
         asset="RTX5080_COMPLETED_resumed_20261013T0930Z.zip",
         kind="zip",
         path=f"{SRC}/affinity-render-5080/artifacts/RTX5080_COMPLETED_resumed_20261013T0930Z.zip",
         prefix="affinity-render-5080/",
         subdir="render-scheduling/",
         skip=None),
    dict(key="static-affinity",
         asset="STATIC_AFFINITY_5080_COMPLETED_20261013.zip",
         kind="zip",
         path=f"{SRC}/static-affinity-5080/artifacts/STATIC_AFFINITY_5080_COMPLETED_20261013.zip",
         prefix="static-affinity-5080/",
         subdir="static-affinity/",
         skip=skip_static),
    dict(key="static-affinity-causal",
         asset="STATIC_AFFINITY_CAUSAL_COMPLETION_20261013.zip",
         kind="zip",
         path=f"{SRC}/static-affinity-causal-5080/artifacts/STATIC_AFFINITY_CAUSAL_COMPLETION_20261013.zip",
         prefix="static-affinity-causal-5080/",
         subdir="static-affinity-causal/",
         skip=None),
]


def safe_rel(name):
    parts = name.split("/")
    if name.startswith("/") or any(p in ("", ".", "..") for p in parts[:-1]):
        raise SystemExit(f"unsafe archive member: {name!r}")
    return name


def zip_members(zf):
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = safe_rel(info.filename)
        mode = (info.external_attr >> 16) & 0o777
        if not mode:
            mode = 0o644
        mtime_ns = int(time.mktime(time.strptime("%04d-%02d-%02d %02d:%02d:%02d" % info.date_time, "%Y-%m-%d %H:%M:%S"))) * 10**9
        yield name, info.file_size, mode, mtime_ns, info


def tar_members(tf):
    for m in tf.getmembers():
        if not m.isfile():
            continue
        name = safe_rel(m.name)
        yield name, m.size, m.mode & 0o777 or 0o644, int(m.mtime) * 10**9, m


def main():
    total_git = 0
    total_git_files = 0
    report = []
    for spec in ASSETS:
        with (zipfile.ZipFile(spec["path"]) if spec["kind"] == "zip" else tarfile.open(spec["path"], "r:gz")) as arc:
            members = list(zip_members(arc) if spec["kind"] == "zip" else tar_members(arc))
            entries = []
            git_bytes = 0
            git_files = 0
            done = 0
            for name, size, mode, mtime_ns, info in members:
                if not name.startswith(spec["prefix"]):
                    raise SystemExit(f"{name} does not start with {spec['prefix']}")
                suffix = name[len(spec["prefix"]):]
                keep = not (spec["skip"] and spec["skip"](name))
                git_path = f"{STAGE}/{spec['subdir']}{suffix}" if keep else None
                if spec["kind"] == "zip":
                    f = arc.open(info)
                else:
                    f = arc.extractfile(info)
                h = hashlib.sha256()
                dest = os.path.join(REPO, git_path) if keep else None
                if dest:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                out = open(dest + ".tmp", "wb") if keep else None
                try:
                    for chunk in iter(lambda: f.read(4 << 20), b""):
                        h.update(chunk)
                        if out:
                            out.write(chunk)
                finally:
                    if out:
                        out.close()
                    f.close()
                digest = h.hexdigest()
                if out:
                    os.replace(dest + ".tmp", dest)
                    os.chmod(dest, mode)
                    os.utime(dest, ns=(mtime_ns, mtime_ns))
                    git_bytes += size
                    git_files += 1
                entries.append({
                    "path": name,
                    "bytes": size,
                    "mtime_ns": mtime_ns,
                    "mode": mode,
                    "type": "file",
                    "sha256": digest,
                    **({"git_path": git_path} if keep else {}),
                })
                done += size
                if done // (200 << 20) != (done - size) // (200 << 20):
                    print(f"  {spec['key']}: {done/1e6:.0f} MB", flush=True)
        entries.sort(key=lambda e: e["path"])
        manifest = f"{REPO}/archive/manifests/rtx5080-{spec['key']}.jsonl"
        os.makedirs(os.path.dirname(manifest), exist_ok=True)
        with open(manifest, "w") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False, separators=(",", ":")) + "\n")
        rec = dict(asset=spec["asset"], manifest=f"archive/manifests/rtx5080-{spec['key']}.jsonl",
                   members=len(entries), source_bytes=sum(e["bytes"] for e in entries),
                   git_files=git_files, git_bytes=git_bytes)
        report.append(rec)
        total_git += git_bytes
        total_git_files += git_files
        print(f"{spec['key']}: {len(entries)} members, git {git_files} files {git_bytes/1e6:.2f} MB", flush=True)
    print(f"TOTAL git evidence: {total_git_files} files, {total_git/1e6:.2f} MB")
    json.dump(report, open("/home/ws/Documents/Codex/2026-10-21/new-chat-2/work/rtx5080/extract_report.json", "w"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
