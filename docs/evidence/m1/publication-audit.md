# M1 evidence publication audit

This is a bounded evidence-hygiene audit of the M1 evidence set and linked M1 docs. It does not review source correctness or re-run product acceptance. Counts below describe the working-tree snapshot before this memo was added.

## Findings

The evidence directory contained 52 files: 7 Markdown, 6 JSON, 21 logs, and 18 screenshots (2,725,566 bytes). Git reported the directory as untracked at the audit snapshot, so these files were local evidence awaiting publication.

The main publication observation is local path visibility. Nineteen of the 21 logs contain 42 occurrences of the developer's absolute home/repository path. The linked [interaction implementation notes](../../implementation/m1-interaction-notes.md) contain two more. Seven screenshots show that local path in the app's work-file field: [native save](native-save.png), [fresh native reopen](native-web-reopened.png), [interaction before](native-interaction-before.png), [first-pass restored interaction](native-interaction-restored-first-pass.png), [final interaction before](native-interaction-before-final.png), [final interaction wave](native-interaction-wave-final.png), and [final interaction restored](native-interaction-restored-final.png). Root's disposition is to retain this original evidence without redaction or recapture: equivalent M0 paths already exist in the public repository, and these paths reveal no credential or unrelated private data. The path is personal machine metadata.

A bounded scan of 40 M1 text/JSON files found no private-key, GitHub/AWS token, bearer-token, credential-field, or email patterns. This was a pattern scan, not a complete secret scanner; it did not inspect unrelated files.

## Evidence and reproducibility

The docs distinguish actual native/Web GUI evidence from JSON exchange artifacts and say the GLB was the repository fixture. They do not claim AI-generated or mocked acceptance. The word “AI” appears in the carried M0 issue #12 title; the M1 contract explicitly excludes a model service, and the interaction notes say a mock action button does not count as acceptance.

The six envelopes in [the CLI replay batch](cli-replay-commands.json) have expected revisions 0 through 5 and match the documented timeline, parameter, and inverse-timeline effects. The [CLI/GUI equivalence record](cli-gui-equivalence.md) states that these commands reconstruct visible GUI outcomes; they are not captured event traces. Its inverse `SetTimeline` commands model undo/redo results and do not establish CLI undo/redo support. The recorded example batch remains separately available at `examples/m1-commands.json`.

All 21 relative Markdown targets checked across the 13 M1 evidence, implementation, and verification documents resolved. The equivalence record gives build, apply, validate, inspect, and save commands. One small reproducibility gap remains: it does not give a command to compare the generated CLI documents as parsed JSON against the saved Web and fresh-native files. Add that comparator when the record is next edited; do not treat this audit as having rerun the CLI.

The current fixture SHA-256 is `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`. It matches the M0 `d74493` fixture and the hashes recorded in the default, M1 example, and native/Web exchange documents. `Cargo.lock` has no diff from M0. The Web revision-6 and fresh-native revision-6 JSON documents are equal after parsing.

## Audit boundary

This audit checked document links, inventory, text patterns, example/replay envelopes, fixture hash, lockfile diff, and parsed exchange JSON. It did not run Cargo, the CLI, a browser, the native app, the Player server, GPU checks, or external issue links. It does not independently validate test/build logs, GUI behavior, Player behavior, or the root agent's final release checks. Refresh checkpoint status and counts against the final root-owned acceptance before publication.

Root final publication check: 131 staged files; no generated target/dist/work-cache files, no file above50MiB and no private-key/GitHub-token/AWS-key/model-API-key patterns found in staged text. All40 frozen manifest hashes match current source/artifacts. Final test log totals57passes; Cargo.lock unchanged; CLAUDE.md exact pointer. Local links in15 evidence/index/handoff documents resolve. Captured log terminal blank lines were trimmed; diagnostic/test-result content is preserved.
