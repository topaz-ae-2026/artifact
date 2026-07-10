# Frozen specification-ablation conditions

All four conditions keep identical task contract, required interface,
task-specific visible examples, response contract, extraction, gate
(R0+B1), and oracle. Only the language-information block differs.

1. full: complete SPEC.md plus PROFILES.md (docs/langl-v5.2 at the
   pinned tree).
2. grammar-static: SPEC.md sections 0 through 21 only (the standard
   library surface section 22 removed), no PROFILES. File
   cond2-grammar-static.md.
3. examples-only: the seven public checked example programs verbatim,
   no specification text. File cond3-examples-only.txt.
4. none: no language information block at all.

Endpoint: the frontier endpoint only, medium effort, fresh stateless
sessions, first drafts only, no repair. 24 tasks x 4 conditions x 3
repetitions = 288 cells, interleaved randomized order (seed 27). The
full-spec arm is rerun fresh in the same window; old cells are not
reused.
