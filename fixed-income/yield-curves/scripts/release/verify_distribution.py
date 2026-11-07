#!/usr/bin/env python3
"""Inspect wheel and sdist independently against reviewed source bytes."""
import argparse
import base64
import csv
from email.parser import BytesParser
import io
import json
from pathlib import Path
import re
import stat
import struct
import tomllib
import zipfile

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from verify_source_export import check_names, digest, read_tar, require, MAX_BYTES

WHEEL_METADATA = {'METADATA', 'WHEEL', 'RECORD', 'top_level.txt', 'licenses/LICENSE'}
EGG_METADATA = {'PKG-INFO', 'SOURCES.txt', 'dependency_links.txt', 'requires.txt', 'top_level.txt'}
# Approved C06a financial source identities; packaging cannot substitute modules.
MODULE_SHA256 = {'yield_curves/__init__.py': 'fac0263eb858ec99e4504883e8f2b7279b2f7437af8820440bd706e0beba5258',
 'yield_curves/baseline.py': '0d3412feeebc8cdadee286bc313fb75873b0ff5c3dfb9668587f640bbdb12035',
 'yield_curves/bootstrap.py': 'aa3af90c52b29afece650a86ddc93b9623ae04b76ab82e00045ef323ebc572a0',
 'yield_curves/calendar_io.py': '27dd07ecafb5db9fa912010ae69084ba7ea56fa8d96f06e8fdc738f360c6eef0',
 'yield_curves/calendars.py': '298b98e64302b5e9605c7672475936b922358438c9bfa7b5ef027f57dbba8a2b',
 'yield_curves/calibration.py': 'ff8f0577a5813ba27ef345e416f95a06bcde0b5d1589a4a812ec95e5cbf3e26e',
 'yield_curves/conventions.py': 'ccde47d40f6b354b7cfac71eecd5765c21971a650681a0b88f57c22496e2d944',
 'yield_curves/curves.py': '80c52fed72ebe5cec76609443607a9ac86d8d6232c341e916a8b3637f568fddd',
 'yield_curves/date_grids.py': '200c1ccaaa6b9c9d0524b3222759a0be25fe2bea17ec5fb43e9c7a25dee82910',
 'yield_curves/diagnostics.py': '371368bad745d09da07d7091eda19834fed4a7f885b1a9beade234ef117b88bc',
 'yield_curves/engine_capabilities.py': 'e4569740c789651f0a4c59eeb4428879940bc372e3a4a2ac97882ba6b3f8f54b',
 'yield_curves/execution.py': '7f514d35ea43453e7eb9853b4f2ad44d91435fbfd83b34943a62377b26e626da',
 'yield_curves/inputs.py': '24685efb9f6f8b1530b5dffd408995dd0b00181ef0b8e7ae26773a1d8e17b13e',
 'yield_curves/instruments.py': 'af3057f3c304c66c251f973ee53444e90b45550fd4b4f916802bd556c63df608',
 'yield_curves/log_linear_diagnostics.py': '3ec0473e1f1b6485252ea5d3de3fc6dcbe1a9633cec77715647a6ca92ee12697',
 'yield_curves/observations.py': '8adc90762b4c3085a185c530c4ad7ebc16f9a7d5ee593176f6ed2b426c624213',
 'yield_curves/pricing.py': 'b430aa2cc2c685263b220fc01706d44e1b0de5caa6ca5dc872799d6f05aeef1d',
 'yield_curves/quote_io.py': 'eeecab76e2066a5adca2e2b7dc81359b71ad228cf752f04ecddd3daa85cefb0c',
 'yield_curves/quotes.py': 'b895768abf079e7550d04f8a1e5f5da1ab3df702ad193d0c1836bed41d159f6b',
 'yield_curves/repricing.py': '3d1c6c8bca429f59eb1a9657cc634c163123762197d09a2bac8b46056b3a6c9a',
 'yield_curves/research/__init__.py': '56ca2f6016c7f414dad7b04ba1847fae6298b9b0136821f4cb37e89017050467',
 'yield_curves/research/calendars.py': '4d4b739eec76a8413f25947c321930da26c56774290c8b0f2079ebed1b5103b5',
 'yield_curves/research/curves.py': '112ea1c4a50d99d3d972cf1ad94f24fad27de954b69c5dd0aad749e3c3ed8478',
 'yield_curves/research/diagnostics.py': 'b626a829933b8b63991f5b9e040028bd52d56ea1639763bbcaa4b0b72bfd9d75',
 'yield_curves/research/global_sensitivity.py': 'c2d195f328b912ca474b9fb2e34387e52ce27616ab7e347ad1a32148f29eb9b0',
 'yield_curves/research/recovery.py': '03829a45a352c35c0c00151f140549f518d90a1a2a01a9bae29d37f4d36ceab4',
 'yield_curves/research/sensitivity.py': 'a8a74cfc2cc468763e584acad6046d46ae9184639439b4ccbb9a096e2f0505ca',
 'yield_curves/research/synthetic.py': 'f4faffb632238f9842576c6697caa53703cc7c929d799db118241cfabe268140',
 'yield_curves/research/validation.py': '09fd2cb11079626b178e09879049f3420559edd48b17dd6a0e113ecbbfe3706c',
 'yield_curves/schedules.py': '697720d76a4bf9f75ce7d749809638adf056e0490ed5c44a7b1194db65a78ad2',
 'yield_curves/snapshot_assurance.py': '52aa5416a569d6dfb1d75a9a4be84bdaf999ad5ec04a807a79dc7b4563843b49',
 'yield_curves/snapshots.py': '3c88a4f8ce5fa50f8f30f574152b8135b2412507a445522f8baa70ef6f24a6a5',
 'yield_curves/tenors.py': 'df0787d93d991d9d0db4e9344ce2cd802902754676481cece7ce21d789cf7174',
 'yield_curves/tooling/__init__.py': '21bc326c329b49b0bfa34c0488aa6240ed609ed4e7176612086e3535d309f767',
 'yield_curves/tooling/cli_inputs.py': '013f5ec677e0a06f2ac90e7e38175f2c23225564f4fd3df373014717c7061ed5',
 'yield_curves/tooling/project_paths.py': '5c8fdcc044aac4d30bfe696901f9ae992484c7700dcbd09ab4a3c76b510b1599',
 'yield_curves/tooling/reference_candidates.py': 'bbb83b49f09e12e70a2477175f5c418c97ff6780a1ff59962b940d5093555976',
 'yield_curves/tooling/reporting.py': '55cf16b1765eb512f86ca60cbba86ae26cfc44f4a7d11dbfc492e41c3702e527'}
