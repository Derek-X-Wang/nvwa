# Historical motion evidence after the rehearsal schema change

This adapter preserves the unchanged experiment48 runtime audit and experiment49
CPU gates after current product source advances. It runs those original scripts
in an authenticated historical source context. It does not compile a historical
binary, collect a new GPU capture, or verify the current rehearsal runtime.
Current workspace tests and native/Wasm compile checks remain separate gates.

```sh
python3 -B experiments/51-rehearsal-history-compat/audit.py
python3 -B -O experiments/51-rehearsal-history-compat/audit.py
python3 -B experiments/51-rehearsal-history-compat/test_controls.py
python3 -B -O experiments/51-rehearsal-history-compat/test_controls.py
```

`--check NAME` selects one fixed original command family; `--help` lists them.
The default `all` runs all 15 families. Both interpreter modes preserve all
original checks and failure controls. A nonzero child exit or timeout rejects the
adapter result. Output includes original stdout/stderr and explicit historical
scope. The adapter repeats preflight after the children finish.

## What source bindings change

The existing `49.../historical48/audit.py` checks all 54 experiment48 source inputs
and both retained experiment49 cohort source maps against its repository root.
That binds root Cargo manifests and product source, including CLI, core, runtime,
and Studio. The rehearsal schema change legitimately makes that direct check
fail. Its original two Studio substitutions still apply within this adapter's
historical experiment49 context; neither that policy nor its source archives is
edited.

The experiment49 attribution commands also bind experiment41 source receipts,
43 mapping source, 44 raw inputs/receipts, 47 calibration/authority documents,
fixture assets and the fixture generator. Those are retained live inputs under
exact baseline hashes, with no substitution. Attribution's optional six-file
original-source cache remains **NOT-RUN**. Existing recorded identities and URL
receipts are checked; this adapter supplies no new source-cache identity.
Earlier experiment42–48 importer/export/calibration CI commands do not bind
changing product crate source and remain direct checks. The experiment49 probe
Cargo format/check commands remain direct current-source compile checks.

## Fixed input mapping and provenance

`MANIFEST.json` was generated from commit
`50eae1979cac47c7eb53dada69f06b716436bf92`, tree
`0bb87d9dc2ff324390de6e184852a87d513017fa`, using exact Git blob bytes.
It records SHA-256, Git blob identity and byte length for every logical path.
The adapter pins the manifest SHA-256 in code.

The mapping contains 179 files:

- 28 root Cargo/toolchain and product source files are archived as
  `sources/<original logical path>.txt` (576,433 bytes total). These are the
  product/root paths required by the recorded source-cohort unions.
- Two original packaging tools (`scripts/build-web.sh` and `scripts/package-native.py`, 3,368 bytes total) are also archived at their unchanged pinned identities. They are separate from the 28 product/root files above.
- The original experiment49 probe Cargo manifest and lock (143,439 bytes) are
  archived at the same pinned identities. Current isolated probes can follow
  the real product dependency graph without replacing recorded source context.
- 147 retained inputs are read from the live checkout and must retain exact
  original bytes. They include the remaining experiment49 inputs, all of experiment48's
  runtime archive, the source-cohort assets/scripts, export artifacts, and the
  attribution/calibration input closure. Source archives and receipts in
  experiments41–49 remain unchanged.

The temporary stage contains exactly those 179 allowlisted files (36,966,316
bytes). It does not copy a checkout, Git metadata, build products, models, or a
source cache. Both historical input trees and the 32-file combined source archive have
exact file-set checks. Missing/extra files, changed bytes or identities,
duplicate JSON keys, path traversal, archive aliasing and symlinks reject the
run. Temporary stages are removed on success or failure.

## Verification boundary

The 19 adapter tests include source/archive pin mutations; missing, extra and
untrusted paths; symlinks; changed asset, capture, source and receipt bytes; and
restoration checks. They also alter staged root Cargo source and a captured
matrix, then prove that the unchanged original historical48 audit and
experiment49 comparator reject those mutations and pass after restoration.
Current product source changes intentionally do not become historical input
claims. The retained `archived_product_source_files: 28` output field counts
the original product/root cohort; it does not count the two additional archived
packaging tools or the two probe Cargo context files. The complete archive
contains 32 files. The new tests also prove that archive corruption rejects,
restoration passes, and current
packaging and probe Cargo changes do not replace historical source bytes.

`VERIFICATION.json` retains the original bounded local normal/optimized record. Hosted CI,
new native/Web runtime collection and the new rehearsal feature are outside this
adapter's evidence scope.
