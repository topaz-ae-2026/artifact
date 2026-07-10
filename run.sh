#!/usr/bin/env bash
# Reduced differential corpus runner. Needs GATE_BIN (a langl R0
# binary) and python3 on PATH. For every fixture: check, run the
# interpreter, emit Python, execute the emitted parity artifact, and
# compare its canonical outcome record with the interpreter stdout.
set -u
GATE_BIN="${GATE_BIN:?set GATE_BIN to a langl binary}"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python
cd "$(dirname "$0")"
agree=0; disagree=0
for f in fixtures/*.l; do
  n=$(basename "$f" .l)
  if ! "$GATE_BIN" check "$f" >/dev/null 2>&1; then
    echo "CHECK-FAIL $n"; disagree=$((disagree+1)); continue
  fi
  interp=$("$GATE_BIN" run "$f" 2>/dev/null)
  if [ "$interp" != "$(cat "expected/$n.stdout.txt")" ]; then
    echo "INTERP-DRIFT $n"; disagree=$((disagree+1)); continue
  fi
  "$GATE_BIN" build "$f" --target python --out-dir "_build/$n" >/dev/null 2>&1
  rec=$("$PY" "_build/$n/program.py" </dev/null 2>/dev/null)
  ok=$("$PY" - "$n" "$rec" <<'EOF'
import json, sys
n, rec = sys.argv[1], json.loads(sys.argv[2])
interp = open(f"expected/{n}.stdout.txt", encoding="utf-8").read().splitlines()
good = rec.get("status") == "ok" and rec.get("stdout") == interp and rec.get("fault") is None
print("yes" if good else "no")
EOF
)
  if [ "$ok" = "yes" ]; then agree=$((agree+1)); else echo "DISAGREE $n"; disagree=$((disagree+1)); fi
done
echo "24 fixtures: $agree agree, $disagree disagree"
[ "$disagree" -eq 0 ]
