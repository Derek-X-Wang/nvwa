# Single GLB retrieval boundary, final R2 repair (issue #6)

Base/HEAD: `44b0ec3b129a1e19f5c8c3598f88de1e50e4e826`. All changes are uncommitted.
Production scope is `crates/nvwa-runtime/src/lib.rs` and new
`crates/nvwa-runtime/src/loading_tests.rs`. The fixture, profile, document schema,
dependency versions, Cargo.lock, manifests, Studio and core are unchanged.
`REPORT-before-r2.md` preserves the initial 28-test report and its rejected
approaches; its old reload description and artifact hashes are historical.

## Adopted byte boundary

One typed `CharacterGlb` root retrieves the source bytes once. The loader moves
that Vec into Bevy's `VecReader`, calls the registered Bevy 0.19.1 GLTF loader
through `LoadContext::load_builder().load_value_from_reader::<Gltf>`, and installs
the entire returned `LoadedAsset<Gltf>` as `NvwaGltf`. This preserves nested
scene, mesh, skin, morph, material and animation assets and their dependencies.
The root retains `VecReader.bytes` for the current document's core validation.
No independent GLTF source retrieval is used.

The current profile's frozen SHA and structural checks run before scene exposure
and Ready. Bevy parsing can precede that validation, as in the baseline. Internal
GLTF asset publication is not authorization to spawn a character scene. Loader
settings remain unit settings; the profile is not captured in path-cached loader
settings. A profile-only reopen therefore validates newly retrieved bytes against
the current profile. Parse failures retain the same bytes so core missing/hash/
container errors have priority; a core-valid parse failure surfaces as
`Character load failed`. Reader failures surface as `Asset byte load failed`.

## Publication fencing for explicit runtime opens

Bevy publishes labeled subassets before their owning root. Rejecting a stale root
completion after publication cannot stop its scene/mesh/animation labels from
replacing an active same-path generation. Runtime explicit opens therefore fence
same-path publication at the request boundary:

1. A superseding document/profile open immediately retires the old visible
   character, resets verification/readiness/playback, and queues the latest work.
2. A superseded root retains its strong handle until its actual root completion
   or failure and recursive dependencies are terminal.
3. The runtime drops that root handle and waits until Bevy removes its cached
   asset ID/normal tracked request. A later same-path retrieval starts only then.
4. A normal fresh `load` creates the replacement root. Production explicit opens
   no longer call forced `reload`. Multiple pending opens coalesce to the latest
   document/profile; old completions cannot verify the current generation.

Distinct fixed-GLB paths have distinct labeled subasset identities. A valid new
path may retrieve and become Ready while an old different-path source remains
held. Retiring roots continue to be processed even while the current work is
Ready, and their eventual completion cannot change the current root or status.
A return to a path with a still-pending retired request remains fenced.

Specific terminal reader/core errors are no longer replaced by an elapsed-time
verification error on later updates. An explicit recovery starts a fresh attempt
and clears the old error at that boundary.

## Pinned owning-source evidence

The installed Cargo registry sources, not a different Bevy version, own this
boundary. Paths below are relative to their `bevy_asset-0.19.1/src` or
`bevy_gltf-0.19.1/src` roots:

- GLTF `loader/mod.rs:1162–1181` reads the supplied reader and parses its bytes.
- Asset `loader_builders.rs:176–187,279–300` selects the registered loader by
  asset type and delegates from that reader without reopening the source.
- Asset `loader.rs:488–522,670–676` exposes nested reader loading and installation
  of the complete loaded asset tree.
- Asset `server/info.rs:397–429` recursively publishes labeled assets before the
  root. This is why late root-only rejection was insufficient.
- Asset `server/info.rs:224–256` retains settings for live path handles and
  handles the dropped-but-not-yet-tracked cache case.
- Asset `assets.rs:573–590` processes final handle drops;
  `server/info.rs:710–752` removes the normal pending task, root info and path
  mapping. The runtime waits for actual root-ID removal before same-path reuse.
- Asset `server/mod.rs:952–1006` launches the forced-reload typed/untyped fallback
  and detaches that task. Production explicit opens avoid this separate route.

## Actual red reproduction and retained requirements

