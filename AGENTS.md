## Agent skills

### Issue tracker

Issues and specs use GitHub Issues in `Derek-X-Wang/nvwa`. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the five default triage labels. See `docs/agents/triage-labels.md`.

### Domain docs

Use a single-context layout: root `GLOSSARY.md` and `docs/adr/`. See `docs/agents/domain.md`.

### Verification

Default to real CLI acceptance for agent authoring. Use Web acceptance for browser-specific behavior, visual playback questions, or requested milestones. Keep existing automated tests, native/Wasm compilation and CI gates. Run targeted native checks for desktop-specific changes; defer routine desktop UI acceptance to a larger version milestone. See `docs/agents/verification.md` for exceptions, evidence labels and the deferred checklist.
