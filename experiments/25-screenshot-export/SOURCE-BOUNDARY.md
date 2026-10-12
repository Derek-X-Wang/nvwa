# Current source boundary: capture callback vs persistent PNG

These are current local primary-source observations from the assigned worktree,
not remembered/browser-policy claims. Source inspection constructs the bounded
comparison. It does not select a cause or prove that the historical IAB symptom
still occurs. Root must run the actual download feedback loop.

## Studio and frozen Web adapter

- [`web/index.html:27`](../../web/index.html#L27) (identical bytes to frozen
  `dist/web/index.html`) adds the explicit Download button only in benchmark
  mode. Lines 33–48 read the real canvas through `toBlob`, handle null, create a
  blob URL, append/click/remove an anchor, and revoke after 1000 ms. The comment
  at lines 28–29 records the earlier embedded-browser observation; it is not
  current diagnosis evidence or an independently verified browser-policy rule.
- [`crates/nvwa-studio/src/lib.rs:351`](../../crates/nvwa-studio/src/lib.rs#L351)
  and lines 408–415 accept only `player`, `work`, and `benchmark`. Web query
  parameters `capture` and `smoke-seconds` have no effect. Lines 423–428 fix the
  automatic benchmark path to `nvwa-web-benchmark.png`, warmup to 15 seconds,
  and timeout to 60 seconds.
- [`crates/nvwa-studio/src/lib.rs:1133`](../../crates/nvwa-studio/src/lib.rs#L1133)
  records capture completion on `ScreenshotCaptured`. Lines 1176–1184 spawn
  the actual primary-window screenshot and attach separate `save_to_disk` and
  `capture_completed` observers. The callback does not contain a browser file
  receipt. Lines 1197–1210 set Wasm `capture_file_bytes` to zero and define Web
  capture completion from the callback alone; native additionally requires a
  fresh nonempty file. Lines 1242–1246 print the callback and byte count.
- [`dist/web/nvwa_studio.js:164`](../../dist/web/nvwa_studio.js#L164), lines
  232–233, and lines 1316–1317 call the element's `.click()`,
  `URL.createObjectURL`, and `URL.revokeObjectURL`. The experiment hooks those
  exact browser boundaries rather than regenerating Bevy screenshot bytes.

## Exact installed Bevy 0.19.1 primary source

Dependency source file:
`/Users/derekxwang/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/bevy_render-0.19.1/src/view/window/screenshot.rs`.
`Cargo.lock:328–329` pins the Bevy version to 0.19.1.

- Lines 133–143: `save_to_disk` clones the actual captured image, converts it to
  a dynamic image, derives format from the filename, and drops the HDR alpha
  channel by producing RGB8.
- Lines 156–167: the Wasm branch encodes that image and creates a blob URL.
  `Blob::new_with_u8_array_sequence` is used without a MIME options object.
- Lines 170–180: the Wasm branch creates an anchor, sets `href` and `download`,
  clicks it without appending it to the document, then revokes its URL in the
  same synchronous function. There is no persistent-file receipt check here.
- Lines 184–186: `Ok(())` logs `Screenshot saved to ...`. In this Web branch,
  that means the called JS operations returned without error. It does not
  establish durable download completion.
- Lines 203–210: Bevy triggers `ScreenshotCaptured` once it receives a captured
  render image. It does not trigger this event from a browser download receipt.

These sources show three distinct boundaries: render image available, browser
export operations attempted, and an actual saved file independently observed.
Only root's real file inspection can establish the third.

## Snapshot hashes at worker inspection

| File | SHA-256 |
|---|---|
| `web/index.html`, `dist/web/index.html` | `73ea243ebc795ec5d405489e8aaeaca4ebe18b537e4b90fa433f5bbe0e2f5114` |
| `dist/web/nvwa_studio.js` | `9ff532cbedc6a814c4b8337c4b82f436de452e7b7fbc8c9e58bfda2e90ad6c5c` |
| `dist/web/nvwa_studio_bg.wasm` | `884134fc98d54e3476dbc799ffdd5cc6b88f69121ddfb649ed9ba9be96156dba` |
| `crates/nvwa-studio/src/lib.rs` | `876329eb625aed45ce4229ea0277c8949a1337d2ff147e5caa25e17e48981f8e` |
| Installed Bevy `screenshot.rs` | `f49e4ca4f0929fc51a5c55fc002294c6009ae7a4c1c07dc6ef6c8ff737df0c5b` |

Hashes identify inspected files; they do not by themselves establish that the
frozen Wasm was built from every current source byte. Root retains build/runtime
provenance and verifies the served frozen artifact hashes.

## Experiment intervention boundary

[`export-probe.js:43`](export-probe.js#L43) wraps actual canvas `toBlob` calls
and retains null/error behavior. Lines 65–80 observe blob URL creation.
Lines 81–105 observe actual PNG anchor clicks; B/D additionally attach the
original automatic anchor. Lines 106–137 observe revocation; D adds the separate
1000 ms delay only to the automatic benchmark screenshot. B/D remove their added
anchor after actual revocation. Lines 140–151 restore adapters and release
pending URLs on Stop. Lines 198 onward install the hooks after iframe load;
the actual case must prove that installation precedes capture.

No product fix is proposed from these source differences. A/B/D/C runtime results
remain NOT-RUN until root captures them in the actual IAB and checks real files.