The independent R2 findings are recorded in the primary checkout at
`/Users/derekxwang/Development/incubator/Nvwa/nvwa/.work/single-transfer-r2-review.md`.
Before production repairs, three real-reader regressions were added and run.
The exact red test source is retained as `r2-red-loading-tests.rs` and its log as
`r2-red-runtime-tests.log`: session `9269`, exit 101, 28 pass and 3 fail.

The async reader captures a parseable byte snapshot before a per-read barrier.
A has the fixture's head y changed to 5.1, first mesh x shifted by 5, and first
animation duration doubled; B is the frozen fixture. Both retain valid GLB
headers/chunks. A SHA-256 is
`5204fa6843bc70415f8732b0e328aa60e69c52423332cba25d89cc7f3456d07a`.
B SHA-256 is
`f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`.

- A-first: releasing rejected A while B stayed held incorrectly surfaced A's
  hash error in current B work. The repaired schedule lets A settle without a
  current scene/error/Ready, then starts and validates B.
- Attempted B-first: before the repair B could finish first, then A overwrote
  B's live scene/mesh/animation assets. The observed fingerprint changed from
  head y 0.100000024, mesh x -0.078, clip duration 3.0416667 to 5.1, 4.922,
  6.0833335. The repaired schedule asserts B cannot even start while same-path A
  is held. After A retires, B retrieves once and remains unchanged. This is a
  serialized attempted B-first schedule, not a claim of concurrent green loads.
- Long-lived Ready: after elapsed time exceeded 30 seconds, an actual async
  reader failure was overwritten by `Asset verification exceeded 30 seconds`.
  The repaired test retains the specific reader error across later updates and
  recovers through an explicit same-path valid open.

All three required tests remain in the green suite. Gates use atomic release/
failure flags plus a Waker; they do not block async worker threads. A drop guard
releases gates on test exit. No red requirement or assertion was removed to
obtain green. The historical red source's unfulfilled deprecated expectation was
removed from the current source to keep clippy clean.

## Regression coverage and actual checks

The 35-test suite has 21 existing runtime tests and 14 production-loading tests.
The new tests use the production runtime system, registered pinned GLTF loader,
actual assets, scene spawning and readiness evidence. They count source-reader
calls; they do not measure HTTP requests, rendering or GPU memory.

Coverage includes cold one-read snapshot validation; scene/skin/four morph
channels/three animations; wrong-profile then correct-profile same-path recovery;
corrupt/empty/missing then valid recovery; Ready-to-corrupt rejection; core-valid
hash-matching parse failure; one-read new-path loading; async failure after Ready;
both barrier schedules and long-lived error; superseded reader failure unblocking
the latest same-path request; pending opens coalescing to the latest profile;
immediate retirement of old root/part entities; and B Ready at a distinct path
while A remains held, with B unchanged after A's eventual terminal publication.

Final commands, run sequentially with one worker compile slot:

```sh
CARGO_BUILD_JOBS=2 CARGO_TARGET_DIR=target/single-glb-transfer \
  cargo test -p nvwa-runtime --lib --locked --offline -- --test-threads=1
CARGO_BUILD_JOBS=2 CARGO_TARGET_DIR=target/single-glb-transfer \
  cargo clippy -p nvwa-runtime --lib --tests --locked --offline -- -D warnings
```

- First repaired 31-test suite: session `26108`, exit 0,
  `r2-green-runtime-tests.log`.
- Final 35-test suite: session `54384`, exit 0, 35 passed/0 failed,
  `r2-final-runtime-tests.log`; test execution 1.30 seconds.
- Final native runtime library/tests clippy: session `53214`, exit 0,
  `r2-final-clippy.log`; `-D warnings`.
- Final formatting, `git diff --check`, script syntax and frozen artifact hash
  checks each exit 0; recorded in `r2-final-lightweight-checks.log`.

`./experiments/09-single-transfer/reproduce.sh` runs formatting, all runtime tests,
and clippy sequentially, defaulting to jobs 2 and the isolated target.
`NVWA_SINGLE_TRANSFER_TARGET_DIR` can select another isolated target. The retained
pre-R2 logs include API-name correction, malformed fixture-vector padding, and
forced-reload fallback observations; no failed attempt is presented as green.

## Rejected approaches and adoption limits

