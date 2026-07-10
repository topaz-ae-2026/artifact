# Language L LMPL 2026 Artifact

## Overview

This anonymous artifact contains the complete corpora, stored experimental
records, replay analyses, and pinned Windows executables for the LMPL 2026
evaluation of language L as a closed authoring boundary. Numeric diagnostic
suffixes and all experimental measurements are unchanged.

The text assets use the review names language L, the `L52xx`/`L5002`/
`L5298`/`L5299` diagnostic family, release R0, and hosted Endpoint A.
See `BLINDING.md` before comparing textual records with direct executable
output.

## Requirements

- Windows x64 for the supplied `bin/gate-r0.exe` and
  `bin/gate-r0b1.exe` executables.
- Python 3.11 or newer.
- Bash for the reduced differential-corpus runner.
- No network access for corpus checks or stored-record replay.
- Optional Study D re-execution additionally requires `CODEX_BIN`, access to
  hosted Endpoint A, and the run configuration preserved in the cell records.

Paths passed through environment variables may be absolute at execution time;
no machine-specific absolute paths are stored in the artifact.

## Layout

- `fixtures/`, `expected/`, `run.sh`: 24-program differential corpus.
- `pilot/`: frozen 24-task capability corpus, references, transcripts,
  records, and analysis.
- `refusal/`: Study A refusal cases, smoke cases, structured-record checker,
  and stored results.
- `seeded/`: Study B seeded-defect cases and Study D repair-ablation records,
  replay, and analysis.
- `ablation/`: Study C conditions, stored outcomes, replay, and codebook.
- `worked-example/`: compact worked reproduction.
- `bin/`: two pinned, byte-preserved release executables.
- `MANIFEST.sha256`: SHA-256 manifest for every other output file.

## Quickstart and expected outputs

The following examples are PowerShell one-liners run from the artifact root.

### Study A: refusal conformance and structured records

```powershell
$env:GATE_BIN="$PWD/bin/gate-r0.exe"; $env:GATE_R0_BIN=$env:GATE_BIN; python refusal/build_refusal_suite.py; if ($LASTEXITCODE -eq 0) { python refusal/structured_conformance.py }
```

Expected refusal result: 15/15 capability cases plus 2/2 nested cases are
rejected, while 0/15 controls are rejected. The structured-record checker
covers 9 properties and reports 17/17 conforming checks.

### Study B: seeded-defect rerun

```powershell
$env:GATE_BIN="$PWD/bin/gate-r0.exe"; $env:GATE_R0_BIN=$env:GATE_BIN; python seeded/seeded_defect_study.py
```

Expected capability coverage is 24/24, with the frozen 5/5/5/5/4 by 8/8/8
balance preserved.

### Study D: repair-ablation replay

```powershell
python seeded/analyze_repair_ablation.py
python seeded/reclassify_removal.py
```

The first command replays the stored cell records with the archived
conservative lexical metric. The second reclassifies every stored cell
and recomputes the paper's main-analysis post-repair L52xx-absence
outcome. See `study-d-plan.md` for the prespecification record and the
construct-correction rationale. The two headline contrasts are:

| Stored headline contrast | Estimate | Stored interval |
|---|---:|---:|
| policy-text minus generic-diagnostic, post-repair L52xx absence | +13.9 pp | [5.6, 23.6] pp |
| policy-text minus generic-diagnostic, other-registered-family substitution | -13.9 pp | [-23.6, -5.6] pp |

The stored records are sufficient for replay. Re-execution is optional and
requires a configured `CODEX_BIN` plus access to hosted Endpoint A:

```powershell
$env:CODEX_BIN="codex"; python seeded/repair_ablation.py
```

Fresh samples need not be byte-identical to the stored samples.

### Study C: stored-outcome replay

```powershell
python ablation/analyze_ablation.py
```

The exact stored acceptance fields are:

| Stored acceptance field | Exact value |
|---|---:|
| `conditions.examples-only.draft0_accept` | 100.0 |
| `conditions.full.draft0_accept` | 100.0 |
| `conditions.grammar-static.draft0_accept` | 97.2 |
| `conditions.none.draft0_accept` | 58.3 |

### Reduced differential corpus

```powershell
$env:GATE_BIN="$PWD/bin/gate-r0.exe"; bash ./run.sh
```

Expected result:

```text
24 fixtures: 24 agree, 0 disagree
```

## Model and run-configuration disclosure

The hosted model identity is deliberately not pseudonymized. Cell records
identify `gpt-5.6-sol` exactly and preserve `model_reasoning_effort`, client
and CLI version identifiers, endpoint-independent run configuration, token
usage, timestamps, seeds, responses, diagnostics, and outcomes. The review
label for the service location is hosted Endpoint A.
