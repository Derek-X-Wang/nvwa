# Bounded existing-Web adapter review

Verdict: PASS FOR ROOT BUILD/STAGING GATE. No blocking finding. Read-only scope was the5 copied probe files, complete source diff, path resolution and5 frozen experiment identities. No compile, probe run, candidate calculation or UI action.

Independent byte comparison confirms Cargo.toml, Cargo.lock, src/main.rs and index.html are identical to old50/probe. The entire new src/lib.rs equals old50 plus exactly one insertion: `| "nvwa-experiment88-chest-local"` in the existing48/50 profile-ID allowlist. No other behavior delta exists. All old50 source hashes match the source receipt. All5 previously frozen constructor/evaluator/control/proposal/input hashes remain unchanged. Readback is web-adapter-readback.json.

Reviewed destination hashes:

- Cargo.toml `cdfb3f242456ba12b41e5b0ddf42e732263f38b000d7b36059718741f9cb7b7f`
- Cargo.lock `c9750a76f3acf9d8334b48fbbd6d1c0c5b6e806a5e880f1271a89f385ab07461`
- src/main.rs `ce58e85cbdac887b9ef0745a8be42d096d6b8328a50d6ebbbec50ec729450a0f`
- src/lib.rs `7b897249e098695866bc8a68a65000dc9822e5aefa2717ea1f09d7210f0811a4`
- index.html `043e744bf61dae564cd730c1da3372f115ba3d9f392b7e5fb6d4e57951636844`

Both probe directories have the same depth. All4 local Cargo dependency/patch paths resolve to identical existing checkout targets: crates/nvwa-studio, crates/nvwa-runtime, vendor/bevy_obj and vendor/wobj. The Studio manual-start feature, `nvwa_studio::build_app()` production graph,7 keys,30Hz times, settled-frame count,60s readiness timeout, clip/graph/skin assertions, post-animation/transform capture and final hold89 are unchanged. HTML/startup/capture export is byte exact. This identity plumbing introduces no key0 hold behavior or new verifier.

Root may build/stage this exact adapter under its existing acceptance release. Runtime compatibility and actual capture remain NOT-RUN until direct execution. Any manual key0 seek must have separate observed key/time evidence; completed seven-key capture establishes the original capture sequence and final89 hold, not a later key0 screenshot. No visual or normal/shading acceptance is implied.

VERIFIED — exact one-ID delta, unchanged copies/old50/frozen files and identical local dependency paths. NOT-RUN — compile, staging, live probe, runtime capture and appearance.
