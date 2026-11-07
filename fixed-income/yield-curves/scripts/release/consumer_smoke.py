#!/usr/bin/env python3
"""Exercise the installed baseline contract without checkout data or research imports."""
import argparse
from dataclasses import replace
from datetime import date, timedelta
import hashlib
import importlib
import importlib.metadata as metadata
import inspect
import json
import math
from pathlib import Path
import sys
import sysconfig

EXAMPLE_SHA256 = 'f276abc9a06af5bfceda88db9b1612aa7903462975ce685a6a54c7c326983ea6'
EXAMPLE = 'from datetime import date\nfrom yield_curves.baseline import build_baseline_ftiie_curve\nfrom yield_curves.calendars import BusinessCalendar\nfrom yield_curves.quotes import OISQuote\n\nquotes = (\n    OISQuote("1M", date(2026, 9, 15), date(2026, 10, 19), 0.05),\n    OISQuote("3M", date(2026, 9, 15), date(2026, 12, 17), 0.051),\n)\ncalendar = BusinessCalendar(\n    "WEEKENDS_ONLY_TEACHING_EXAMPLE",\n    holidays=frozenset(),\n    weekend_days=frozenset({5, 6}),\n    coverage_start=date(2026, 1, 1),\n    coverage_end=date(2026, 12, 31),\n)\nresult = build_baseline_ftiie_curve(quotes=quotes, calendar=calendar)\nprint(f"accepted_for_use = {str(result.accepted_for_use).lower()}")\nif not result.accepted_for_use:\n    raise RuntimeError(result.acceptance.issues)\ncurve = result.curve\nquery_date = date(2026, 10, 1)\nforward_end = date(2026, 10, 29)\nassert curve.reference_date <= query_date < forward_end <= curve.node_dates[-1]\nprint("discount_factor =", curve.discount_factor(query_date))\nprint("zero_rate =", curve.zero_rate(query_date))\nprint("forward_rate_28d =", curve.forward_rate(query_date, forward_end))\n'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_origin(path, prefix, forbidden):
    path = Path(path).resolve()
    require(path.is_relative_to(prefix.resolve()) and 'site-packages' in path.parts, 'editable or non-independent module origin')
    require(not any(path.is_relative_to(p.resolve()) for p in forbidden), 'forbidden checkout origin')


