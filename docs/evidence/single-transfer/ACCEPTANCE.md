# Single GLB retrieval: integrated acceptance

Source: `fix/single-glb-transfer`, based on `bf536f8` (the history PR), with exact
runtime hashes in [build-manifest.json](build-manifest.json). PR18 is now merged to main at `07858fe6`; the current production artifact bytes remain identical to the tested integration. This is a new
integrated release, not a relabelled PR18, worker or historical performance run.

## Compilation and independent review

93 workspace tests passed, zero failed/ignored. Formatting, strict native and
Wasm clippy, native release/package, Web release and the real release CLI profile
capability probe all exited 0. [gate-exits.json](gate-exits.json) and logs retain
the commands. Dependencies, Cargo.lock, document schema and fixture are unchanged.

Independent R2 found a P1 late same-path subasset publication race and a P2
specific-error/timeout ordering error. Three real-reader tests reproduced them
before repair (28 passed/3 failed); the final runtime has 35 passing tests.
[Review](REVIEW.md) and [targeted rereview](REREVIEW.md) accept the repaired bounded
runtime-open guarantee with zero open findings. This is source/evidence review;
the reviewer did not independently build or operate UI.

## Actual Web HTTP A/B

One renderer at a time; no heavy compile or other performance test ran during
the comparison. The loopback [probe server](../../../experiments/09-single-transfer/http_probe_server.py)
served immutable baseline/candidate bundles on9202 with `Cache-Control: no-store`.
Baseline is PR18 `de9dac0`, Wasm `6aa960bc…`; candidate includes the history repair
and current runtime, Wasm `0d8e1b79…`. Both use the same frozen GLB and three-action
work. [Bundle manifests](baseline-bundle-manifest.json) and
[candidate manifest](candidate-bundle-manifest.json) preserve full identities.

| Observed quantity | Baseline | Candidate |
| --- | ---: | ---: |
| Successful GLB GETs | 2 | 1 |
| Actual compressed GLB response body bytes | 2,258,162 | 1,129,081 |
| All initial HTTP response body bytes | 21,656,114 | 20,541,440 |

The GLB saves exactly **1,129,081 bytes**. Total response bodies save1,114,674bytes;
that figure includes the different compiled bundle and one fewer404 `.meta`
response. It is not pure runtime size savings. Directory index HTML was served
uncompressed. HTTP headers/TCP overhead are excluded. No-store and fresh URLs do
not prove cold Wasm compilation, GPU startup, exact first presentation or browser
memory. [Raw capture](http-requests.jsonl), [summary](http-summary.json) and the
[capture checker](../../../experiments/09-single-transfer/summarize_http.py)
make the response-count/byte result reproducible without implying a GUI driver.

The actual Player reached `Ready · skin + morph + animation` in both versions.
Candidate Restart visibly resumed idle from0seconds; the three-action work
completed on turn. Screens: [baseline](web-baseline-ready.jpg),
[candidate](web-candidate-ready.jpg), [active animation](web-candidate-animation.jpg).

## Actual missing and changed-asset recovery

On the same running candidate Player, the real file chooser opened
[fault.nvwa.json](fault.nvwa.json), which changes only the fixture path.

1. A missing file returned404. The old character disappeared; the Player showed
   `Asset byte load failed: Path not found` and no fallback character.
2. Copied the exact frozen GLB to that disposable candidate path. Reopening the
   same work retrieved once and returned Ready with actual animation.
3. Changed only the final GLB byte (XOR1), keeping the original profile hash.
   Reopening retrieved once, showed `asset_hash_mismatch`, and exposed no character.
4. Restored the exact frozen GLB and reopened the same work. One retrieval returned
   Ready and real animation again.

[Injection identity](fault-injection.json), [missing](web-missing-error.jpg),
[missing recovery](web-missing-recovered.jpg), [hash rejection](web-hash-error.jpg)
and [hash recovery](web-hash-recovered.jpg) preserve outcomes. Only disposable
copies changed; the published fixture/profile and normal release stayed intact.
This checks missing/changed bytes; it is not a visual test of every malformed GLB.

## Native execution, failed locked captures and unlocked acceptance

Both actual packaged native Player launches exited0, loading exchanged revision9
with18 joints,4 morph weights,3 timeline entries and one active animation on Metal
M2Pro. [Logs](native-current.log) and [extracted evidence](native-evidence.json)
record this. However, both2-second and6-second captured PNGs are black. CUA then
reported that the Mac is locked and could not unlock it. Runtime Ready and capture
success are **not** visual acceptance. Both failed captures are retained. Derek subsequently unlocked the Mac. A third launch on the same exact native binary exited0 and produced [native-unlocked.png](native-unlocked.png), visually inspected: the real character is waving, Player reads Ready, revision9/18 joints/4 morphs/3 timeline entries/1 active animation are recorded in [native-unlocked.log](native-unlocked.log). Current native visual acceptance therefore passes.
The previous history branch's valid native screenshot is separate evidence.

## Limits and lifecycle

Same-path runtime opens serialize until the old actual load finishes/fails and
Bevy removes its cached root ID. Queued opens coalesce to the latest document.
Different paths can recover while a prior reader remains held. A permanently
pending same-path load remains fenced;30seconds reports the wait without pretending
to cancel it. Pending roots/resources have no memory/GPU cap. External/manual
concurrent forced reloads, automatic watchers, arbitrary shared external resources
and custom loaders are outside the guarantee. Immediate scene removal does not
prove immediate GPU reclamation. The supported fixture is self-contained.

No current formal startup/cadence/GPU/memory benchmark, additional browser/OS,
physical IME retest, hosted CI, public hosting or signing was performed. Both probe
tabs and native processes exited;9202 diagnostic server stopped. The existing9201
production preview remains for Derek. Both worker checkouts are confirmed archived and their ignored build caches absent; disposable A/B copies were removed after preserving evidence. [Cleanup](cleanup.json). PR21 has completed bounded local acceptance and can leave draft after this evidence is published.

```sh
cargo test --workspace --locked
bash experiments/09-single-transfer/reproduce.sh
python3 experiments/09-single-transfer/summarize_http.py docs/evidence/single-transfer/http-requests.jsonl
```

VERIFIED —93 tests, strict checks, dual release builds, actual native/Web character/animation,2→1 GLB requests and missing/hash same-path recovery passed. PARTIAL —current cold-start/GPU/browser-memory and broader platform coverage remain NOT-RUN.