Separate byte/GLTF fetches cannot prove identical snapshots. Injecting profile
settings risks Bevy's live same-path settings cache. Copying/rebuilding the GLTF
loader broadens defaults/extensions/dependency ownership. Taking only its Gltf
value loses labeled assets. A custom asset source would require broader source
registration and invalidation work. Root-only stale rejection was reproduced as
insufficient. The bounded adopted solution uses public reader delegation plus
same-path explicit-open serialization, without dependency changes.

A source/dependency that never terminates at the same path keeps that queue
fenced. After 30 seconds the queued work reports
`Previous character load exceeded 30 seconds`; this does not cancel the source
or authorize unsafe overlap. It advances when the old request really terminates
and is purged. Specific known failure paths recover without holding the queue
forever. A different valid path remains usable while the old path is stuck.

Externally/manual concurrently forced Bevy reloads are outside this runtime-open
fence. They can be detached from the normal tracked request and publish into
shared labels; automatic live reload is not an adopted feature. Manual reloads
in the controlled reader-error tests exercise error ordering, not concurrent
reload safety. Pinned Bevy can make typed and then untyped fallback reads after a
forced-reload I/O failure while labels remain alive. The controlled missing-
after-Ready test observes two failed reads, no transferred GLB, then one successful
recovery retrieval. Production explicit opens avoid that forced-reload path.

The accepted asset is the fixed self-contained GLB with the default registered
loader. Distinct paths cannot alias its internal labels. No broad guarantee is
claimed for arbitrary external resources, shared dependencies, custom extension
handlers, alternate asset processing or watcher behavior. Core rejects external
resource references before exposure, but delegated parsing can process those
references first, as in the baseline. This adds no network sandbox.

Retiring roots retain strong handles, dependency references and pending async
resources until real completion/cache purge. No cap, timeout cancellation or RAM/
GPU bound is introduced. Many distinct never-ending paths can retain multiple
requests. Same-path queued work coalesces, and only the current character scene
is exposed. Immediate scene retirement does not prove immediate GPU reclamation.

## Frozen source and artifact identities

All SHA-256 values below are for the final 35-test source/checks:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `crates/nvwa-runtime/src/lib.rs` | 82619 | `bd6da4b2212a6bec251ad8ae4ca7b8fbca1038b383a6031cec1b9c0fa1b8ce72` |
| `crates/nvwa-runtime/src/loading_tests.rs` | 24394 | `9fec6b200db271117b26db45eef2758820f644a8bbc7ef4e74de4d8cc9a8c26a` |
| `r2-final-source.patch` | 42242 | `1f53696336ac9a31e334a8034cadd4553fcc67d7c4644119f17ef88cf57c1c1d` |
| `r2-red-loading-tests.rs` | 20346 | `0215921182d69dfbd32a4f53852e531aa847bdf8d3fee7b35459052d1e77bc4d` |
| native test executable `nvwa_runtime-74980f9e59502172` | 88279968 | `f2d0fb53d769a543e60e575dc057623de46ade1d092c54570cbde636594ac513` |
| native library metadata `libnvwa_runtime-e91db866af5cfb84.rmeta` | 201397 | `a1c83f7d7c84b88cd6ece674cb673f92ae641b406f328c227c7ec07559d9ed47` |

The source patch is against base 44b0ec3 and includes tracked lib.rs plus the new
untracked loading_tests.rs. It excludes experiment/report files. Test executable
and metadata reside under `target/single-glb-transfer/debug/deps/`. The executable
is Mach-O arm64. No new linked runtime `.rlib` was emitted by these checks; cloned
older rlibs are not current evidence. Downstream Studio must build/link the
patched runtime. The unchanged published fixture is 3,827,840 bytes with B's SHA.

Local macOS arm64, Rust/Cargo 1.95.0. No GPU/UI, native release, Wasm, HTTP/network
measurement, upload, commit, push or PR was performed. Root owns cross-model
rereview, integration, workspace/release/Wasm checks, actual cold/error/recovery
GUI and HTTP A/B acceptance. These remain NOT-RUN in this worker.

## Resource and cleanup state

