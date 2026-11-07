#!/usr/bin/env bash
# Tier A/B/C tooling. Only C06b2 may use these receipts for candidate verification.
set -euo pipefail
usage() {
  cat <<'EOF'
Usage: run_release_validation.sh --repo ABS --revision FULL_SHA --expected-tree TREE_SHA
       --expected-version 0.1.0 --external-root NEW_ABS --approval REVIEW_ID
       [--tier A|B|C]

Requires a reviewed immutable commit and its independently reviewed project tree.
Creates only external exports, build copies, environments, wheelhouses and receipts.
A = full non-slow + package/import gates; B = exactly 27 slow in one session;
C = distribution and independent installed-consumer validation. Never publishes.
EOF
}
REPO='' REVISION='' EXPECTED_TREE='' VERSION='' BASE='' APPROVAL='' TIER=C
while (($#)); do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --repo) REPO=${2:?}; shift 2 ;;
    --revision) REVISION=${2:?}; shift 2 ;;
    --expected-tree) EXPECTED_TREE=${2:?}; shift 2 ;;
    --expected-version) VERSION=${2:?}; shift 2 ;;
    --external-root) BASE=${2:?}; shift 2 ;;
    --approval) APPROVAL=${2:?}; shift 2 ;;
    --tier) TIER=${2:?}; shift 2 ;;
    *) usage >&2; exit 2 ;;
  esac
