# Issue #79 exact-export diagnosis (HTML only)

The portable HTTP, JavaScript and byte-transfer controls run from a clean checkout without `.work/`. The live legacy R2 reproduction additionally needs the authenticated retained compiled site and validator capsule. Those large local inputs are not included here and are never downloaded implicitly. See [the observed result](REPORT.md) and [actual Web screenshots and hashes](evidence/observations.json).

Original compiled R2 site/Wasm is restored byte-exact under `.work/hairline-export79/retained-r2-site`. Original `index.html` is never overwritten. `diagnostic80.html` adds a standalone observational harness; TRANSFER_CORE SHA256 remains44698bd8f212ae656ccf6561b277ceb3bb4e9f01bbf9d51d1ceb3f318dbeab9a. No Rust build or scene/material/viewport changes.

Root owns actual browser/GPU. Worker adapter inventory had no browsers; advertised IAB readiness returned unavailable. Worker prepared CPU/HTML only, except explicitly authorized ephemeral loopback integration tests (closed after each test).

## Root launch

Check9205 is free. Use a fresh run ID for EACH page (create-only event files), close the old page/server before the next run.

```
python3 -B experiments/80-hairline-export-diagnosis/server.py --run-id h79e80-manual-v2 --port 9205
```

At1280x720 open:
`http://127.0.0.1:9205/diagnostic80.html?work=works/default-arms.nvwa.json&benchmark=1&player=1&case=manual`

Manual mode sends zero app commands. Expand the original right panel, send unique paused source0 request and unique combined/textured `a_original` diagnostic request, wait actual current successful acknowledgement, then click the original Prepare button. Observer records `manual-prepare-enter` BEFORE calling original prepareTransfer/readCapture, then digest boundaries, exit/error. Left-bottom DIAG80 status and original visible report are screenshot cues. Panel/overlay does not resize the canvas. Use original download button if enabled.

After stopping this server/page, start with a NEW run ID `h79e80-auto-v2`; open the same URL with `case=fixed-auto`. Only this explicit case runs automatically. It waits actual committed b1_76_work equal the independently pinned Work before sending `h79e80-auto-v2-hold0`, then `h79e80-auto-v2-A`. It retains original actual ready/current/ack/success, stable2, Work/frame/generation/visibility and exact before-after token/string gates. No retry or readiness bypass. Fixedcase original A only.

Receiver binds127.0.0.1 only, exact Host/Origin, no CORS/arbitrary output path,32MiB body cap, create-only output. Artifacts: `.work/hairline-export79/actual/<run-id>/manifest.json`, exact original `capture.json`, `currentness.json`, and per-event JSON. A network receipt certifies bytes only. Qualified snapshot additionally needs successful named currentness fences after prepare/exactText and before/after manifest/raw responses, then DOM DONE with post-currentness-response. Partial raw is retained if later currentness fails; no current-render claim follows.

## CPU controls and versions

`python3 -B -m unittest discover -s experiments/80-hairline-export-diagnosis -p 'test_*.py'`

V1's21 direct seam tests passed but missed HTTP Handler construction. Root actual curl/browser found connection reset from Handler.__init__ reading unset self.server. Retained v1 under `.work/hairline-export79/frozen-v1`; actual lifecycle regression first goes red with the same AttributeError/reset, then green after using explicit passed server. An initial test-only variable-shadow error is also retained separately. V2 adds committed-Work startup wait (not a relaxed capture gate).22 tests pass, including real loopback GET/HEAD/config and manifest/raw/currentness POST, origin/host/create-only red controls, unchanged transfer cancellation/stale/overlap/request/readiness controls and called harness. Main-thread/browser timing remains an actual root test, not a CPU claim.

V2 frozen source list: `.work/hairline-export79/SOURCE-FREEZE-v2.json` SHA256 dfc5e24ae4577861c9f0ab46a14cf9caaf46715238d84addefeee41278d2e65a. Do not edit these files during root's actual run. Later changes require a new version/hash.

## Original single-A source check

Actual R2 source310 plus69 RESULTS supplement311 files restored without edits under `.work/hairline-export79/validator-root`; receipts VALIDATOR-ROOT.json and VALIDATOR-ENTRY.json. Run:

```
python3 -B experiments/80-hairline-export-diagnosis/validate_one.py --capture ABSOLUTE_RAW --manifest ABSOLUTE_MANIFEST --expected-request-id INDEPENDENT_ROOT_ID
```

This first verifies original exact transfer bytes, then calls unchanged `check_captures.validate` for one original A. It does not call the full matrix checker or admit hair quality. Results create-only under `.work/hairline-export79/validation/<id>.json`. Transfer recovery, source/CPU validation, full cohort, and GPU visual quality remain separate claims.

## Portable regression gate

Run both commands from the repository root. These 26 checks use explicit synthetic transport fixtures; they do not claim real skeletal or image validation. The actual retained A record was validated separately with the unchanged source checker.

```sh
python3 -B -m unittest discover -s experiments/80-hairline-export-diagnosis -p 'test_*.py'
python3 -B -O -m unittest discover -s experiments/80-hairline-export-diagnosis -p 'test_*.py'
```

Post-run generator and validator guard fixes preserve the observed v2 runtime HTML, harness, Wasm and transfer-core bytes. The generator rejects changed input structure or output bytes. The standalone validator wrapper rejects missing or empty receipt lists, unsafe paths, changed source bytes, mismatched request IDs and B captures under normal Python and `-O`. Its private 311-file capsule is required only for the separately invoked actual-record validator, never for portable test discovery.
