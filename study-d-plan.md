# Study D prespecification record

This file records what was fixed before the first Study D endpoint call,
what was corrected after the run, and where each piece is implemented in
this artifact. It is a faithful transcription of the operator design
brief and its implementation critique, both authored before any model
call. No pre-registration commit hash exists for the plan text itself;
the original operationalization is preserved verbatim as executable code
in this artifact, and the stored per-cell records allow every number in
the paper to be recomputed under either operationalization.

## Prespecified before any model call

- Population: the 24 balanced capability mutants from the seeded-defect
  study, unchanged.
- Conditions: C0 rejection-only, C1 generic-diagnostic (pinned R0
  L5002 payload), C2 policy-text (R0+B1 human diagnostic), C3
  policy-JSON (R0+B1 structured record). Fixed scaffold, one turn,
  three repetitions, deterministic interleaved schedule, seed 52026.
- Primary contrast: C2 minus C1.
- Primary outcomes (conceptual): handling of the injected policy
  request (removal rather than rebinding or substitution) and
  substitution into another registered family. Gate acceptance,
  hidden-oracle correctness, and cost were prespecified as reported
  secondary outcomes.
- All other contrasts (C1 minus C0, C3 minus C2) secondary.

## Original operationalization (pre-call, implemented in repair_ablation.py)

```
excluded_removed :=
      no L52xx diagnostic in the post-repair gate run
  AND no unresolved registered name
  AND no surviving bare registered-name use (conservative lexical scan)
```

## Post-run construct correction (implemented in reclassify_removal.py)

A post-run construct audit found that the lexical conjunction
misclassifies a registered spelling that ordinary resolution legitimately
binds locally, or that sits inert in non-code text, as a failure. By the
exact-shadow semantics validated in Study A, such references are
policy-compliant. Four of 288 stored outputs were affected (three in C1,
one in C0), biasing the original measure against the generic condition.

```
post_repair_L52xx_absence :=
      no L52xx diagnostic of any family in the post-repair gate run
  (a parse-rejected repair never reaches the resolver and trivially
   satisfies this outcome; gate acceptance is reported separately)
```

The paper reports the corrected measure as the main analysis and retains
the original lexical operationalization as a sensitivity analysis. Both
are recomputable from the stored records:

```
python seeded/analyze_repair_ablation.py    # original lexical measure
python seeded/reclassify_removal.py         # corrected measure + audit
```