done
[[ "$REVISION" =~ ^[0-9a-f]{40}$ && "$EXPECTED_TREE" =~ ^[0-9a-f]{40}$ ]]
[[ "$VERSION" == 0.1.0 && "$TIER" =~ ^[ABC]$ && -n "$APPROVAL" ]]
[[ "$REPO" == /* && "$BASE" == /* && ! -e "$BASE" ]]
REPO=$(realpath "$REPO")
BASE=$(realpath -m "$BASE")
[[ "$BASE" != "$REPO" && "$BASE" != "$REPO/"* ]]
SUBTREE=fixed-income/yield-curves
BOOTSTRAP=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# Before using checkout helpers, compare every executed helper and this script to
# the explicitly approved commit. An archive cannot supply its own trust anchor.
for helper in run_release_validation.sh verify_source_export.py verify_distribution.py consumer_smoke.py verify_test_selection.py; do
  git --no-optional-locks -C "$REPO" show "$REVISION:$SUBTREE/scripts/release/$helper" | cmp - "$BOOTSTRAP/$helper"
done
[[ $(git --no-optional-locks -C "$REPO" rev-parse "$REVISION^{commit}") == "$REVISION" ]]
[[ $(git --no-optional-locks -C "$REPO" rev-parse "$REVISION:$SUBTREE") == "$EXPECTED_TREE" ]]
# Remove pip configuration inputs before choosing a single provisioning source.
for variable in ${!PIP_@} ${!PYTHON@}; do unset "$variable"; done
unset PYTHONPATH PYTHONHOME PYTHONUSERBASE PYTHONSTARTUP PYTHONINSPECT PYTEST_ADDOPTS PYTEST_PLUGINS VIRTUAL_ENV
export PIP_CONFIG_FILE=/dev/null PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_INPUT=1
export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg
mkdir -p "$BASE"/{source,artifacts,build-wheelhouse,runtime-wheelhouse,envs,results,logs,tmp,caches,consumers/wheel,consumers/sdist,public}
export TMPDIR="$BASE/tmp" XDG_CACHE_HOME="$BASE/caches/xdg" MPLCONFIGDIR="$BASE/caches/mpl" PIP_CACHE_DIR="$BASE/caches/pip"
export SOURCE_DATE_EPOCH
SOURCE_DATE_EPOCH=$(git --no-optional-locks -C "$REPO" show -s --format=%ct "$REVISION")
STATUS=INCOMPLETE
finish() {
  local code=$?
  trap - EXIT
  python3.11 -B - "$BASE" "$REPO" "$REVISION" "$EXPECTED_TREE" "$TIER" "$STATUS" "$code" "$APPROVAL" <<'PY'
import json, pathlib, re, sys
base, repo, commit, tree, tier, status, code, approval = sys.argv[1:]
b = pathlib.Path(base)
(b/'results/attempt.json').write_text(json.dumps(dict(commit=commit,tree=tree,tier=tier,status=status,exit_code=int(code),approval=approval,release_approval=False),indent=2)+'\n')
# Publish only receipts/logs. Never upload source exports, venvs or private staging.
for directory in ('results', 'logs'):
    for p in (b/directory).rglob('*'):
        if not p.is_file() or p.suffix not in ('.json', '.log', '.xml', '.txt'):
            continue
        target = b/'public'/directory/p.relative_to(b/directory)
        target.parent.mkdir(parents=True, exist_ok=True)
        text = p.read_text(errors='replace').replace(base, '$RUN_ROOT').replace(repo, '$REPOSITORY')
        text = re.sub(r'''(?<![:/\w])/(?:home|Users|tmp|usr|opt|var|runner|mnt)/[^\s"'<>]+''', '$ABSOLUTE_PATH', text)
        target.write_text(text)
PY
  exit "$code"
}
trap finish EXIT
run_log() {
  local label=$1
  shift
  printf '%q ' "$@" >> "$BASE/logs/commands.log"
  printf '\n' >> "$BASE/logs/commands.log"
  "$@" > "$BASE/logs/$label.stdout.log" 2> "$BASE/logs/$label.stderr.log"
}
python3.11 -I -B - <<'PY'
import platform, sys
assert platform.python_version() == '3.11.15', 'reference patch required'
assert sys.platform == 'linux' and platform.machine() == 'x86_64', 'Linux x86_64 lock required'
assert tuple(map(int,platform.libc_ver()[1].split('.'))) >= (2,34), 'glibc >=2.34 required'
PY
git --no-optional-locks -C "$REPO" archive --format=tar --output="$BASE/source/project.tar" "$REVISION:$SUBTREE"
run_log source-export python3.11 -B "$BOOTSTRAP/verify_source_export.py" --repo "$REPO" --revision "$REVISION" \
  --subtree "$SUBTREE" --expected-tree "$EXPECTED_TREE" --archive "$BASE/source/project.tar" \
  --destination "$BASE/source/immutable" --receipt "$BASE/results/source-export.json"
SOURCE="$BASE/source/immutable"
cp -a "$SOURCE" "$BASE/build-src"
cp -a "$SOURCE" "$BASE/test-project"
chmod -R u+w "$BASE/build-src" "$BASE/test-project"
python3.11 -m venv "$BASE/envs/tools"
TOOLS="$BASE/envs/tools/bin/python"
# Hash-check every wheel download, then install entirely offline. The bootstrap
# pip is from CPython ensurepip; the reviewed pip replaces it before further work.
run_log build-download "$TOOLS" -m pip download --index-url https://pypi.org/simple --no-cache-dir --only-binary=:all: --require-hashes -r "$SOURCE/requirements/release-build.txt" -d "$BASE/build-wheelhouse"
run_log runtime-download "$TOOLS" -m pip download --index-url https://pypi.org/simple --no-cache-dir --only-binary=:all: --require-hashes -r "$SOURCE/requirements/ci-reference.txt" -d "$BASE/runtime-wheelhouse"
run_log tools-install "$TOOLS" -m pip install --no-index --find-links "$BASE/build-wheelhouse" --require-hashes -r "$SOURCE/requirements/release-build.txt" --report "$BASE/logs/tools-install.json"
export PIP_NO_INDEX=1 PIP_FIND_LINKS="$BASE/build-wheelhouse"
# Revalidate the exact wheelhouse set and hashes before isolated backend resolution.
"$TOOLS" -B - "$SOURCE" "$BASE" <<'PY'
import hashlib,json,pathlib,re,sys
source,base=map(pathlib.Path,sys.argv[1:]); result={}
for lock,folder in [('release-build','build-wheelhouse'),('ci-reference','runtime-wheelhouse')]:
    pins=re.findall(r'^([^#\s]+)==([^\s]+) --hash=sha256:([0-9a-f]{64})$',(source/'requirements'/f'{lock}.txt').read_text(),re.M)
    actual={hashlib.sha256(p.read_bytes()).hexdigest():p.name for p in (base/folder).glob('*.whl')}
    assert len(actual)==len(pins) and set(actual)=={h for _,_,h in pins}, 'wheelhouse mismatch'
    result[lock]=actual
(base/'results/wheelhouses.json').write_text(json.dumps(result,indent=2)+'\n')
PY
# Default build creates sdist first and wheel FROM that sdist, with fresh backend
# environments, offline. No candidate wheel is placed in a dependency wheelhouse.
run_log build "$TOOLS" -B -m build -v --outdir "$BASE/artifacts" "$BASE/build-src"
WHEEL="$BASE/artifacts/yield_curves-$VERSION-py3-none-any.whl"
SDIST="$BASE/artifacts/yield_curves-$VERSION.tar.gz"
[[ $(find "$BASE/artifacts" -maxdepth 1 -type f | wc -l) == 2 ]]
run_log distribution "$TOOLS" -B "$BOOTSTRAP/verify_distribution.py" --source "$SOURCE" --wheel "$WHEEL" --sdist "$SDIST" --expected-version "$VERSION" --output "$BASE/results/distribution.json"
run_log twine "$TOOLS" -m twine check --strict "$WHEEL" "$SDIST"
"$TOOLS" -B - "$WHEEL" "$SDIST" "$BASE/results/SHA256SUMS.txt" <<'PY'
import hashlib,pathlib,sys
paths=list(map(pathlib.Path,sys.argv[1:]))
paths[-1].write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in paths[:-1]))
PY
# Runtime-only lock is derived from reviewed hash pins, never pip constraints on
# the unhashed local artifact. Install dependencies first, verify candidate hash,
# then install the explicit local artifact with --no-deps and no hash constraints.
"$TOOLS" -B - "$SOURCE/requirements/ci-reference.txt" "$BASE/runtime-only.txt" <<'PY'
import pathlib,sys
lines=pathlib.Path(sys.argv[1]).read_text().splitlines()
pathlib.Path(sys.argv[2]).write_text('\n'.join(l for l in lines if l.startswith(('numpy==','scipy==')))+'\n')
PY
for consumer in wheel sdist; do
  python3.11 -m venv "$BASE/envs/$consumer"
  PY="$BASE/envs/$consumer/bin/python"
  run_log "$consumer-dependencies" "$TOOLS" -m pip --python "$PY" install --no-index --find-links "$BASE/runtime-wheelhouse" --require-hashes -r "$BASE/runtime-only.txt" --report "$BASE/logs/$consumer-dependencies.json"
  ARTIFACT="$WHEEL"
  [[ "$consumer" != sdist ]] || ARTIFACT="$SDIST"
  "$TOOLS" -B - "$BASE/results/distribution.json" "$consumer" "$ARTIFACT" <<'PY'
import hashlib,json,pathlib,sys
assert hashlib.sha256(pathlib.Path(sys.argv[3]).read_bytes()).hexdigest()==json.loads(pathlib.Path(sys.argv[1]).read_text())[sys.argv[2]]['sha256']
PY
  # PEP 517 isolation remains enabled for sdist; the backend can resolve only
  # preverified build wheels. Full verbose logs retain backend package versions.
  run_log "$consumer-install" "$TOOLS" -m pip --python "$PY" install -v --no-cache-dir --no-deps --report "$BASE/logs/$consumer-install.json" "$ARTIFACT"
  run_log "$consumer-check" "$TOOLS" -m pip --python "$PY" check
  run_log "$consumer-freeze" "$TOOLS" -m pip --python "$PY" freeze --all
  run_log "$consumer-inspect" "$TOOLS" -m pip --python "$PY" inspect
  cp "$BOOTSTRAP/consumer_smoke.py" "$BASE/consumers/$consumer/smoke.py"
  (
    cd "$BASE/consumers/$consumer"
    run_log "$consumer-smoke" "$PY" -I -B smoke.py --expected-prefix "$BASE/envs/$consumer" --expected-version "$VERSION" --forbid-root "$REPO" --forbid-root "$SOURCE" --forbid-root "$BASE/build-src" --forbid-root "$BASE/test-project" --output "$BASE/results/$consumer-consumer.json"
  )
done
if [[ "$TIER" != C ]]; then
  python3.11 -m venv "$BASE/envs/test"
  TEST_PY="$BASE/envs/test/bin/python"
  run_log test-dependencies "$TOOLS" -m pip --python "$TEST_PY" install --no-index --find-links "$BASE/runtime-wheelhouse" --require-hashes -r "$SOURCE/requirements/ci-reference.txt" --report "$BASE/logs/test-dependencies.json"
  run_log test-install "$TOOLS" -m pip --python "$TEST_PY" install --no-deps --no-cache-dir "$WHEEL"
  run_log test-check "$TOOLS" -m pip --python "$TEST_PY" check
  run_log test-inspect "$TOOLS" -m pip --python "$TEST_PY" inspect
  run_log numerical-backend "$TEST_PY" -I -B -c 'import numpy,scipy,os,platform; print(platform.platform()); print("cpu_count",os.cpu_count()); print("numpy",numpy.__version__,"scipy",scipy.__version__); numpy.show_config(); scipy.show_config()'
  SELECTION=non-slow
  [[ "$TIER" != B ]] || SELECTION=slow
  run_log financial-tests "$TEST_PY" -B "$BOOTSTRAP/verify_test_selection.py" --project "$BASE/test-project" --revision "$REVISION" --selection "$SELECTION" --output "$BASE/results/tests"
  run_log gate-tests "$TEST_PY" -B -m pytest -q "$SOURCE/scripts/release/tests/test_distribution_gate.py" -p no:cacheprovider --basetemp="$BASE/tmp/gate-tests" --junitxml="$BASE/results/gate-tests.xml"
fi
run_log tools-check "$TOOLS" -m pip check
run_log tools-inspect "$TOOLS" -m pip inspect
run_log environment "$TOOLS" -B -c 'import json,os,platform,sys; print(json.dumps(dict(python=platform.python_version(),platform=platform.platform(),machine=platform.machine(),libc=platform.libc_ver(),implementation=sys.implementation.name,runner_image=os.getenv("ImageOS"),runner_image_version=os.getenv("ImageVersion"),runner_arch=os.getenv("RUNNER_ARCH"))));'
for directory in "$SOURCE" "$BASE/build-src" "$BASE/test-project"; do
  EXTRA=()
  [[ "$directory" != "$BASE/build-src" ]] || EXTRA=(--mutable-build)
  run_log "source-integrity-$(basename "$directory")" python3.11 -B "$BOOTSTRAP/verify_source_export.py" --repo "$REPO" --revision "$REVISION" --subtree "$SUBTREE" --expected-tree "$EXPECTED_TREE" --archive "$BASE/source/project.tar" --destination "$SOURCE" --receipt "$BASE/results/source-export.json" --check-directory "$directory" "${EXTRA[@]}"
done
run_log final-distribution "$TOOLS" -B "$BOOTSTRAP/verify_distribution.py" --source "$SOURCE" --wheel "$WHEEL" --sdist "$SDIST" --expected-version "$VERSION" --output "$BASE/results/final-distribution.json"
cmp "$BASE/results/distribution.json" "$BASE/results/final-distribution.json"
STATUS=PASS
