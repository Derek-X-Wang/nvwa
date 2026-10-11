# M1.1 Web profile experiment

Disposable experiment. No production source or dependency change. Frozen product base `11fc789e898119e0ed2b423f8a909dacb547f772`; B changes only compiler profile. See PROPOSAL.md and PROPOSED-PROFILE.toml. Preparation reads exact Git blobs at that base, so a later documentation-only commit can reproduce the same product inputs.

Run from the experiment worktree. The script derives the primary checkout from the absolute Git common directory; its existing target cache remains shared. Before a fresh preparation, root must manually preserve the verified accepted native binary as `<primary>/.work/m1-1/baseline/nvwa-studio` and accepted Web bundle as `<primary>/.work/m1-1/baseline/web/`, and supply the existing pinned wasm-bindgen under `<primary>/.tools/`. This freeze is a required external input. A rebuild cannot claim to recreate byte-identical accepted binaries. Current preparation is complete; `prepare` refuses to overwrite it. Root must apply the exact proposed profile to the generated Cargo.toml and grant a build lease. Reproduction commands on a saved experimental branch are:

```sh
task_primary_git_dir="$(git rev-parse --path-format=absolute --git-common-dir)"
task_primary_checkout="$(dirname "$task_primary_git_dir")"
python3 -B experiments/16-web-build-ab/experiment.py prepare
python3 -B experiments/16-web-build-ab/check-packaging.py
python3 -B experiments/16-web-build-ab/check-owned-process.py
# Root applies PROPOSED-PROFILE.toml's exact approved fragment to generated Cargo.toml.
python3 -B experiments/16-web-build-ab/experiment.py verify --approved-profile
# Only after root grants the compile lease:
python3 -B experiments/16-web-build-ab/experiment.py build \
  --target "$task_primary_checkout/target" \
  --lease ROOT_GRANTED_LEASE_ID --jobs 1 --timeout 2700
python3 experiments/16-web-build-ab/experiment.py package
```

The build runs in a new process group. A finally block stops only that owned group after timeout, interruption, log/memory errors or normal completion. TERM has a bounded 20-second wait, then KILL escalates; the direct child is reaped and group absence checked. Cancellation/error metadata is saved in build.json. Lightweight sleeper checks exercise this production-called helper, including a TERM-ignoring descendant. Logs and 15-second descendant RSS/system-memory snapshots stay under `.work/m11-web/evidence/`. Sum of per-process RSS can double-count shared pages; `/usr/bin/time -l` maximum RSS and vm_stat are complementary observations, not complete memory attribution. Shared root target cache is retained and never removed.

Package preserves baseline per-resource encoding. Static resources, Work, profile and licenses are identical. Only bindgen-generated JS/Wasm and declarations may differ. Existing raw and gzip static files are copied byte for byte when unchanged; every gzip pairing is verified. Manifest inventory includes shipped metadata but first-screen total counts only HTML, JS, Wasm and GLB. Profile JSON is embedded by Rust `include_str!`; separate retained profile and license files do not become measured first-screen requests. Player total adds the fixed Work separately. HTTP body audit is root-owned and must be invoked against each running loopback bundle:

```sh
python3 experiments/16-web-build-ab/experiment.py audit-http \
  --url http://127.0.0.1:ROOT_ASSIGNED_PORT \
  --bundle /absolute/path/to/served/web \
  --output .work/m11-web/evidence/ARM-http-audit.json
```

This verifies actual received Python HTTP body bytes and both hashes. Browser transfer and cadence remain separate root measurements. Server body writes do not prove browser receipt. Root keeps identical diagnostic bootstrap and excludes diagnostic bytes from product totals.

Artifacts are intentionally retained for root integration and review. Worker owns no GUI/server process; root owns worktree cleanup.

For observed browser requests, root can use the same loopback handler for each bounded navigation. No worker server is launched. Root assigns the port and owns the process. Use a fresh log per A/B repetition, with one product navigation, then stop that exact server process before switching arms:

```sh
python3 -B experiments/16-web-build-ab/serve-observed.py \
  --bundle /absolute/path/to/served/web --port ROOT_ASSIGNED_PORT \
  --arm A --log .work/m11-web/evidence/A1-browser-requests.jsonl
# Root opens the actual product in the browser and runs its assigned checks.
python3 -B experiments/16-web-build-ab/summarize-requests.py \
  --log .work/m11-web/evidence/A1-browser-requests.jsonl \
  --output .work/m11-web/evidence/A1-server-body-summary.json
```

The request logger tags audit requests by explicit `Nvwa-M1.1-Audit/1` User-Agent. Browser-candidate tags use observed browser User-Agent, so root must confirm the sole UI/browser target. The sum requires all four product resources and rejects missing, failed, repeated or incomplete product transfers. It counts server writes, not TCP/browser receipt. Separate diagnostic resource URLs are listed as excluded nonproduct requests. If root adds inline diagnostic code to product HTML, its compressed bytes cannot be exactly separated by subtraction; use a separate diagnostic resource or report that HTML-body boundary explicitly. Keep complete logs for rejected runs. Cache-Control is identically `no-store` in both arms; this does not prove cold cache.