def smoke(prefix, version, forbidden):
    require(Path(sys.prefix).resolve() == prefix.resolve() and sys.prefix != sys.base_prefix, 'independent venv required')
    dist = metadata.distribution('yield-curves')
    require(dist.version == version == '0.1.0' and dist.metadata['Name'] == 'yield-curves', 'installed version/name mismatch')
    require(set(dist.requires or []) == {'numpy>=1.24', 'scipy>=1.11.4', 'pytest>=8.0; extra == "dev"', 'matplotlib>=3.7; extra == "plots"'}, 'installed dependencies mismatch')
    require(set(dist.metadata.get_all('Provides-Extra', [])) == {'dev', 'plots'} and not list(dist.entry_points), 'installed extras/entrypoints mismatch')
    require(set(dist.metadata['Requires-Python'].split(',')) == {'>=3.11', '<3.12'} and dist.metadata['License-Expression'] == 'MIT', 'installed metadata mismatch')
    direct = dist.read_text('direct_url.json')
    require(direct is not None and not json.loads(direct).get('dir_info', {}).get('editable', False), 'editable/missing direct origin')
    require('archive_info' in json.loads(direct), 'local reviewed archive installation required')
    require(not list(Path(sysconfig.get_paths()['purelib']).glob('*editable*')), 'editable installation detected')
    from yield_curves.baseline import build_baseline_ftiie_curve, assess_baseline_calibration
    from yield_curves.inputs import BaselineInputError
    from yield_curves.calendars import CalendarCoverageError
    signature = inspect.signature(build_baseline_ftiie_curve)
    require(tuple(signature.parameters) == ('quotes', 'calendar', 'initial_discount_factors'), 'baseline API signature')
    require(all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in signature.parameters.values()) and signature.parameters['initial_discount_factors'].default is None, 'baseline API defaults')
    require(hashlib.sha256(EXAMPLE.encode()).hexdigest() == EXAMPLE_SHA256, 'canonical example changed')
    namespace = {}
    exec(compile(EXAMPLE, '<C05b-public-example>', 'exec'), namespace)
    result, curve, quotes, calendar = (namespace[n] for n in ('result', 'curve', 'quotes', 'calendar'))
    query, end = namespace['query_date'], namespace['forward_end']
    values = [curve.discount_factor(query), curve.zero_rate(query), curve.forward_rate(query, end)]
    require(result.accepted_for_use and all(math.isfinite(v) for v in values) and values[0] > 0 and (end - query).days == 28, 'positive consumer contract')
    rejections = []
    def rejects(label, callback, error):
        try:
            callback()
        except error:
            rejections.append(label)
        else:
            raise ValueError('negative consumer case accepted: ' + label)
    # Input protocol objects avoid constructor guards hiding baseline validation.
    from types import SimpleNamespace
    def quote(**changes):
        return SimpleNamespace(**({'tenor': quotes[1].tenor, 'trade_date': quotes[1].trade_date,
                                   'contractual_maturity_date': quotes[1].contractual_maturity_date,
                                   'par_rate': quotes[1].par_rate} | changes))
    for label, invalid in [('empty-quotes', ()), ('nonfinite-quote', (quotes[0], quote(par_rate=float('nan')))),
                           ('duplicate-quotes', (quotes[0], quotes[0])),
                           ('mixed-dates', (quotes[0], quote(trade_date=date(2026, 9, 16))))]:
        rejects(label, lambda invalid=invalid: build_baseline_ftiie_curve(quotes=invalid, calendar=calendar), BaselineInputError)
    rejects('calendar-coverage', lambda: build_baseline_ftiie_curve(quotes=quotes, calendar=replace(calendar, coverage_end=date(2026, 10, 1))), CalendarCoverageError)
    for vector in ([], [0.99], [0.99, float('nan')], [-1.0, 0.98], [3.0, 0.98]):
        rejects('initial-vector-' + repr(vector), lambda vector=vector: build_baseline_ftiie_curve(quotes=quotes, calendar=calendar, initial_discount_factors=vector), ValueError)
    failed = assess_baseline_calibration(calibration_result=replace(result.calibration_result, success=False), quotes=quotes, calendar=calendar)
    require(not failed.accepted_for_use and 'CALIBRATION_SOLVER_FAILED' in failed.issues, 'solver declaration rejection')
    rejections.append('solver-declaration')
    before, after = curve.reference_date - timedelta(days=1), curve.node_dates[-1] + timedelta(days=1)
    for label, callback in [('discount-before', lambda: curve.discount_factor(before)), ('discount-after', lambda: curve.discount_factor(after)),
                            ('zero-before', lambda: curve.zero_rate(before)), ('zero-after', lambda: curve.zero_rate(after)),
                            ('forward-before', lambda: curve.forward_rate(before, query)), ('forward-after', lambda: curve.forward_rate(query, after)),
                            ('forward-reversed', lambda: curve.forward_rate(end, query))]:
        rejects(label, callback, ValueError)
    # Mutate the actual live spline then require the existing value-binding guard.
    curve._spline_object.c[0, 0] += 0.01
    require(not result.accepted_for_use, 'mutated live binding accepted')
    rejections.append('mutated-live-values')
    origins = {}
    for name, module in list(sys.modules.items()):
        if name == 'yield_curves' or name.startswith('yield_curves.'):
            verify_origin(module.__file__, prefix, forbidden)
            origins[name] = str(Path(module.__file__).relative_to(prefix))
    require(not any(n.startswith(('yield_curves.research', 'yield_curves.tooling')) for n in origins), 'checkout/research dependency')
    return {'status': 'PASS', 'version': dist.version, 'example_sha256': EXAMPLE_SHA256,
            'values': values, 'rejections': rejections, 'module_origins_relative_to_environment': origins,
            'versions': {n: metadata.version(n) for n in ('yield-curves', 'numpy', 'scipy')}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-prefix', required=True, type=Path)
    parser.add_argument('--expected-version', required=True)
    parser.add_argument('--forbid-root', action='append', default=[], type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = smoke(args.expected_prefix, args.expected_version, args.forbid_root)
    except Exception as exc:
        args.output.write_text(json.dumps({'status': 'FAIL', 'gate': str(exc)}) + '\n')
        raise
    args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
