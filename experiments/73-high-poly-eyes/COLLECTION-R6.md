# R6 bounded Web collection interface

QUALITY HOLD. This changes experimental HTML transfer only. Rust, production,
geometry, materials, camera, Work fixtures, strict comparator and thresholds are
unchanged. Existing R4/R5 artifacts and failures remain separate. A transfer test
with an old raw record does not create a new runtime observation.

The retained R5 Web frame was13,915,980 characters in the DOM. Its one-shot tool
return contained `[Truncated]`; the saved358,477-byte record was invalid JSON.
The controls-summary operation exceeded its CDP deadline before dispatch while
screenshots remained available. The cause of that deadline is UNKNOWN. Removing
large DOM fields is not proof that control or screenshot collection now works.

R6 keeps only compact request/phase/current/error status in the DOM. Preparing a
record retains original Rust report/frame strings and concatenates them verbatim.
It checks ready/current/success/diagnostic, matching request/Work/endpoint and
stable identity before transfer, then checks unchanged raw strings after hashing.
Every download/chunk rechecks those raw strings. A new command invalidates the
prepared transfer. Numeric parsing is used only for checks; exported witness
numbers, including `-0.0`, are never serialized from parsed values.

## Root-only UI plan after independent review and new export

1. Use a fresh separately named session/evidence directory and the reviewed R6
   export. Keep historical source/record identities separate. Root owns the one
   graphics session. No worker launch or hidden/global bridge call is required.
2. Open the existing approved short-front Work with existing player/benchmark
   settings. Use the normal visible request controls. Hold source0, then request
   A combined/textured using a fresh request ID. Wait for visible ready/current
   and normal render updates. `#report` is compact status, not raw evidence.
3. Click **Prepare exact CPU record** (`#prepare`). Open **Exact record transfer
   status** if needed. Read small JSON from visible `#wire-status`; retain it as
   `manifest.json`. Require `ready:true` and the expected request ID. Click
   **Download prepared CPU record** (`#export`), and locate the actual download.
4. Verify the actual downloaded bytes before strict CPU validation:

   ```sh
   python3 -B experiments/73-high-poly-eyes/collect_transfer.py manifest.json --expected-request-id exact-request --download exact-request.json
   ```

   Retain `exact-request` independently from the command you issued; never copy
   the expected ID from the supplied manifest. The collector requires it to equal
   manifest, raw report and raw frame request IDs. It checks the transfer token's
   `transfer-<positive-epoch>-<envelope-sha256>` relationship. A prepare-result
   manifest may omit `ready`; if present, `ready` must be exactly `true`.

   This checks envelope/report/frame byte lengths and SHA256s, UTF-8 decoding,
   UTF-16 character count and exact concatenation framing. It rejects malformed
   or duplicate-key raw JSON, stale/unsuccessful reports and report/frame identity,
   endpoint or Work mismatch. The original bytes and number tokens are returned
   unchanged; no parsed evidence is serialized. Hashes/tokens provide transfer
   consistency, not cryptographic source authenticity or proof of live freshness. It does not validate
   geometry, pixels, source IDs or complete-matrix coverage. Run the unchanged
   `check_captures.strict_json` and `validate` on the downloaded envelope next.
5. Only if normal download cannot be obtained, use the visible **Fallback chunk
   index** input (`#chunk-index`) and **Show prepared chunk** (`#chunk-read`). Set
   each integer0 through `chunks-1`. Read visible `#wire-chunk` text after each
   click. Save each complete JSON object as one line of `chunks.jsonl`. Each is
   under45KB and contains a token, index and base64 bytes. Never accept tool text
   with `[Truncated]`, omit a chunk, silently repair JSON, or mix prepared tokens.

   ```sh
   python3 -B experiments/73-high-poly-eyes/collect_transfer.py manifest.json --expected-request-id exact-request --chunks chunks.jsonl --out fresh-envelope.json
   ```

   The output path must be new. Assembly rejects missing/duplicate/out-of-range,
   truncated/oversized, mismatched-token and same-size-corrupted chunks. Decoding
   and concatenating bytes preserves the original Rust number tokens exactly.
6. Collapse the outer controls, retain an actual A screenshot, then switch to B
   without reopening/reseeking/changing Work/camera/time/material. Repeat exact
   transfer verification and screenshot. Confirm both actual identities with the
   unchanged comparator and report pixels separately. Stop at a definitive
   failure or another capture block; no endless UI repair. One valid pair can
   support a bounded rejection/HOLD decision. Admission still requires original
   complete endpoint matrices and current eight-parameter gate.

## Source checks and limits

```sh
/opt/homebrew/bin/python3 -B -m unittest discover -s experiments/73-high-poly-eyes -p 'test_*.py'
NVWA73_REAL_CAPTURE=.work/eyes73/ui-plan/evidence-web/w73-sf-s0-A.json /opt/homebrew/bin/python3 -B -m unittest discover -s experiments/73-high-poly-eyes -p 'test_transfer.py'
```

The first runs original14 plus15 transfer tests (29 total). Node executes the exact HTML transfer
functions and actual Prepare/Download/Show-chunk handlers with DOM/Blob adapters.
Synthetic tests include signed zero and Unicode across chunk boundaries. The
second runs15 transfer checks and replays original Rust raw text from a retained14,074,462-byte Web envelope;
its bytes are never rewritten. Both are source/CPU transfer tests. Private
mutations removing currentness checks and re-encoding parsed numbers must fail. Collector
identity controls cover altered manifest IDs, ready:false, wrong tokens and a
coherently rehashed alternative header against an independent expected ID, on
both download and chunk paths. These cannot authenticate arbitrary forged bytes;
the unchanged strict geometry/source comparator is still required.

NOT-RUN: fresh R6 Rust/build/export, actual browser download and chunk clicks,
CDP control recovery, new A/B capture, whole matrices, eight-parameter acceptance,
GPU quality and intended lid fit. Rust remains the reviewed R5 source; its prior
16-test result is historical evidence, not a new R6 run.
