# Revised-binary actual agent run

The same native LLM worker repeated the exact root-authored acceptance task
after the R2 transport correction. This is actual adaptive authoring through
nine separately invoked production CLI calls, not deterministic replay,
synthetic harness output, a fresh human request or an independent agent.
See [DECISIONS.md](DECISIONS.md) for observations and choices between calls and
[the original task](../TASK.md) for exact authority and route attribution.

The worker read revised capabilities, authored appearance, deliberately caused
a real stale-revision failure, inspected actual input, corrected the request,
validated the asset, saved and inspected the final file. Complete inputs,
outputs and raw process receipts are in this directory. `record.py` is an
unchanged copy of the generic one-call recorder, with no authoring policy.
The revised binary recorded by every call has SHA256
`e0da6b3e5759801b9d5e4898a2ecda716111ee05159415163521fb01eb6ea637`.

Current work: [agent-nine-second.nvwa.json](agent-nine-second.nvwa.json).
Its SHA256 remains
`e33356b490cb8d6c01118958c3d22409f4546cfa6164a7d69d496be292eb25cc`.
It is byte-identical to the historical final work, but this directory records
the actual revised-binary authoring chain. Revision 2, jaw width 0.42, smile
0.2, idle 0–3 seconds, wave 3–6, turn 6–9, all nonlooping authored actions.
No generated action is claimed. Native/Web acceptance remains root-owned.

The original nine receipts remain immutable historical evidence. Their
pre-fix transport contract was rejected and is not current API evidence.
Historical source snapshots and a pinned manifest preserve that distinction.
`source-manifest.json` pins current relevant source hashes without depending
on private binaries. The portable stdlib verifier checks both source manifests,
both nine-call chains, command and output snapshots, revised discovery limits,
and separate transport red/green/probe evidence. It never rewrites hashes or
manifests, launches a binary/model, acquires source, or uses the network.
It checks retained evidence, not hosted LLM authorship or signed attestations.

Run from any working directory:

```sh
python3 -B experiments/38-agent-cli/verify.py
python3 -B experiments/38-agent-cli/verify_controls.py
```

The commands above are repository-relative examples; the verifier itself
resolves its location. Binary execution and model authorship are separate
from this portable retained-evidence audit. The historical absolute paths in
raw argv are provenance only. Both binaries and the child worktree remain
retained for root QA. Source and binary re-review is still outstanding.
