# #112 local non-gating pilot

Approved scope: historical identity admission and reuse of existing independent
raw-recipe geometry reconstruction. Base checkout:
`caf6069ab2ed26a3965cd27ad8f238db0d4a0596`. Design proposal SHA256:
`9677ffba9152703a89f67c2df6466427aadcc3b48de50a2f059ec80481a950c6`.

## Local contract

- Historical admission accepts only the complete original compressed frame with
  SHA256 `5df0c97e5c51b3e71741e115ca4040d441189dd5853a505c1076d9ed0a53ae5e`,
  strict bounded decoding, the independent expected case and pinned source/asset
  identities. Missing input reports `BLOCKED_MISSING_HISTORICAL_INPUT` and a
  nonzero exit; wrong or substitute input fails. No fallback to traces or other
  captures. Actual historical replay remains NOT-RUN when input is absent.
- Current geometry admission has a separate identity and expected case catalogue.
  Use existing retained experiment60 B1 motion-v1 frames and authenticated v1
  assets only. Do not rewrite a current frame as historical or a current19 record
  as experiment60. Unsupported profiles/recipes/schemas fail explicitly.
- Reuse existing independent source84/85 numerical helpers through a v1-only
  source-explicit adapter. Preserve exact topology/source support and existing
  applicable numerical bounds: recipe rest `1e-7 m`, signed garment fit `1e-6 m`,
  normalized weights `1e-6` dimensionless, upload reconstruction `1e-5 m`.
  Do not introduce an epsilon from observed sample differences.
- Report each actual frame, recipe/time, source/driver closure, scope and timing.
  Retained-frame reconstruction is offline evidence, not fresh production,
  platform/GPU/visual acceptance or full current-runtime correctness.
- Independent source-to-rig reconstruction and new rig error bounds are outside
  this pilot. Report `NOT_VERIFIED_RIG_ORACLE`. Preserve original Linux failure
  and optimized-control gap, all quality HOLDs, #3 blocked and #4 gaps.

## Failure and recovery proof

Exercise missing/corrupt/substitute identities, unsupported or stale cases,
changed geometry, exact topology/support and weights through the new real local
entry point or its actually called validator. Ensure numerical faults reach the
numerical check rather than merely failing a file hash. Restore the same input
and prove recovery. Distinguish these payload/admission faults from production
Rust source mutations, which this pilot does not run or replace.

Run focused local controls in normal and optimized Python, with captured exit
codes, case counts and logs. No zero-test success, error swallowing or overwrite
of original evidence. Existing files/frames/gates remain unchanged.

## Ownership and resources

One worker owns new implementation/tests under this directory. The orchestrator
owns this contract and final docs; a separate helper audits available cohorts and
v1-only dependency closure without editing implementation. Existing source84/85,
product code, assets, dependencies, locks and workflows are no-touch.

No new downloads, Rust builds, models, GUI/GPU jobs, remote/additional compute,
CI run, required-gate change or runner-frequency change. Only existing local
Python and frame data are used. Commands are bounded and timings retained. Any
needed scope/resource change stops for the orchestrator; no silent expansion.
