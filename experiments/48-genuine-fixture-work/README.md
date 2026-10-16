# 48 — One genuine sample transported into the exact fixture

This isolated experiment appends the admitted experiment44 motion sample to the unchanged Nvwa fixture under experiment47's selected engineering policy. The separate [admission](admission.json) authorizes the transformation;47's original proposal remains unchanged.

Python3.9+ and the standard library only, from repository root:

~~~sh
python3 -B experiments/48-genuine-fixture-work/export.py verify experiments/48-genuine-fixture-work/artifacts
python3 -B experiments/48-genuine-fixture-work/test_controls.py
python3 -B -O experiments/48-genuine-fixture-work/test_controls.py
~~~

The advertised verify command and normal/optimized controls pass on CPython3.9.6 and3.14.7. The ledger retains historical build-time diagnostic residuals. Live verification reports its runtime. Only three named finite float residuals may differ by at most2e-15 absolute; all other ledger values and types, nonallowlisted binary64 float representations (including zero sign), and the GLB/profile/Work bytes, remain exact. See the report for the original3.14 failure and correction.

The optional build operation accepts an exclusively new output directory whose parent exists: export.py build <new-output-directory>. It refuses existing destinations and symlinks. It uses only the exact pinned current raw44 bytes and admitted47 mapper. It does not generate new model output.

Outputs are [GLB](artifacts/assets/generated/genuine44-calibrated47.glb), [profile](artifacts/character.profile.json), [Work](artifacts/genuine44-calibrated47.nvwa.json), and [transformation ledger](artifacts/transformation-ledger.json). The asset root for this Work is artifacts/assets, and asset_path is generated/genuine44-calibrated47.glb. Keep that relationship when staging for native or Web. The Work explicitly selects genuine44_calibrated47 at animation index3.

The [primary report](REPORT.md), [primary controls](verification.json), and [CLI evidence](cli-verification.json) retain the original pre-UI checkpoint. [Independent serialized checks](independent/REPORT.md) live in a separately owned directory and are not imported by this exporter. The later [runtime report](runtime/REPORT.md) retains actual native/Web playback, edits, downloaded/saved Work files, and both exchange directions. Offline runtime-evidence checks verify the retained files; they do not rerun a renderer.

VERIFIED — Exact serialized90frame/19channel derivative, original BIN prefix and old JSON preservation,51 negative controls on both tested runtimes, and7 existing-CLI calls including save/reopen and missing/corrupt asset rejection.
VERIFIED — Later native/Web playback and bidirectional save/edit/reload, with exact whole-Work comparisons; see the separate runtime report.
HOLD — Visible arm/torso intersections; source motion, mapping and skin-weight contributions remain unattributed.
NOT-RUN — Official decoder parity, general rigs, runtime bone-value capture, certified anatomy/contact, semantic or physical-human motion quality and performance.
