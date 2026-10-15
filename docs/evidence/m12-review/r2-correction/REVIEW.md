# Independent R2 correction and initial publication re-review

Reviewed HEAD `aa9f942136f00d154ffe650936579d056fb637d1` and the frozen workflow, roadmap/history/Alpha documentation, and experiments 39/40 against base `a094baa048e6e50056e3288ecfa85bb4ac62e140`. This pass excluded `docs/evidence/m12-agent-loop/**` and was not whole-PR approval.

## Conclusion

Prior P2 resolved; no new findings within this reviewed scope. Fallible common stdout write/flush returns `stdout_write` with exit 1. Stderr delivery is best effort. The public contract correctly separates file commit from response delivery and directs callers to inspect the actual output before retrying.

## Actual verification

- Independent accepted-binary probes passed all seven closed-stdout entrypoints, closed-stderr domain failure, simultaneous stdout/stderr failure, and late batch failure with absent/existing output.
- All ten CLI integration tests passed with `cargo test -p nvwa-cli --locked --offline -j 1` in a reviewer-private target.
- Portable evidence audit and all five tamper rejection/restoration controls passed. Static workflow review confirmed pinned checkout, read-only permission, five-minute Ubuntu scope, and stdlib-only commands. Hosted execution was NOT-RUN.
- Experiment 39 static analysis exactly matched retained output and checked all 38 captured-source hashes. Primary pinned source supports the 30-to-77 expansion and six-channel contact distinction. No inference, model download, runtime memory measurement or generated motion was run.
- Experiment 40: checked 61 file hashes, renderer/asset/Work identities, and recomputed 12 wave and two rest comparisons. Independent CPU rerun produced byte-identical numerical metrics and derivative GLBs. Inspected actual retained captures. Conclusions remain limited to controlled derivatives and the older frozen renderer; no live GUI/GPU or current-main acceptance was run.
- Historical roadmap matched base exactly. Checked 429 listed path/blob comparisons across PRs 22/28/29. Live GitHub metadata state was NOT-RUN; retained metadata statements were reviewed as such.

Accepted binary SHA-256 remained `e0da6b3e5759801b9d5e4898a2ecda716111ee05159415163521fb01eb6ea637`. Workflow SHA-256: `3d5be32fc8fff706a358f1b44c8869dc569c3f354a7d75bffaebe227882ac36d`. The 259-file `reviewed-source-hashes.json` SHA-256 is `d0493fd52d28606e45fd5af8c2520ddfe88671a26f14835c37981f82edaafc89`. Raw outputs and individual hashes remain in this directory.

Remaining gates at this pass: final publication reconciliation after root freeze; GUI and independent operator acceptance; native authorship confirmation; final CI and exact merged-main verification. All review commands exited and were reaped. Private Cargo target and test temporary directories were removed. No source or retained binary was changed. Raw evidence and numerical outputs were retained for root.

This report records the completed re-review; it does not assert new runs or approve later publication changes.