SOURCE_METADATA = {'pyproject.toml', 'MANIFEST.in', 'README.md', 'CHANGELOG.md', 'LICENSE'}


def read_wheel(path):
    files = {}
    total = 0
    require(path.stat().st_size <= MAX_BYTES, 'wheel input size limit')
    raw = path.read_bytes()
    require(len(raw) >= 22 and raw[-22:-18] == b'PK\x05\x06', 'wheel trailing payload/comment')
    end = struct.unpack('<4s4H2LH', raw[-22:])
    require(end[1] == end[2] == end[7] == 0 and end[3] == end[4] and end[5] + end[6] + 22 == len(raw), 'noncanonical wheel directory')
    position = 0
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        require(len(infos) <= 10000 and len(infos) == end[4], 'wheel member count')
        names = [i.filename for i in infos]
        # A list is necessary here: constructing a dict first would hide duplicates.
        check_names(names)
        for info in infos:
            require(info.header_offset == position and not info.extra and not info.comment and not info.flag_bits & 8, 'unreviewed wheel header/gap')
            position += 30 + len(info.filename.encode('utf-8')) + info.compress_size
            mode = info.external_attr >> 16
            require(not info.is_dir() and stat.S_IFMT(mode) in (0, stat.S_IFREG), 'wheel nonregular member')
            require(not mode & 0o7000 and not info.flag_bits & 1, 'special wheel permissions or encryption')
            total += info.file_size
            require(0 <= info.file_size <= MAX_BYTES and total <= MAX_BYTES, 'wheel size limit')
            files[info.filename] = archive.read(info)
    require(position == end[6], 'unreviewed wheel prefix/padding')
    return files


