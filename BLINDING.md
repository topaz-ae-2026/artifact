# Blinding and Pseudonymization

## Pseudonymized for review

The generated artifact pseudonymizes:

- the real language and toolchain name as language L and `langl`;
- the diagnostic prefix as `L` in every text asset;
- release labels as R0;
- machine-specific absolute paths, usernames, hostnames, email addresses, and
  organizational identifiers;
- the hosted service location as hosted Endpoint A; and
- language-source filenames from the original extension to `.l`, including every textual path
  reference.

Numeric diagnostic suffixes are unchanged. The review mapping is:

| Review code | Preserved suffix | Direct binary display |
|---|---:|---|
| `L5201` | `5201` | original prefix + `5201` |
| `L5202` | `5202` | original prefix + `5202` |
| `L5203` | `5203` | original prefix + `5203` |
| `L5204` | `5204` | original prefix + `5204` |
| `L5205` | `5205` | original prefix + `5205` |
| `L5002` | `5002` | original prefix + `5002` |
| `L5298` | `5298` | original prefix + `5298` |
| `L5299` | `5299` | original prefix + `5299` |

“Original prefix” in the final column means the prefix printed by the pinned
executables. The paper and every artifact text asset map that runtime prefix
to `L`.

## Preserved exactly

The pseudonymizer preserves all measurements and experimental records,
including numeric values, task and schedule seeds, timestamps, token usage,
responses, outcomes, model reasoning effort, and the disclosed model identity
`gpt-5.6-sol`. Client and CLI version identifiers and run configuration also
remain available to reviewers.

Prompt SHA-256 values were computed over the pre-pseudonymization prompt text.
Each cell record preserves that original hash beside the pseudonymized prompt.
The hash therefore authenticates the frozen pre-pseudonymization prompt and is
not expected to equal a hash recomputed from the displayed review text.

`pilot/FROZEN.sha256` likewise records the frozen pre-pseudonymization corpus.
`MANIFEST.sha256` is the integrity manifest for the generated review tree.

## Executable caveat

`bin/gate-r0.exe` and `bin/gate-r0b1.exe` are pinned review builds whose
diagnostic rendering emits the review prefix `L` directly, in both human and
JSON output, so executable output matches the review records byte for byte
on codes. The rendering shim affects only the code label; numeric suffixes,
acceptance decisions, spans, and all other behavior are the compiler's own.
The camera-ready artifact will ship builds with the original prefix restored.
