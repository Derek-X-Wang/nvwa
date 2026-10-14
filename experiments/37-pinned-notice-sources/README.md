# Pinned notice source evidence (schema 1)

This isolated experiment retains three original legal-file candidates for exactly `profiling@1.0.18`, `svg_fmt@0.4.5`, and `hexf-parse@0.2.1`. Its portable checker verifies retained provenance and unknowns. It does not approve applicability, an entire license instrument, whole-package or expression coverage, redistribution, or release.

The independent baseline36 manifest is SHA-256 `2b551ed8c7fa22b347424c1056a3b6e5c935baaf7f4df7ebae4eb3e44ccb24fd`. Its **23 missing-text packages and 47 gap records remain unchanged**. Terms-bearing files for the other 300 packages do not establish complete or applicable coverage. This experiment does not amend experiment36.

| Package | Original declaration (unchanged) | Observed source result |
| --- | --- | --- |
| profiling 1.0.18 | `MIT OR Apache-2.0` | Root `LICENSE-APACHE` and `LICENSE-MIT` original terms candidates captured; no branch choice or applicability determination. |
| svg_fmt 0.4.5 | `MIT/Apache-2.0` | Root `LICENSE` contains MIT terms. The missing Apache branch and whole-expression/applicability coverage remain UNKNOWN. The slash expression is not normalized or selected. |
| hexf-parse 0.2.1 | `CC0-1.0` | No `LICENSE*`, `LICENCE*`, or `COPYING*` blob at the resolved package directory or its repository ancestors. This narrow filename absence leaves the text gap UNKNOWN. |

Hexf's published `.cargo_vcs_info.json` **has no `path_in_vcs` field**. That absence remains intact. Its actual `parse/Cargo.toml` path is independently resolved by the unique Git blob hash of the original published manifest in the exact retained tree. Ambiguity fails verification; the result is not backfilled into published metadata.

## Reproduce offline

Python 3.11 or newer, standard library only. From the repository root:

```sh
python3 -B experiments/37-pinned-notice-sources/verify.py
python3 -B experiments/37-pinned-notice-sources/portable_test.py --scratch .work/pinned-notice-sources/recheck-portable
python3 -B experiments/37-pinned-notice-sources/controls.py --scratch .work/pinned-notice-sources/recheck-controls --evidence .work/pinned-notice-sources/recheck-evidence
```

Use new scratch/evidence directories for each control run; existing directories are refused so earlier raw results cannot be overwritten. Mutated copies are removed after each expected red result; stdout/stderr and restored-green results remain in the chosen evidence directory. Unexpected errors fail the run and retain available raw outputs.

The default checker reads only this retained packet and its trusted classifier code. `portable_test.py` calls that real verifier on an isolated data copy while forbidding external file reads, writes, network access, and subprocesses. It does not simulate a green verifier. Optional same-host comparison against the recorded original 43 input paths is separate:

```sh
python3 -B experiments/37-pinned-notice-sources/verify.py --live
```

`--live` performs no network request. Those source paths need not exist on another machine; omit this option for portable retained-input verification. `acquisition.py` is the bounded HTTP transport, not a CI acquisition step. No collection command runs as part of the tests.

## Trust and limits

`pins.py` independently fixes the baseline manifest, captured packet and classifier hashes. The baseline supplies exact package IDs, versions, source repositories, raw expressions, normalized manifest hashes and published VCS metadata. The checker reconstructs all Git trees from entries, joins legal bytes and original manifests to actual Git blob IDs, resolves original-manifest paths uniquely, checks HTTP/body/inventory joins, recomputes content roles, and preserves mandatory unknowns. Mirrored mutable hashes cannot replace those independent expectations. The captured GitHub commit API records are retained primary-source observations; this is not a signed Git-commit authentication scheme.

All 9 actual requests were public, unauthenticated, bounded to 10 seconds and 256 KiB each, with no retries or redirects. All returned HTTP 200; 38,945 response bytes total. Original bodies, HTTP headers, statuses, UTC timestamps and SHA-256 values are retained. README, code/header bodies and nested document bodies were not acquired or audited; the 89-byte public cached Rust fixture is retained only as a source-as-terms negative control. `copyright_lines` preserves matching lines, not an exhaustive rights-holder attribution audit.

`REPORT.md` records exact sources, outcomes, controls and remaining scope. `FILE-HASHES.json` freezes the delivered files (excluding itself), including the one authorized new workflow.

## Integration

`.github/workflows/pinned-notice-evidence.yml` adds a separate lightweight Ubuntu 24.04 offline integrity job for natural pull requests and main pushes affecting this experiment or that workflow. It uses the existing pinned checkout action, read-only contents permission, no persisted credentials, a five-minute timeout and cancellation of older heads. It runs the checker, portability test and actual mutation controls with preinstalled Python. It neither collects sources nor installs dependencies, compiles Rust, runs GPU work or grants release approval. Its result remains separate from the existing 113 Rust and 77 diagnostic checks. Hosted execution is NOT-RUN in this handoff.

Current user principle: within the authorized task scope, independent review and final CI authorize autonomous merge, followed by exact-main CI. This note grants no new release, legal, paid-resource or publication permission. The parent agent owns review, Git integration and publication. Fresh independent review of this frozen candidate is PENDING.
