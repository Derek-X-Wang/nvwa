# Second publication P2: complete request settings

The optimized-mode correction remained in place. A later independent review
found a separate normal-mode defect: comparing only keys already present in
`generation.request` admitted a missing `seed` or an entirely empty request after
a private fixture's manifest and provenance hashes were rebound.

`request-shape-red.json` is the exact reviewer receipt, SHA-256
`fcf2a98cc3e4ed9ec9706135631aed6ec6869d63a78929567b715949014f059c`.
`verifier-before-request-fix.py.txt` preserves the post-optimization/pre-request-fix
source unchanged, SHA-256
`db8b255a49faff9cb76441b922ab57d19e3f183413d3b1e8a2ed58920187baa2`.
Both are historical evidence; the source text is never executed by CI.

The current verifier compares against the unchanged guard's full request:
`code_revision`, `ggml_revision`, `artifacts`, `prompt`, `seed`, `frames`, `fps`,
`diffusion_steps`, `text_cfg`, and `constraint_cfg`. Dictionary equality requires
all ten keys, no extras, and matching values. The early non-assert optimization
rejection and every other existing verification/privacy check remain.

Private controls use copied evidence and explicitly mutated private source
receipts. Their copy-provenance records name those private test sources and
recompute bytes/hashes; the manifest also binds the changed fixture bytes. This
lets missing seed, empty request, extra key and wrong seed reach and fail the
request check, rather than merely failing an earlier stale-hash check. Both CLI
and imported `main()` paths are exercised, with an unchanged valid fixture as the
positive control. Canonical published receipts, model outputs, authorization,
prior review files and prior red/green controls are not modified.

The real retained request already had all correct fields. This fixes verification
strength, not the recorded generation result or its remaining playable HOLD.
