# Disposable viewport boundary diagnostic

This appends read-only DOM measurements to a **copy of the current Web dist**. The original `index.html` bootstrap, Wasm, JS bundle, and assets are reused. It does not change the canvas size, CSS, DPR, editor input, or Rust state. No dependency installation or compilation is needed. The installer supports Python 3.9 or later; actual Python 3.9.5 execution is verified. SHA256 uses portable chunked reads.

## Install and collect

Run from the integration checkout after copying this experiment directory there:

```sh
python3 experiments/13-viewport-boundary/install.py /absolute/path/to/current/dist/web /absolute/path/to/new-disposable-dist
```

The destination must not exist and must be outside the source dist. The source must be self-contained, with no symlinks. The installer appends `diagnostic-panel.html` before the real index's `</body>` and adds `viewport-boundary.js` plus `viewport-boundary-manifest.json`. If the source has `index.html.gz`, the copied sidecar is regenerated from the patched HTML with gzip `mtime=0`. A gzip-preferring server can then serve the same diagnostic page for explicit `/index.html`. The manifest lists both HTML and its existing gzip sidecar as intentional changes. Every other source file is checked for byte equality. The source is never written.

The integration owner should serve the disposable copy through the already authorized localhost server and GPU slot. Open its ordinary `index.html` with no `benchmark=1` query. No server, browser, app, or GPU was started by this workstream.

The collapsed **Viewport measurements** panel is fixed at the lower right. It does not participate in canvas layout. It will cover a small area, so avoid that area during app input. The collector starts a bounded 180-second, 1 Hz measurement window automatically. After that it records only resize, focus, visibility, page lifecycle, canvas-attribute, and supported observer events. The ring retains 180 records; `droppedRecords` reports overflow. Click **Record next 180 seconds** before another case if needed, then collapse the panel and refocus Work. These samples are diagnostics, not timing benchmarks.

Use a documented read-only DOM inspection to collect:

```js
JSON.parse(document.getElementById('viewport-boundary-json').textContent)
```

This reads a DOM JSON node, not app internals. The node contains recorded samples; it does not take a fresh sample when read. A sample at most one second old is expected while sampling is active and the browser is scheduling the page. Hidden-page throttling can delay samples. The collector has no editor/runtime API.

The **Download viewport measurements JSON** button exports the complete retained report through a user-activated download. **Snapshot geometry** takes a sample, but clicking any diagnostic control can move focus away from Work. For caret checks, use the passive samples taken while Work was focused and record a screen image of the same state. No input values, typed text, selection text, keyboard events, pointer events, clipboard, or document contents are read by this collector.

Keep the copied dist's `viewport-boundary-manifest.json` with actual screenshots and full saved Work documents. Saved Work documents must come from the app's ordinary Save action. This collector cannot establish an edit, Undo, or persistence pass.

## Cases for the integration owner

| Case | Required observation | App action and verdict |
| --- | --- | --- |
| Ordinary Web baseline | Actual CSS/client rectangle, buffer dimensions, reported DPR, visual viewport scale, focus and input-proxy geometry after boot settles | Click Work, type a task-owned name, inspect caret, Save full baseline. No assumed DPR. |
| Resize to 1600×900 | Samples before resize, resize event, and settled geometry after at least one second; actual reported DPR | Refocus Work, type, Save baseline, drag jaw once, Save changed, Undo once, Save restored. Compare whole parsed documents; only revision may differ for Undo equivalence. |
| Resize to 1024×768 | Same boundary samples, visible caret and text target | Repeat focused typing and save; repeat drag/Undo only if the complete control is visible. Record any unavailable UI as a limit. |
| Restore ordinary viewport | Use the documented viewport reset, then settled boundary sample | Verify focused typing/caret again. Width/height resizing is not DPR emulation. |
| Ordinary native scale 2 | Existing actual native log/screen reports scale factor 2 and physical dimensions | Integration owner/native worker uses the ordinary binary. Verify text/caret and one drag/one Undo with full saved documents. This Web collector cannot measure native scale. Do not change OS display settings to create this case. |
| Actual browser tab hide/show | Real `document.visibilityState` hidden→visible event pair, followed by actual focus state | Use only a current interface that truly changes browser tabs. Refocus Work, append task text, Save; repeat drag/Undo if in scope. Merely binding/creating an independent task surface does not prove tab hide/show. |

Preserve stage labels outside the JSON, with capture times or sequences. Download one report before moving to the next stage if a long case would push important records out of the ring. An unchanged DPR means a size-only resize case. If no current interface exposes DPR changes, browser zoom, or real tab transitions, record **NOT-RUN — interface unavailable**, not failure or success.

## Interpret the fields

- `canvas.rect` is the rendered CSS/client rectangle; `canvas.client` excludes borders. `canvas.buffer` reads actual HTML canvas `width` and `height`, separately from those rectangles.
- `bufferPerCssPixel` is an observed ratio. `cssTimesDprEstimate` is explicitly an estimate, not Bevy/Winit/egui state. For the ordinary, borderless full-window page, a settled ratio near reported DPR is an expected consistency observation. Rounding and browser reporting limits remain possible.
- `latestResizeObserver.devicePixelContentBoxSize` is browser-reported device-pixel content size when the API supplies it. A missing/empty box is unavailable, not a zero-sized rendering surface. `observedAt` shows how old that last observer result is.
- `visualViewport.scale` is reported separately from DPR. Neither is treated as an observed egui zoom factor.
- `textInputGeometry` records up to eight generic textarea/input rectangles and styles. It records no values. These can show the current invisible text proxy position; a screen is still needed to judge whether its position matches the drawn caret.
- Winit/Bevy scale, camera target scale, egui pixels per point, and an actual input-coordinate event are **not directly observed**. The local source excerpts describe how they are intended to connect.

## Verification and cleanup

`checks.json` records actual Python 3.9.5 execution, portable SHA256 identity, JS syntax, Python parse, installer byte preservation, exact gzip decompression, zero gzip timestamp, and byte repeatability across two installs against an actual existing dist. `checked-dist-manifest.json` preserves that check's source hashes. Those temporary copied dists were deleted. These checks did not launch the application or an HTTP server.

`packaging-failure-evidence.json` preserves the stale-sidecar failure: an unchanged original gzip sidecar decompresses to the original HTML, which lacks the diagnostic node and differs from the patched HTML. The initial insufficient disk checks are retained as `checks-before-sidecar-fix.json` and `checked-dist-manifest-before-sidecar-fix.json`. `artifact-sha256.json` freezes the final artifact file hashes.

`python39-failure-evidence.json` preserves the actual Python 3.9.5 failure from the earlier `hashlib.file_digest` call, including its traceback and proof that no destination was created. The checks before the portability correction are retained as the two `*-before-python39-fix.json` files.

The only repository changes are this experiment directory. No production, dependency, lockfile, shared evidence, or shared document was edited. No server/process/browser/GPU was started. Cleanup is deletion of the newly created disposable dist after retaining needed proofs; no production cleanup is required. The integration owner should reset any viewport override used during actual collection.
