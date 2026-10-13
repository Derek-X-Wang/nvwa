# M1.1 bounded candidate — 2026-10-13

PARTIAL — permanent CPU paint checks, the four-root loading policy, complete
workspace checks and actual candidate Web recovery pass. Native visual
acceptance, real tab raster positive/mutant cases and candidate hosted CI remain
pending. Baseline hosted run38286368500 is not evidence for this candidate.

## Mainline changes

Six permanent tests call the production editor painter at1280×720 and1024×768.
They check literal independent tab colors, text, geometry and clipping while
preserving the complete Work/history. A paint-only mutation fails the new color
check while the old state test remains green. Original mutation receipts and
the later lint-only repair/re-review are separate cohorts. Existing CI runs
`cargo test --workspace --locked`, so it collects these tests automatically.
No GPU runner, dependency or workflow expansion is needed.

The runtime admits at most four active/retiring root requests and retains one
latest pending request. Waiting and errors remain visible. Completed requests
must leave asset tracking before a slot is reused; this is not cancellation.
Production-called stalled-load controls reproduce12 roots before the change,
four after it, and latest-only recovery. Eighteen loading controls pass. The
HTTP test adapter's initial incomplete-body failure, exact transport mutation
and repaired full-body controls are retained.

This bounds root-request count. It does not bound content bytes, dependent
asset count, loader tasks or GPU memory. Native GUI whole-Work recovery remains
pending; headless runtime controls are not relabelled as native GUI acceptance.

See [UI evidence](ui-paint/README.md) and
[loading experiment](../../../experiments/29-stalled-loads/README.md).

## Checks, builds and actual operation

| Boundary | Actual result |
| --- | --- |
| Workspace CPU tests |113 passed; zero failed, ignored or filtered |
| Format and native strict Clippy |Passed after three test-only collapsible-if repairs; initial failure retained |
| Actual Wasm target strict Clippy |Passed |
| Native release and local app package |Passed; unsigned local artifact |
| Web release |Passed; actual Wasm build |
| Existing diagnostic controls |77 tests and two collector controls passed |
| Candidate Web |One real app,12 accepted Works, four stalled transfers, latest12 recovery and full saved-Work equality; separate real Shape/Profile clicks and unchanged complete Work at1280×720/1024×768 |
| Candidate native |Actually launched; observed blank content; later explicit Mac-lock blocker; visual acceptance not passed |
| Separate baseline native experiment |Two actual launches, all-black readbacks; profile/timing only |
| Separate baseline Web experiment |Actual humanoid/timeline and exact HTTP ledger reconciliation;19 new controls passed |
| Independent pixel experiment |Compiled after retained egui API error; actual raster cases NOT-RUN |

Native executable SHA256:
`72d3df8cfdeea062282c8731b0a95cb971f90976fe881772f3e3c24afe76973a`.
Candidate Wasm SHA256:
`d890dfee73e9eeeee6ce3d82f255c79979e8c8b6bed90243c6101f8e1c1763a8`.
Root Cargo.lock remains
`457f603a78c6822b6dec754978c425ed6b61d4ed3acd0b856e606e180f5c4e73`.
Build receipts and32 input identities are in [build](build/).

The candidate Web case used one URL startup and eleven real chooser selections,
not twelve page navigations or twelve Work GETs. Before release only GLB01–04
were requested. After all four bodies were explicitly released together, GLB12
was the sole fifth request. The saved whole Work matches variant12; serialization
bytes differ. Four simultaneous releases do not prove one-slot Web recovery.
The failed initial path-edit attempt is preserved and excluded. Configured hold
was105 seconds, watchdog120; actual normal exit was85.8951 seconds. Real full
watchdog dwell and archived timeout-UI proof remain NOT-RUN.

A separate [actual tab control](ui-paint/actual-web/README.md) displays Profile
at1280×720 and Shape at1024×768, with recorded actual canvas backing/CSS dimensions
and identical downloaded full Works. One attempted slider track click produced
no observed edit; this control does not establish edit/Undo or all narrow
transport controls. It does not reopen or solve the original blocked#3 case.

Baseline Web performance uses Wasm884134fc… from045d8abc, deliberately excluding
the new policy. Its eight GETs total20,565,000 response-body bytes, including an
exact19-byte favicon404 and28-byte optional metadata404. Browser timing omits
the metadata entry and reports its own transfer sizes. Navigation, Bevy and
host clocks remain separate. Readback callbacks and main-loop cadence do not
measure physical first presentation or GPU pass time. See
[Web report](../../../experiments/30-startup-profile/WEB-REPORT.md) and
[native failure report](../../../experiments/30-startup-profile/REPORT.md).

## Reproduce current local checks

From the candidate checkout:

```sh
cargo test --workspace --locked
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo clippy -p nvwa-studio --lib --target wasm32-unknown-unknown --locked -- -D warnings
cargo build -p nvwa-studio -p nvwa-cli --release --locked
python3 scripts/package-native.py
bash scripts/build-web.sh release
python3 scripts/serve-web.py
```

The ordinary local preview uses9201. The separate controlled experiments use
9203/9204 and must follow their fixed input and cleanup instructions. Native
requires an awake, unlocked Mac. The current task retained candidate artifacts
in `/Users/derekxwang/.codex/worktrees/m11-ui-integration/nvwa/dist/`; primary
checkout work was not overwritten. Diagnostic experiments do not join root
workspace dependencies. Experiment30 historical full-byte replay also requires
its retained private baseline artifacts; it is not a fresh-checkout CI test.

## Decisions and remaining gates

Adopt permanent CPU paint checks and the finite root-request policy after
candidate acceptance. Keep independent pixel checking as an experiment; there
is no actual raster control result supporting permanent CI adoption. Preserve
native visibility failures and unavailable physical metrics rather than deriving
a shader or lock-screen cause from them. #3 remains blocked under its original
unavailable conditions. #4/#40 and the native remainder of#23 stay open.

Only task-owned renderers, tabs and servers were used, with competing heavy
tasks stopped during measurements. Their processes exited and task tabs closed;
browser viewport override reset. Worktrees, artifacts and raw receipts remain
retained for review and the unlocked follow-up. No new main merge has occurred.
