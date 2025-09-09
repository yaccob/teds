#!/usr/bin/env bash
set -euo pipefail

# Build fresh artifacts
python -m pip install -U pip build twine >/dev/null
rm -rf dist
python -m build >/dev/null
twine check dist/*

# Assert artifact contents
python - << 'PY'
import glob, zipfile, tarfile
wheels = glob.glob('dist/*.whl')
sdists = glob.glob('dist/*.tar.gz')
assert wheels and sdists, 'missing artifacts'
def wheel_ok(p):
    with zipfile.ZipFile(p) as z:
        names = set(z.namelist())
        root = {'spec_schema.yaml','teds_compat.yaml'}
        pkg = {'teds_core/spec_schema.yaml','teds_core/teds_compat.yaml'}
        return root <= names or pkg <= names
def sdist_ok(p):
    with tarfile.open(p, 'r:gz') as t:
        names = {m.name.split('/',1)[-1] for m in t.getmembers() if m.isfile()}
        return 'spec_schema.yaml' in names and 'teds_compat.yaml' in names
assert all(wheel_ok(w) for w in wheels), 'wheel missing required resources'
assert any(sdist_ok(s) for s in sdists), 'sdist missing required resources'
print('artifact content OK')
PY

# Use a temp venv outside the repo to avoid polluting the workspace
tmpdir=$(mktemp -d 2>/dev/null || mktemp -d -t teds-pkg-smoke)
python -m venv "$tmpdir/venv"
. "$tmpdir/venv/bin/activate"
python -m pip install -U pip >/dev/null
pip install --no-cache-dir dist/*.whl >/dev/null

# Version line
teds --version | sed -n '1p'

# Resource loads
python - << 'PY'
from teds_core.resources import read_text_resource as r
assert r('spec_schema.yaml')
assert r('teds_compat.yaml')
print('resource load OK')
PY

# verify demo; expect rc=1
set +e
teds verify demo/sample_tests.yaml --output-level warning > "$tmpdir/out.yaml"
rc=$?
set -e
echo "verify rc: $rc"
test "$rc" -eq 1

# generate smoke
teds generate demo/sample_schemas.yaml
test -f demo/sample_schemas.tests.yaml

deactivate || true
rm -rf "$tmpdir"
echo "package smoke OK"
