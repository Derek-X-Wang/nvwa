# Issue 5: supported download observation follow-up

This experiment reuses the accepted Wasm and the fixed original humanoid. It
does not change product source, dependencies, rendering, or download actions.
The conclusion is **INCONCLUSIVE for cause**; see [REPORT.md](REPORT.md).

## CPU verification

From the repository root:

```sh
node --test experiments/35-web-export-followup/observer.test.cjs
python3 -B -m unittest discover -s experiments/35-web-export-followup -p 'test_*.py' -v
python3 -B experiments/35-web-export-followup/verify.py
```

The Node checks exercise exact console argument/receiver/return/exception
forwarding, DOM-backed initialization and per-overflow publication, and DOM
write/creation failure behavior. The current counts are six Node and seven
Python controls. Python checks exercise the exact
file map, traversal rejection, unchanged payloads, limited HTML insertions,
and corrupt/truncated actual PNG rejection. These checks are CPU controls,
not browser download or pixel evidence. The offline verifier checks the
retained actual receipts and source/network/image hashes.

## Actual browser protocol

Use the exposed `mcp__cua_repl` adapter only. Freshly inventory adapters before
selecting one. The recorded adapter was IAB browser `2`; its initial tab list
was empty. A browser installed on the machine is not an attached adapter.
Stop for unsupported capabilities or any new permission requirement. Do not
change browser settings, profiles, or security policy.

Before a new run, compare all 32 inputs against
`docs/evidence/m1-1-final/build/build-inputs-after-lint-fix.json` and compare
`dist/web` against `docs/evidence/m1-1-final/build/artifact-identities.json`.
Require Wasm SHA-256 `d890dfee73e9eeeee6ce3d82f255c79979e8c8b6bed90243c6101f8e1c1763a8`,
GLB `f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`, and
the 1624-byte common work `ff0b8e36adfc3ebadc5fc700a4c760f6f551273b56e85bf336563e18b63eb445`.
Do not rebuild or substitute pixels.

Require a fresh empty listener check on the assigned loopback port:

```sh
lsof -nP -iTCP:9206 -sTCP:LISTEN
python3 -B experiments/35-web-export-followup/server.py --serve
```

The server serves only exact member paths, rejects foreign Host/Origin, accepts
no POST uploads, exposes no directory listings, and logs response body hashes
and socket-write UTC separately. It starts one listener on `127.0.0.1:9206`.
Use one renderer at a time. New raw network logs append in the private packet;
do not overwrite the accepted evidence directory.

1. Set the supported viewport override to 1280×720. Create a fresh blank tab.
2. For case 1, arm `tab.playwright.waitForEvent('download', {timeoutMs:30000})`
   **before** `goto`. Navigate to
   `http://127.0.0.1:9206/case-1/index.html?benchmark=1&work=works/character-loop.nvwa.json`.
   This deliberately records the listener-spanning-navigation observation.
3. Retain start/end UTC, exact event or bounded timeout, `tab.dev.logs`, DOM
   canvas geometry, and an original `getScreenshot()` output. Never equate
   `Screenshot saved` or the Rust callback with file durability.
4. In that same case-1 runtime, arm a 15-second download wait before clicking
   the original **Download actual benchmark canvas PNG** button with a
   supported UI locator. Retain `Download.path({timeoutMs:1000})`. No physical
   human activation is implied by a tool click.
5. Close case 1 before opening case 2. Case 2 URL is the same query under
   `/case-2/index.html`. Its wrapper adds only a fixed 5000 ms delay immediately
   before production initialization. No UI activation starts this runtime.
6. After `goto` returns, immediately arm the 30-second download wait in the
   loaded document. The bootstrap gap permits listener setup before Wasm
   initialization and the original 15-second Rust warmup. Retain the visible
   journal through `#nvwa-export-followup-journal` text, not through guessed
   read-only evaluator access to custom Window fields.
7. Independently inspect only each exact returned file path. Verify current
   birth/modification times within its event window, SHA-256, PNG structure,
   1280×720 dimensions and actual character/UI pixels. Copy original bytes into
   the new run's own packet. A missing event with no returned path is a file
   observation limit; do not invent a broad filesystem absence claim.
8. Stop once the current automatic control passes. Maximum budget is three
   Nvwa loads and six total automatic/explicit triggers; each event wait is at
   most 30 seconds. This accepted run used two loads and three triggers.
9. Close owned tabs, reset the temporary viewport, stop the exact owned server
   through its terminal session, and verify exact PID and listener absence.
   Preserve actual files before removing only proven fresh task-owned downloads.

The first case's original 1663-byte observer is frozen in
`evidence/case-1-observer.js`; the second observer adds a hidden JSON journal
for supported DOM reads. Neither observer hooks Blob, anchors, object URLs,
revocation, `toBlob`, character/editor behavior, or runtime timers. The original
module is preserved except the case-2 pre-init delay. No delay is a proposed
product workaround. No iframe attachment/revocation comparison was repeated.

### Future helper versus historical browser source

The actual case-2 observer remains frozen in `evidence/case-2-observer.js`
(SHA-256 `08b34dec576254dc8e67255c6f5ee047990cf82b84fec01cad1bc2e5a283ef06`).
The current `observer.js` is a subsequently hardened **future-run helper**. It
now publishes the DOM journal after every overflow, keeps at most 64 records,
and contains DOM initialization/write failures so original console calls still
forward. `journalFailures` exposes counts and bounded last-error text after a
successful DOM publication. Persistent write failure leaves the last successful
snapshot stale; failed journal creation leaves no supported DOM read surface.
Neither limit is actual-browser-tested in this rework.

The existing `/case-2/observer.js` route will use this future helper in a new
run; it does not reproduce the historical observer bytes. Use the preserved
snapshot and network receipt when assessing the original case. No historical
source, raw evidence, manifest, PNG or screenshot was replaced. Rework ran CPU
controls only, with no new browser/server/download/build. Three independent
mutants (stale DOM overflow, failed-write suppression of originals, and a
65-record bound) each produced red then restored green; receipts are private
under `.work/issue5-export-followup/rework/` for root review/publication.

## Evidence ownership

`evidence/` contains selected immutable actual packets and original images.
`.work/issue5-export-followup/` holds the private execution packet and only the
eight selected own browser call/output pairs. It contains no other chats.
Root owns archive copying, publication, independent review, and issue status.
No GitHub writes, staging, commits, or branch changes were made by this worker.
