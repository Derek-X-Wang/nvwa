# Desktop Web Control-key acceptance

Production source SHA256 `30ee884731913c0d65bbaccb9e29b06e5681d82e25a8a95c4337fa9a043cb2d7`, parent `44b0ec3b129a1e19f5c8c3598f88de1e50e4e826`. New Web Wasm SHA256 `6aa960bc21a85a16c05a42083a7f2c01414531638477274f69d00ebba5b677f2`. Exact source/build identities and gate exits are in [manifest](build-manifest.json).

The independent final review found a P2: supported Control editing/navigation keys were dropped by the desktop proxy. The repair forwards these events to the existing egui editor and initializes desktop platform metadata before event processing. It adds no alternative text-editing algorithm. [Final review](../web-input/FINAL-REVIEW.md) and [targeted rereview](REVIEW.md) preserve that gate.

## Compilation and regressions

Root ran the recorded commands in gate-exits.json: **71 workspace tests, zero failed/ignored**, fmt, strict native/Wasm clippy, native release build/package, Web release build and the real pinned-egui probe; all exit0. The retained red probe has8 passes/3 failures; green has12 passes. The previous67-test input/physical acceptance and59-test font-only acceptance retain separate source identities.

Native executable/package bytes remain exactly `ab32a2b1ad8ecd7efdc998b40e536bdbc01e84fdb9f47d9b72b644379aa829f3`; this wasm-only production repair does not change native bytes. Native startup was not repeated at this checkpoint; earlier actual startup belongs to that identical binary. The rebuilt Web actually started and displayed the real skinned/morphed animated fixture at revision6.

## Actual browser callback evidence

Root used one task-owned Codex in-app Browser surface at1280x720, DPR1 on the same M2 Pro host. No user test input or clipboard was inspected. The disposable diagnostic page imports the rebuilt Wasm at a unique query URL and logs only task-owned keyboard events.

1. An initial CUA `pressKey(null,"ctrl+h")` left `abc` unchanged. The trace in `cua-control-h-trace.txt` proves this API sent `key:h,ctrl:false,meta:true,isTrusted:true`. This is a transport-tool limitation, not evidence of a remaining production Control defect. Older `control-h-after.jpg` and viewport `control-h-before-fix.jpg` are retained but are invalid Control reproductions.
2. A diagnostic button dispatched explicit DOM Control+H. The trace records `ctrl:true,meta:false,isTrusted:false` and preventDefault=true. Installed production callbacks changed `abc` to `ab`. This synthetic path is distinct from trusted keyboard injection.
3. Documented Playwright `locator('#nvwa_text_input').press('Control+h')` delivered `ctrl:true,meta:false,isTrusted:true`. The captured callback path deleted again: `ab` became `a`. See `playwright-control-h-trace.txt` and `control-h-green.jpg`.
4. Command+A replaced that task-owned text with `abc`. Explicit Control+A then typed `X`, producing `Xabc`, establishing the runtime macOS platform/cursor behavior; see `control-a-trace.txt` and `control-a-green.jpg`.
5. The unmodified production index was reopened and the same explicit Control+H changed `abc` to `ab`, visible in `production-control-h-green.jpg`. The diagnostic overlay was absent.

All events still reach the normal egui Work editor. Physical human Control-key checks were not performed. The prior user acceptance for Chinese candidate input/Space, Command+A/V and cross-app refocus belongs to the67-build and is not relabelled as71-build evidence.

## Reproduction and limits

Run `cargo test --workspace --locked`, `bash scripts/build-web.sh` and `python3 scripts/serve-web.py`. In a desktop Mac browser, click Work, type `abc`, move to End and press actual Control+H: expect `ab`. Control+A then `X` should insert at the row start. Automated injection must verify Control rather than Meta. `control-debug.html` and `control-trace.js` preserve the diagnostic source; copy them to dist/web only for local diagnosis.

The current unique HTML/JS/Wasm/GLB gzip sum is20,524,320bytes (Player20,524,843), smaller than the preceding67-build20,529,790. It is not a cold-start measurement. Mobile, extra browsers/platforms, browser-tab recovery and actual zoom/DPR remain NOT-RUN; width/height-only validation is [separate](../../../experiments/11-viewport-input/REPORT.md). No hosted CI, paid resource or public hosting was used.

VERIFIED — root gates, actual rebuilt Web startup and explicit Control callbacks passed; source rereview accepted. PARTIAL — broader physical/platform/zoom coverage remains open.
