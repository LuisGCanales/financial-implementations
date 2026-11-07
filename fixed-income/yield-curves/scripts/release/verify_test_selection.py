#!/usr/bin/env python3
"""Run or collect the exact reviewed financial suite; retain complete attempt receipts."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from verify_source_export import require

# C05/C06a sorted node IDs, UTF-8, one LF after every ID. Counts alone are insufficient.
IDENTITIES = {'all': {'count': 1035,
         'sha256': '386dc7256b02d588f5afd8a6a739456f8a8b99629c3c4a614c123588227cc10c'},
 'non-slow': {'count': 1008,
              'sha256': '525da27e4ab479acba8a8691e61ab100f2a423c24c7dc1f13d8c1b98b91c161e'},
 'slow': {'count': 27,
          'sha256': '04e6b605cce70ad3aec87f587eadb342c9a1864b604193fdd25d3fd3ace91371'}}


def identity(nodes):
    require(len(nodes) == len(set(nodes)), 'duplicate node IDs')
    return {'count': len(nodes), 'sha256': hashlib.sha256(('\n'.join(sorted(nodes)) + '\n').encode()).hexdigest()}


def validate_selection(rows):
    all_ids = [r['nodeid'] for r in rows]
    slow = [r['nodeid'] for r in rows if r['slow']]
    normal = [r['nodeid'] for r in rows if not r['slow']]
    for label, nodes in [('all', all_ids), ('slow', slow), ('non-slow', normal)]:
        require(identity(nodes) == IDENTITIES[label], 'reviewed selection mismatch: ' + label)
    require(not set(slow) & set(normal) and set(slow) | set(normal) == set(all_ids), 'partition mismatch')


def validate_outcomes(selected, phases, exit_code):
    require(set(phases) == set(selected), 'incomplete or substituted outcome set')
    for node in selected:
        reports = phases[node]
        require([r['when'] for r in reports] == ['setup', 'call', 'teardown'], 'incomplete test protocol: ' + node)
        require(all(r['outcome'] == 'passed' and not r['xfail'] for r in reports), 'unexpected test outcome: ' + node)
    require(exit_code == 0, 'nonzero pytest exit')


def classify_attempt(selected, phases, code):
    if code < 0 or code == 2 or set(phases) != set(selected):
        return 'INCOMPLETE'
    for node in selected:
        reports = phases[node]
        if not reports or reports[0]['when'] != 'setup' or reports[-1]['when'] != 'teardown':
            return 'INCOMPLETE'
        if reports[0]['outcome'] == 'passed' and 'call' not in [r['when'] for r in reports]:
            return 'INCOMPLETE'
    return 'FAIL'


def validate_junit(path, selected):
    root = ET.parse(path).getroot()
    cases = root.findall('.//testcase')
    expected = {tuple(n.rsplit('::', 1)) for n in selected}
    mapping = {(file.removesuffix('.py').replace('/', '.'), name) for file, name in expected}
    actual = [(c.get('classname'), c.get('name')) for c in cases]
    require(len(actual) == len(set(actual)) and set(actual) == mapping, 'JUnit incomplete/substituted outcomes')
    require(not root.findall('.//error') and not root.findall('.//failure') and not root.findall('.//skipped'), 'JUnit unexpected outcome')


class Recorder:
    def __init__(self):
        self.rows = []
        self.phases = {}

    def pytest_collection_finish(self, session):
        self.rows = [{'nodeid': item.nodeid, 'slow': item.get_closest_marker('slow') is not None} for item in session.items]

    def pytest_runtest_logreport(self, report):
        self.phases.setdefault(report.nodeid, []).append({
            'when': report.when, 'outcome': report.outcome,
            'xfail': hasattr(report, 'wasxfail'), 'duration': report.duration})


def worker(args):
    import pytest
    recorder = Recorder()
    try:
        code = int(pytest.main(json.loads(args.pytest_args), plugins=[recorder]))
    finally:
        Path(args.worker_output).write_text(json.dumps({'rows': recorder.rows, 'phases': recorder.phases}) + '\n')
    return code


def run(project, selection, output, revision, collect_only=False):
    require(not output.exists(), 'new attempt directory required')
    output.mkdir(parents=True)
    modules = sorted((project / 'tests').rglob('test_*.py'))
    functions = sum(sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test_') for n in ast.walk(ast.parse(p.read_text()))) for p in modules)
    require(len(modules) == 38 and functions == 414, 'test source identity mismatch')
    actual_revision = subprocess.check_output(['git', '-C', str(project), 'rev-parse', 'HEAD'], text=True).strip() if (project / '.git').exists() else revision
    require(actual_revision == revision and len(revision) == 40 and all(c in '0123456789abcdef' for c in revision), 'full candidate SHA required')
    commands = []
    started = time.time()
    receipt = {'status': 'INCOMPLETE', 'commit': revision, 'selection': selection, 'collect_only': collect_only,
               'commands': commands, 'started_epoch': started, 'python': platform.python_version(), 'machine': platform.machine(),
               'cpu_count': os.cpu_count(), 'physical_memory_bytes': os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')}
    code = 1
    try:
        for phase in (['collect'] if collect_only else ['collect', 'run']):
            pytest_args = ['tests', '-p', 'no:cacheprovider', '--strict-config', '--strict-markers']
            if phase == 'collect':
                pytest_args += ['--collect-only', '-q']
            else:
                pytest_args += ['-vv', '--durations=25', '--junitxml=' + str(output / 'junit.xml'), '--basetemp=' + str(output / 'tmp')]
                if selection != 'all':
                    pytest_args += ['-m', 'slow' if selection == 'slow' else 'not slow']
            command = [sys.executable, '-B', str(Path(__file__).resolve()), '--worker-output', str(output / (phase + '.json')), '--pytest-args', json.dumps(pytest_args)]
            env = os.environ.copy()
            env.pop('PYTHONPATH', None)
            env.pop('PYTHONHOME', None)
            env.pop('PYTEST_ADDOPTS', None)
            env.pop('PYTEST_PLUGINS', None)
            env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONDONTWRITEBYTECODE='1', MPLBACKEND='Agg', MPLCONFIGDIR=str(output / 'mpl'), XDG_CACHE_HOME=str(output / 'cache'), TMPDIR=str(output / 'temp'))
            (output / 'temp').mkdir(exist_ok=True)
            with (output / (phase + '.stdout.log')).open('w') as stdout, (output / (phase + '.stderr.log')).open('w') as stderr:
                before = time.time()
                proc = subprocess.run(command, cwd=project, env=env, stdout=stdout, stderr=stderr)
            code = proc.returncode
            commands.append({'argv': command, 'pytest_argv': pytest_args, 'exit_code': code, 'duration_seconds': time.time() - before, 'stdout': phase + '.stdout.log', 'stderr': phase + '.stderr.log'})
            data = json.loads((output / (phase + '.json')).read_text())
            if phase == 'collect':
                validate_selection(data['rows'])
                require(code == 0, 'collection failed')
                selected = [r['nodeid'] for r in data['rows'] if selection == 'all' or r['slow'] == (selection == 'slow')]
                receipt['node_ids'] = selected
            else:
                require([r['nodeid'] for r in data['rows']] == selected, 'execution selection mismatch')
                validate_outcomes(selected, data['phases'], code)
                validate_junit(output / 'junit.xml', selected)
        receipt['status'] = 'COLLECTION_ONLY' if collect_only else 'PASS'
        return 0
    except Exception as exc:
        receipt['gate'] = str(exc)
        # A zero/failed process with missing outcomes still represents an incomplete attempt.
        if 'data' in locals() and 'selected' in locals() and set(data.get('phases', {})) == set(selected):
            receipt['status'] = classify_attempt(selected, data.get('phases', {}), code)
        return 1
    finally:
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        receipt.update(exit_code=code, duration_seconds=time.time() - started,
                       resources={'max_rss_kib': usage.ru_maxrss, 'user_seconds': usage.ru_utime, 'system_seconds': usage.ru_stime},
                       junit='junit.xml' if (output / 'junit.xml').exists() else None)
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--selection', choices=['all', 'non-slow', 'slow'])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--revision')
    parser.add_argument('--collect-only', action='store_true')
    parser.add_argument('--worker-output', help=argparse.SUPPRESS)
    parser.add_argument('--pytest-args', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_output:
        return worker(args)
    require(all((args.project, args.selection, args.output, args.revision)), 'project, selection, output and revision required')
    return run(args.project.resolve(), args.selection, args.output.resolve(), args.revision, args.collect_only)


if __name__ == '__main__':
    sys.exit(main())
