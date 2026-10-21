#!/usr/bin/env python3
"""Verify RTX 5080 evidence and release assets without executing archived code."""
import argparse
import hashlib
import json
import subprocess
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'archive/rtx5080/INDEX.json'


def digest_file(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def check_file(path, size, sha):
    if path.is_symlink() and not path.exists():
        raise ValueError(f'Missing target: {path}')
    if path.stat().st_size != size or digest_file(path) != sha:
        raise ValueError(f'File hash or size mismatch: {path}')


def safe_name(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError(f'Unsafe archive path: {name}')


def check_member(name, size, stream, expected, seen):
    safe_name(name)
    if name not in expected or name in seen:
        raise ValueError(f'Unexpected or duplicate member: {name}')
    row = expected[name]
    if size != row['bytes']:
        raise ValueError(f'Member size mismatch: {name}')
    h = hashlib.sha256()
    with stream:
        for chunk in iter(lambda: stream.read(4 << 20), b''):
            h.update(chunk)
    if h.hexdigest() != row['sha256']:
        raise ValueError(f'Member hash mismatch: {name}')
    seen.add(name)


def verify_archive(record, assets, expected):
    segments = record.get('parts') or [{
        'asset': record['asset'], 'bytes': record['compressed_bytes'],
        'sha256': record['sha256'],
    }]
    paths = []
    for segment in segments:
        path = assets / segment['asset']
        check_file(path, segment['bytes'], segment['sha256'])
        paths.append(path)
    seen = set()
    kind = record['format']
    if kind == 'zip':
        with zipfile.ZipFile(paths[0]) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                check_member(member.filename, member.file_size,
                             archive.open(member), expected, seen)
    elif kind == 'tar.gz':
        with tarfile.open(paths[0], 'r:gz') as archive:
            for member in archive:
                if member.isdir():
                    continue
                if not member.isfile():
                    raise ValueError(f'Unsupported member type: {member.name}')
                check_member(member.name, member.size, archive.extractfile(member), expected, seen)
    elif kind == 'tar.zst':
        cat = subprocess.Popen(['cat', '--', *map(str, paths)], stdout=subprocess.PIPE)
        proc = subprocess.Popen(['zstd', '-q', '-d', '-c'], stdin=cat.stdout,
                                stdout=subprocess.PIPE)
        cat.stdout.close()
        try:
            with tarfile.open(fileobj=proc.stdout, mode='r|') as archive:
                for member in archive:
                    if member.isdir():
                        continue
                    if not member.isfile():
                        raise ValueError(f'Unsupported member type: {member.name}')
                    check_member(member.name, member.size, archive.extractfile(member), expected, seen)
            # A streaming tar reader can stop before the final compression frame.
            while proc.stdout.read(1 << 20):
                pass
            if proc.wait() != 0 or cat.wait() != 0:
                raise ValueError('Archive decompression failed')
        finally:
            proc.stdout.close()
            for child in (proc, cat):
                if child.poll() is None:
                    child.kill()
                child.wait()
    else:
        raise ValueError(f'Unsupported format: {kind}')
    if seen != set(expected):
        raise ValueError(f'Missing archive members: {record["asset"]}')
    return len(seen)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path)
    parser.add_argument('--git-only', action='store_true')
    parser.add_argument('--only', help='Logical archive filename')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.git_only and args.assets is None:
        parser.error('provide --assets or --git-only')
    index = json.loads(INDEX.read_text())
    records = [r for r in index['archives'] if not args.only or r['asset'] == args.only]
    if not records:
        parser.error('unknown --only archive')
    report = {'git_files_verified': 0, 'archives_verified': 0,
              'archive_members_verified': 0, 'gpu_experiments_run': 0}
    for record in records:
        rows = [json.loads(line) for line in (ROOT / record['manifest']).read_text().splitlines()]
        expected = {row['path']: row for row in rows}
        if len(expected) != len(rows):
            raise ValueError('Duplicate manifest paths')
        for row in rows:
            if 'git_path' in row:
                safe_name(row['git_path'])
                check_file(ROOT / row['git_path'], row['bytes'], row['sha256'])
                report['git_files_verified'] += 1
        if not args.git_only:
            count = verify_archive(record, args.assets, expected)
            report['archives_verified'] += 1
            report['archive_members_verified'] += count
        print('verified', record['asset'], flush=True)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
