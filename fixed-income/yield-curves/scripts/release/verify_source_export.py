#!/usr/bin/env python3
"""Validate Git bytes and archive structure before any extraction (stdlib only)."""
import argparse
import hashlib
import json
import io
import gzip
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tarfile
import unicodedata

MAX_BYTES = 256 * 1024 * 1024
FORBIDDEN = {'.git', '.venv', '__pycache__', 'build', 'dist', '.task-checkpoints'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    require(isinstance(name, str) and name and len(name) <= 1024, 'invalid member name')
    require(not any(ord(c) < 32 or ord(c) == 127 for c in name), 'control character in path')
    require('\\' not in name and ':' not in name, 'path alias or drive path')
    require(not name.startswith('/') and not name.endswith('/'), 'absolute or noncanonical path')
    require(all(p not in ('', '.', '..') for p in name.split('/')), 'traversal or alias path')
    require(str(PurePosixPath(name)) == name, 'noncanonical path')
    return unicodedata.normalize('NFC', name).casefold()


def check_names(entries):
    seen = set()
    for name in entries:
        key = safe_name(name)
        require(key not in seen, f'duplicate/aliased member: {name}')
        seen.add(key)
    for name in entries:
        parents = PurePosixPath(name).parents
        require(not any(unicodedata.normalize('NFC', str(p)).casefold() in seen for p in parents if str(p) != '.'), 'file/directory collision')


def read_tar(path):
    files, dirs, aliases = {}, set(), set()
    total = 0
    require(path.stat().st_size <= MAX_BYTES, 'archive input size limit')
    with path.open('rb') as stream:
        compressed = stream.read(2) == b'\x1f\x8b'
    opener = gzip.open if compressed else open
    with opener(path, 'rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, 'expanded archive size limit')
    end = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
        for member in archive:
            require(len(aliases) < 10000, 'too many archive members')
            name = member.name.rstrip('/') if member.isdir() else member.name
            key = safe_name(name)
            require(key not in aliases, f'duplicate/aliased member: {name}')
            aliases.add(key)
            require(not member.pax_headers or set(member.pax_headers) <= {'mtime'}, 'unreviewed PAX metadata')
            require(not member.mode & 0o7000, 'special permission bits')
            end = member.offset_data + ((member.size + 511) // 512) * 512
            if member.isdir():
                dirs.add(name)
                continue
            require(member.isreg() and not member.issparse(), f'nonregular archive member: {name}')
            total += member.size
            require(0 <= member.size <= MAX_BYTES and total <= MAX_BYTES, 'archive size limit')
            files[name] = archive.extractfile(member).read()
    require(len(raw) % 512 == 0 and len(raw) - end >= 1024 and not any(raw[end:]), 'noncanonical/trailing tar payload')
    check_names(files)
    require(not set(files) & dirs, 'file/directory collision')
    require(all(any(n.startswith(d + '/') for n in files) for d in dirs), 'unexpected empty directory')
    return files


def archive_shape(data):
    # Git <2.38 archives tree objects using wall-clock mtime. Compare all other
    # headers to a fresh canonical Git export and require one uniform timestamp.
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
        members = archive.getmembers()
    require(len({m.mtime for m in members}) == 1, 'nonuniform clean Git archive timestamp')
    return [(m.name, m.type, m.mode, m.uid, m.gid, m.uname, m.gname,
             m.linkname, m.size, m.pax_headers) for m in members]


def normalized_git_archive(data):
    archive_shape(data)
    normalized = bytearray(data)
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
        for member in archive:
            require(not member.pax_headers, 'unreviewed Git export extended headers')
            # Tarfile validates header checksums before this comparison. Erase
            # only the timestamp and dependent checksum; retain padding, member
            # order, spare fields and all trailing bytes for exact comparison.
            offset = member.offset
            normalized[offset + 136:offset + 148] = b'0' * 12
            normalized[offset + 148:offset + 156] = b'0' * 8
    return bytes(normalized)


def git(repo, *args):
    return subprocess.check_output(['git', '--no-optional-locks', '-C', str(repo), *args])


def tracked(repo, revision, subtree, expected_tree):
    require(re.fullmatch(r'[0-9a-f]{40}', revision) is not None, 'full commit SHA required')
    safe_name(subtree)
    require(git(repo, 'rev-parse', '--verify', revision + '^{commit}').decode().strip() == revision, 'commit identity')
    tree = git(repo, 'rev-parse', revision + ':' + subtree).decode().strip()
    require(tree == expected_tree and re.fullmatch(r'[0-9a-f]{40}', tree), 'tree identity mismatch')
    files = {}
    for row in git(repo, 'ls-tree', '-rz', tree).split(b'\0'):
        if not row:
            continue
        header, raw = row.split(b'\t', 1)
        mode, kind, blob = header.decode().split()
        name = raw.decode('utf-8')
        safe_name(name)
        require(mode in ('100644', '100755') and kind == 'blob', 'unapproved Git object type')
        require(not any(part in FORBIDDEN or part.endswith(('.egg-info', '.dist-info')) for part in PurePosixPath(name).parts), 'inherited build/editable metadata')
        files[name] = git(repo, 'cat-file', 'blob', blob)
    check_names(files)
    return files


def verify_directory(root, expected, mutable=False):
    actual = {}
    for p in root.rglob('*'):
        require(not p.is_symlink(), 'source symlink')
        if p.is_dir():
            continue
        require(stat.S_ISREG(p.stat().st_mode), 'source nonregular file')
        name = p.relative_to(root).as_posix()
        if mutable and name.startswith('src/yield_curves.egg-info/'):
            require(name.split('/')[-1] in {'PKG-INFO', 'SOURCES.txt', 'dependency_links.txt', 'requires.txt', 'top_level.txt'} and len(name.split('/')) == 3, 'unknown generated metadata')
            continue
        if mutable and name.startswith('build/lib/'):
            require('src/' + name[len('build/lib/'):] in expected and p.read_bytes() == expected['src/' + name[len('build/lib/'):]], 'unexpected generated build payload')
            continue
        actual[name] = p.read_bytes()
    require(actual == expected, 'unexpected source modifications or file set')


def export(repo, revision, subtree, tree, archive, destination, receipt):
    repo_root = Path(repo).resolve()
    require(all(not p.resolve().is_relative_to(repo_root) for p in (archive, destination, receipt)), 'export outputs must stay outside Git')
    expected = tracked(repo, revision, subtree, tree)
    require(read_tar(archive) == expected, 'archive differs from tracked Git content')
    # Enforce canonical Git archive structure/modes; tree-export mtime is not a
    # commit timestamp. Archive bytes and tracked-file hashes are both receipted.
    canonical = git(repo, 'archive', '--format=tar', revision + ':' + subtree)
    require(normalized_git_archive(archive.read_bytes()) == normalized_git_archive(canonical), 'not a clean Git archive')
    require(not destination.exists(), 'destination must be new')
    destination.mkdir(parents=True)
    # No tar extraction API is used; all members have already passed validation.
    for name, data in expected.items():
        p = destination / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    verify_directory(destination, expected)
    for p in destination.rglob('*'):
        p.chmod(0o555 if p.is_dir() else 0o444)
    destination.chmod(0o555)
    result = {'status': 'PASS', 'commit': revision, 'tree': tree,
              'archive_sha256': digest(archive.read_bytes()), 'git_tree_archive_mtime': 'uniform execution timestamp; excluded from header comparison',
              'files': {n: digest(b) for n, b in expected.items()}}
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'revision', 'subtree', 'expected-tree', 'archive', 'destination', 'receipt'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--check-directory', type=Path)
    parser.add_argument('--mutable-build', action='store_true')
    args = parser.parse_args()
    if args.check_directory:
        verify_directory(args.check_directory, tracked(args.repo, args.revision, args.subtree, args.expected_tree), args.mutable_build)
    else:
        export(args.repo, args.revision, args.subtree, args.expected_tree,
               Path(args.archive), Path(args.destination), Path(args.receipt))


if __name__ == '__main__':
    main()
