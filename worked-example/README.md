# Worked example

The paper's worked trace, machine-verified against release R0.

- `badness.l` - the accepted program. `langl check` reports
  resolve-ok and types-ok. `langl run` prints the content of
  `expected-interpreter-stdout.txt`.
- `badness-nearmiss.l` - the same program with the return expression
  replaced by a call to `eval`. The checker rejects it with the
  diagnostic in `expected-nearmiss-diagnostic.txt` (L5002, `eval` is
  not bound).
- `emitted-python/` - the parity artifact written by
  `langl build badness.l --target python`. Executing `program.py`
  emits the canonical outcome record in
  `expected-python-outcome-record.json`.