No task-owned service, port, watcher, UI session, PID or Cargo session remains
live. The test gates are released on exit; temporary filesystem fixtures are
removed by completed tests. The dirty worktree, experiment evidence and ignored
`target/single-glb-transfer` remain for root review/integration/cleanup. The target
was initially clone-copied from primary dependency artifacts into
`target-single-transfer`, then moved to the ignored target directory; old logs
retain the initial path. No target-seeding or compile work is still running.

Completed sessions: `8335` exit 1 (initial fmt suggestions), `8843` exit 101
(initial API typo), `23061` exit 101 (vector padding), `12071` exit 0 (27 tests),
`45122` exit 101 (forced-reload count observation), `17522` exit 0 (28 tests/clippy),
`9269` exit 101 (R2 required red), `26108` exit 0 (31 tests), `54384` exit 0
(final 35 tests), `53214` exit 0 (final clippy). Root is cleanup owner.


## Root integrated checkpoint (later than worker freeze)

Root integrated the exact two frozen source files over `bf536f8`, without dependency/lock/fixture/schema changes.93 full-workspace tests, fmt, strict native/Wasm clippy, native release/package, Web release and real CLI profile capability checks exited0. Actual no-store Web comparison against PR18 `de9dac0` reduced GLB GETs2→1 and actual compressed body bytes2,258,162→1,129,081. Real Player Ready/restart, missing asset rejection/recovery and final-byte hash rejection/recovery passed via the actual file chooser. The standalone worker35-test report above remains unchanged in meaning. Independent R2 findings and accepted repairs are retained in the root evidence directory.

[Integrated acceptance](../../docs/evidence/single-transfer/ACCEPTANCE.md), [exact manifest](../../docs/evidence/single-transfer/build-manifest.json) and [HTTP capture](../../docs/evidence/single-transfer/http-requests.jsonl) own these later results. Native process/Ready passes, but screenshots are black with a CUA-confirmed locked Mac; unlocked native visual acceptance remains NOT-RUN. Cold startup/GPU/memory and true zoom/DPR are not claimed. The root diagnostic tabs/native processes/9202 server have exited;9201 production preview remains.

Recheck the retained real HTTP capture:

```sh
python3 experiments/09-single-transfer/summarize_http.py docs/evidence/single-transfer/http-requests.jsonl
```

To repeat live A/B, recreate the baseline at the exact PR18 commit and the candidate from the containing commit in isolated directories, build each sequentially, freeze each Web bundle, and serve a parent directory containing `baseline` and `candidate` with:

```sh
python3 experiments/09-single-transfer/http_probe_server.py --root /absolute/probe-root --log /absolute/new-http-capture.jsonl --port 9202
```

Open `/baseline/?player=1&work=works/m1-sequence.nvwa.json` and `/candidate/?player=1&work=works/m1-sequence.nvwa.json` sequentially, observe real Ready/restart, and close the first renderer before opening the second. Preserve new source/artifact identities. For recovery, use `fault.nvwa.json` and a disposable `candidate/assets/fixtures/nvwa-fault.glb`: absent→exact frozen fixture→last byte XOR1→exact frozen fixture; reopen with the actual Player chooser at each step. Compress the corresponding disposable copies with gzip mtime0. Never alter the published fixture. Preserve actual screens and separate response bodies from unique file sums. This is no-store HTTP transfer verification, not a cold compiler/GPU benchmark.


The exact worker source patch is stored as `r2-final-source.patch.gz` (gzip mtime0). Its decompressed bytes retain the SHA/table identity above. This preserves literal diff context spaces without treating the patch text as production trailing whitespace. Extract with `gzip -dc experiments/09-single-transfer/r2-final-source.patch.gz > /tmp/nvwa-single-transfer-final.patch`; the primary production source has no trailing-whitespace errors.


Later acceptance update: Derek manually unlocked the Mac. The same current native binary (`3be9380f…`) now exits0 with a visually inspected real character playing wave, revision9 and18 joints/4 morphs/3 timeline entries. [Unlocked native evidence](../../docs/evidence/single-transfer/native-unlocked.png) supersedes only the earlier blocked visual result; both black captures remain retained failures. This is a functional smoke, not a current performance benchmark. PR18 is merged at `07858fe6b5d6062200d28df654c5ce53ad89007b`, with #1/#19 closed; #2/#3 remain open. PR20 remains pending merge; PR21 completes local acceptance and is pending review/merge.