def requirement_key(text):
    req = Requirement(text)
    require(req.url is None, 'absolute/machine dependency URL')
    return (req.name.lower().replace('_', '-'), tuple(sorted(req.extras)), str(req.specifier), str(req.marker))


def verify_metadata(data, source, project):
    meta = BytesParser().parsebytes(data)
    def one(key, expected):
        require(meta.get_all(key) == [expected], f'metadata {key} mismatch')
    one('Metadata-Version', '2.4')
    one('Name', project['name'])
    one('Version', project['version'])
    one('Summary', project['description'])
    # Specifier order is not meaningful; source order is preserved by setuptools 79.
    require(len(meta.get_all('Requires-Python', [])) == 1 and SpecifierSet(meta['Requires-Python']) == SpecifierSet(project['requires-python']), 'metadata Requires-Python mismatch')
    one('License-Expression', 'MIT')
    one('License-File', 'LICENSE')
    one('Description-Content-Type', 'text/markdown')
    one('Author', project['authors'][0]['name'])
    one('Keywords', ','.join(project['keywords']))
    require(meta.get_all('Dynamic', []) == ['license-file'], 'unknown dynamic metadata')
    require(set(meta.get_all('Classifier', [])) == set(project['classifiers']), 'classifiers mismatch')
    require(set(meta.get_all('Project-URL', [])) == {f'{k}, {v}' for k, v in project['urls'].items()}, 'project URLs mismatch')
    extras = project['optional-dependencies']
    require(sorted(meta.get_all('Provides-Extra', [])) == sorted(extras), 'extras mismatch')
    expected = project['dependencies'] + [f'{r}; extra == "{extra}"' for extra, reqs in extras.items() for r in reqs]
    actual = meta.get_all('Requires-Dist', [])
    require(sorted(map(requirement_key, actual)) == sorted(map(requirement_key, expected)), 'dependencies mismatch')
    # Compare raw UTF-8 payload; email's legacy ASCII decoder loses Unicode.
    require(data.partition(b'\n\n')[2] == (source / 'README.md').read_bytes(), 'description mismatch')
    return meta


def verify_record(files, prefix):
    record = prefix + '/RECORD'
    rows = list(csv.reader(io.StringIO(files[record].decode('utf-8'))))
    require(all(len(r) == 3 for r in rows), 'invalid RECORD row')
    names = [r[0] for r in rows]
    require(len(names) == len(set(names)) and set(names) == set(files), 'incomplete/duplicate RECORD')
    for name, encoded, size in rows:
        if name == record:
            require(encoded == size == '', 'RECORD self entry')
        else:
            expected = base64.urlsafe_b64encode(__import__('hashlib').sha256(files[name]).digest()).rstrip(b'=').decode()
            require(encoded == 'sha256=' + expected and size == str(len(files[name])), 'corrupted RECORD: ' + name)


def safety_scan(files):
    pattern = re.compile(rb'(/home/[^\s/]+/|/Users/[^\s/]+/|[A-Za-z]:\\Users\\|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16})')
    for name, data in files.items():
        require(not pattern.search(data), 'private/machine content in ' + name)


