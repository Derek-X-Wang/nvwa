# Bounded first-presentation, GPU and memory follow-up (#4)

PARTIAL — Three native processes and three Web loads actually displayed the
same real humanoid Work. Native diagnostics produced reported surface-display
timestamps, real GPU-command samples, PID-qualified memory and actual character
readbacks. Web HTTP/CPU boundaries and JS heap estimates reconcile; the actual
GPU timestamp attempt has invalid results and remains unaccepted. Issue #4
stays open; issue #3 stays blocked by its unavailable original DPR reproduction.

## Fixed inputs and actual execution

- Accepted main: `d832ef3e044017bddb5a0681ff5ca99256ebaef4`.
- Same revision0 natural-idle Work,1,624bytes, SHA256
  `ff0b8e36adfc3ebadc5fc700a4c760f6f551273b56e85bf336563e18b63eb445`.
- Real fixed humanoid:18joints,9meshes/skins,4morph weights,one animation player.
- Canvas1280×720/DPR1; native window captures1280×784 include64px title chrome.
- Original native binary SHA256 `72d3df8cfdeea062282c8731b0a95cb971f90976fe881772f3e3c24afe76973a`.
- Independent diagnostic binary SHA256 `31999ece7a4b74875ac254eb15ebb8fad08e73e8880ca8a3fbd68c5026af8a6c`.
- Original Wasm SHA256 `d890dfee73e9eeeee6ce3d82f255c79979e8c8b6bed90243c6101f8e1c1763a8`.

Root controlled the only task-owned renderer. No task-owned heavy build ran
during acquisition. User applications and system caches remained uncontrolled;
native inventories retain other active CPU consumers. This is not an
uncontended whole-machine benchmark. Diagnostic observers and three extra
native readbacks perturb the measured program; their results are separate from
the unchanged release baseline. One standalone diagnostic release build ran;
the existing baseline and Wasm were reused. Root dependencies, Cargo.lock,
CI configuration and character assets are unchanged.

The three native runs exit0 with exact child/group absence and reaping receipts.
Both Web servers exit0,port9205 is free,owned tab54 is closed,and the temporary
viewport override is reset. [Root lifecycle readback](common/lifecycle-root-readback.json).

## Results and meaning

| Measurement | Actual result | Boundary |
| --- | --- | --- |
| Native recorded surface display | Diagnostic1 index5:9.963883–9.967385s; repeat index2:1.745521–1.749544s after external launch | Earlier callbacks report zero and remain retained. Metal/CA host time is calibrated per callback to CLOCK_MONOTONIC; intervals include launch/reading brackets and clock resolution allowance. They do not bound undocumented driver accuracy or prove character pixels in that surface. |
| Native character readback | First main-update PNGs are blank. Diagnostic1 first-ready callback9.947958–9.951460s has a real character; UI still says Preparing | GPU readback observation differs from display. The two Ready+2s and all three final PNGs show the character and Ready UI. |
| Native GPU | Each diagnostic has134submitted command samples;p95 0.537750/0.381750ms | Retain zero-duration commands and other command kinds separately. No overlapping-duration sum,full-frame claim or sustained-character workload association. |
| Native baseline memory |115samples;maximum RSS209,977,344bytes;maximum physical footprint295,781,552bytes | PID and kernel birth checked. RSS and physical footprint overlap; do not add them or Metal device resource allocations. Sample maxima differ from the separate kernel-reported lifetime maximum. |
| Web startup | First submit CPU return956.0/1192.1/1188.3ms;GLB responseEnd1158.2/1399.0/2124.3ms | Each uses its own navigation clock. Submit precedes character download in every case,so it cannot mean first character frame. |
| Web GPU attempt | Four compute0/0 query records;two UI65,536ns records;two nonmonotonic errors | Actual attempt ran. StatusNOT-RUN means no accepted GPU timing result. Do not infer zero compute cost,character cost or a failure cause. |
| Web JS memory |30samples/load;maximum19,292,318 /21,151,025 /20,179,465bytes | Coarse browser JS heap subset;not process RSS,complete Wasm,physical footprint or GPU memory. |

