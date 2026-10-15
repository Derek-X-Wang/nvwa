# Unchanged original private evidence

These three files are exact byte copies of the original private numerical study
under `.work/m2-genuine-mapping-feasibility/` in the provider worktree. They retain
the original absolute paths, wording, and source-hash attribution. They are not
the public reproduction entry points. Do not run their private-path script as
the current experiment.

| Original filename | SHA-256 |
|---|---|
| probe.py | `eda8d227ff632cacf7701985de26b0df8a6b78a8426861c33e0a771b3b798058` |
| numeric-proof.json | `7ef382ef09efe79d9cbb0ae558943ec54c5a805323162a6df20ddf9a61665104` |
| PROOF-NOTES.md | `7ab0d8fbe50b78ea594de7a0258080e9abc9e6d06b6cdeccd4f8441f6b281a76` |

The current `../probe.py` keeps the mathematical calculation and replaces
private dependencies/output with pinned public files and explicit guards. It
adds input and output protection, successful-receipt binding, rest-correspondence
observations, strict numeric controls, and an explicit admission HOLD.
`../test_controls.py` verifies these copies with exact file hashes. The 17 shared
fields require exact structure/types/discrete values and finite float agreement
within `1e-13 + 1e-13 * max(abs(actual), abs(historical))`. This comparison corrects
a Python 3.9 last-bit portability failure without changing these originals.
Changed current metadata is not presented as unchanged original bytes or as
byte-identical runtime output.