def verify(source, wheel, sdist, expected_version):
    cfg = tomllib.loads((source / 'pyproject.toml').read_text())
    project = cfg['project']
    require(project['name'] == 'yield-curves' and project['version'] == expected_version == '0.1.0', 'version identity')
    modules = {p.relative_to(source / 'src').as_posix(): p.read_bytes() for p in (source / 'src/yield_curves').rglob('*.py')}
    require(len(modules) == 38, '38 source modules required')
    require({n: digest(b) for n, b in modules.items()} == MODULE_SHA256, 'approved module source identity mismatch')
    require({n.rsplit('/', 1)[0] for n in modules if n.endswith('/__init__.py')} == {'yield_curves', 'yield_curves/research', 'yield_curves/tooling'}, 'package identity')
    prefix = f'yield_curves-{expected_version}.dist-info'
    root = f'yield_curves-{expected_version}'
    require(wheel.name == root + '-py3-none-any.whl', 'wheel filename/tag')
    require(sdist.name == root + '.tar.gz', 'sdist filename')
    wf = read_wheel(wheel)
    require(set(wf) == set(modules) | {prefix + '/' + n for n in WHEEL_METADATA}, 'unexpected/missing wheel members')
    for name, data in modules.items():
        require(wf[name] == data, 'wheel source hash mismatch: ' + name)
    verify_metadata(wf[prefix + '/METADATA'], source, project)
    require(wf[prefix + '/licenses/LICENSE'] == (source / 'LICENSE').read_bytes(), 'wheel license mismatch')
    require(wf[prefix + '/top_level.txt'] == b'yield_curves\n', 'wheel top-level metadata')
    wm = BytesParser().parsebytes(wf[prefix + '/WHEEL'])
    require(wm.get_all('Wheel-Version') == ['1.0'] and wm.get_all('Root-Is-Purelib') == ['true'] and wm.get_all('Tag') == ['py3-none-any'], 'WHEEL tag/format')
    require(list(wm.keys()) == ['Wheel-Version', 'Generator', 'Root-Is-Purelib', 'Tag'] and wm['Generator'] == 'setuptools (79.0.1)', 'unknown WHEEL metadata')
    verify_record(wf, prefix)
    raw = read_tar(sdist)
    require(all(n.startswith(root + '/') for n in raw), 'sdist root mismatch')
    sf = {n[len(root) + 1:]: data for n, data in raw.items()}
    egg = 'src/yield_curves.egg-info/'
    required = {'src/' + n for n in modules} | SOURCE_METADATA | {'PKG-INFO', 'setup.cfg'} | {egg + n for n in EGG_METADATA}
    require(set(sf) == required, 'unexpected/missing sdist members')
    for name in SOURCE_METADATA | {'src/' + n for n in modules}:
        require(sf[name] == (source / name).read_bytes(), 'sdist source hash mismatch: ' + name)
    verify_metadata(sf['PKG-INFO'], source, project)
    require(sf[egg + 'PKG-INFO'] == sf['PKG-INFO'], 'stale sdist metadata')
    require(sf['setup.cfg'] == b'[egg_info]\ntag_build = \ntag_date = 0\n\n', 'unknown generated setup.cfg')
    require(sf[egg + 'dependency_links.txt'] == b'\n', 'unexpected dependency links')
    require(sf[egg + 'top_level.txt'] == b'yield_curves\n', 'sdist top-level metadata')
    req_lines = project['dependencies'] + ['', '[dev]', *project['optional-dependencies']['dev'], '', '[plots]', *project['optional-dependencies']['plots']]
    require(sf[egg + 'requires.txt'].decode().splitlines() == req_lines, 'stale requires.txt')
    source_list = sf[egg + 'SOURCES.txt'].decode().splitlines()
    require(len(source_list) == len(set(source_list)), 'duplicate SOURCES entries')
    require(set(source_list) == required - {'PKG-INFO', 'setup.cfg'}, 'stale/unreviewed SOURCES.txt')
    safety_scan(wf)
    safety_scan(sf)
    def inventory(path, files):
        return {'filename': path.name, 'sha256': digest(path.read_bytes()), 'bytes': path.stat().st_size,
                'members': {n: {'sha256': digest(b), 'bytes': len(b)} for n, b in sorted(files.items())}}
    return {'status': 'PASS', 'version': expected_version, 'module_count': 38,
            'wheel': inventory(wheel, wf), 'sdist': inventory(sdist, sf)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'wheel', 'sdist', 'expected-version', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        result = verify(Path(args.source), Path(args.wheel), Path(args.sdist), args.expected_version)
    except Exception as exc:
        Path(args.output).write_text(json.dumps({'status': 'FAIL', 'gate': str(exc)}, indent=2) + '\n')
        raise
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