[Native results and reproduction](../../../experiments/33-native-present-metrics/RESULTS.md)
and [Web results and reproduction](../../../experiments/34-web-cold-metrics/RESULTS.md)
include full tables, source identities and raw-packet references. All retained
pixels are actual captures; no static substitute, mock or generated animation
was used. Root and the native worker inspected all nine native PNGs. Cua
original JPEG bytes, call/output attribution and observation brackets are in
[visual/](visual/). Their host UTC clocks are not converted into Bevy or browser
monotonic clocks.

Web production Ready/idle/revision0 and18joints/4morphs appear in three exact
`NVWA_EVIDENCE` entries. First AssetReady values0.4056/0.4240/1.1601s and delayed
capture callbacks15.4356/15.4766/16.5365s use the Bevy first-update clock; the
requested15s warmup is not first display. Native stdout/stderr contain no such
INFO record in these runs,so current native main-loop cadence is NOT-RUN.

## Preserved failures and decisions

The first actual Web checker rejected the automatic favicon404. The corrected
checker requires the exact same-origin19-byte404 response and Chrome155's
observed319-byte transfer estimate. The original failure and independent
20/318/320 transfer counterexamples remain. Only checker/tests changed; actual
raw data, wrappers and production inputs stayed unchanged.

Initial native clock controls exposed Python monotonic_ns differing from C
CLOCK_MONOTONIC on this Mac. Launcher anchors were corrected and real bracket
controls passed. A later interpreter executable guard rejected a Homebrew
trampoline; the fixture was repaired to use the observed interpreter,while
the production executable/birth guards stayed strict. Failed and restored
controls remain in native/controls and review/preparation.

Native strict bundle signature verification failed for both baseline and
diagnostic artifacts. Those failures remain recorded; no signing,permission,
Gatekeeper or security settings changed. Actual app launches subsequently
displayed the character and exited normally.

Adopt the measurement boundaries and reproducible evidence. Keep the native
observer and Web query variant isolated. Do not adopt a product performance
fix: neither startup-stall attribution nor an accepted Web character GPU timing
result exists.

## Cold-state and remaining scope

New native processes and new Web navigation clocks are established. Fresh Web
prefixes,no-store responses and exact complete transmitted bodies establish
the HTTP cache boundary. The second baseline uses the same tab/URL after an
about:blank pause;it is not a literal reload or cache-hit benchmark.

NOT-RUN — fully cold OS file cache,Metal driver/shader cache,browser process,
Wasm compiler and WebGPU caches;exact first physical character presentation;
native stall attribution;current native cadence;accepted Web character GPU
timing;browser process RSS and total GPU memory. Current IAB capabilities expose
no isolated browser/process/cache or physical presentation API. No reboot,
cache purge,alternate driver,paid resource or extra fourth load was used.

## Recheck without launching an app

```sh
python3 docs/evidence/bounded-perf-20261013/verify.py
python3 experiments/34-web-cold-metrics/check_metrics.py --capture docs/evidence/bounded-perf-20261013/web/baseline-http/1c1f52dcadf5449ba40195226e16f287-attempt1-browser.json --manifest docs/evidence/bounded-perf-20261013/web/baseline-http/manifest.json --requests docs/evidence/bounded-perf-20261013/web/baseline-http/requests.jsonl --run 1c1f52dcadf5449ba40195226e16f287 --attempt 1
python3 experiments/33-native-present-metrics/reconcile_native.py docs/evidence/bounded-perf-20261013/native/runs/diagnostic-1/stderr.log --pid 70636 --output /tmp/nvwa-native-perf-recheck.json
```

The manifest binds exact archived bytes,all524accepted source inputs and the
experiment source files. It excludes its own manifest and the human-readable
acceptance/review pages from the byte inventory;their claims receive independent
review. The verifier reads no dist/.work file or live browser. It confirms
provenance,not a new runtime benchmark. Full execution commands and the strict
three-run protocols remain in the experiment READMEs.

Downloads cleanup receipts and the13preserved unique works are deliberately
private and outside this publication packet.
