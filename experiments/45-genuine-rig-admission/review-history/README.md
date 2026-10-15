# Initial review and portability correction

These are unchanged records from before the float-comparison repair, not final
approval of the current experiment.

* `initial-review.json` is copied exactly from the initial independent publication
  review at `.work/m2-approved-trial-publication-review/45-first/REVIEW.json`.
  SHA-256: `20422634fecfe5c8e5b13facf2fbfa9cdad0ee69327822c6888f9adb07378b96`.
  Its reviewed cohort is the earlier inventory, not the current one. It found one
  P2 Python 3.9 historical-float comparison failure and independently corroborated
  the bounded root/endpoint math and admission HOLD. Its auxiliary evidence hashes
  identify private review records; those records are not required by this public
  reproduction.
* `portability-before.json` is the original worker's independently reproduced
  Python 3.9.6 red receipt, preserved before editing the comparison. The original
  scripts and stdout/stderr remain privately retained under this experiment's
  `.work/portability-before/`. It records probe exit 0 and controls exit 1 at
  `historical numeric drift: all_signed_bases`.

Current restored-green receipts and explicit per-runtime numeric differences are
in `../portability.json`. All three original files in `../historical/` remain
unchanged. Current review approval remains a separate gate.
