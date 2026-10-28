# B1 admission CPU controls — experiment 72

**Bounded CPU execution PASS; see [actual results](RESULTS.md).** This is a bounded #85 compatibility and
production-mutation evidence runner. It does not change a product file. Root owns
review, build scheduling, execution, retained outputs and cleanup.

The immutable product baseline is `581f6c8329c984bf55a913ca999830430334e5a1`.
[REVIEW.md](REVIEW.md) records the contract, production seams, bounds and limits.
[cases.json](cases.json) preserves the original eight recipes and five diagnostic
poses; [pins.json](pins.json) authenticates the frozen inputs and product seams.

## Current checkout compatibility after issue86 and stage closeout

The portable Python controls now distinguish the checkout they inspect from the
immutable source they execute. [input-context-v1.json](input-context-v1.json)
admits one additional, complete source context: the reviewed issue86 runtime
retention changes. Only `b1.rs` and `appearance/mod.rs` differ from baseline581;
both must match their exact SHA-256 together. The other fifteen files in the
seventeen-file baseline set retain their original hashes. Unknown changes,
mixed baseline/current pairs, missing files and symlinks reject. The original
pins file and context manifest each retain their complete code-pinned hash.

[input-context-v2.json](input-context-v2.json) admits one more complete context:
the reviewed character-stage closeout. Its three exact overrides are the issue86
appearance controller, `b1.rs` with the added CPU-feedback test assertion, and
Core `b1.rs` with the unsupported-version diagnostic correction. The Core change
removes the misleading `expected 1` suffix; version rejection and numerical
catalogues do not change. The other fourteen baseline input hashes stay exact.
The original baseline, issue86 context and closeout context remain separate;
no mixture of their files is accepted. Both context manifests are mandatory and
code-pinned, including when authenticating the historical baseline. Missing,
symlinked, empty or altered manifests reject.

Five source sections retain byte-identical hashes across these three historical
contexts: signed target mapping, source IDs, visible-body indices, CPU upload and
the existing endpoint semantic test. `appearance/geometry.rs`, the B1 adapter,
frozen original40 inputs and numeric evaluators also retain their original
whole-file pins. Core `b1.rs` has the separately pinned closeout identity described
above. These are source identity witnesses; they do not establish current
issue86 or closeout runtime numeric results.

`--check-inputs` reports the selected checkout context separately from the
baseline. `--execute` still archives **only baseline581**, verifies that archive
in historical-only mode, and runs every original zero/original40/five-fault gate
there. Its receipt records both identities. No current file is overlaid onto
that archive. Existing execution receipts and historical pins stay unchanged.
Current production tests and mutation gates remain separate checks; current
issue86 and closeout original40 execution is **NOT-RUN** by this tooling fix.

## Explicit short01 product source context

[input-context-v3.json](input-context-v3.json) adds `hair79-short01-product-v1`
as one exact complete 17-input map. Five overrides are relative to baseline581;
four inputs differ from closeout: runtime `b1.rs`, appearance controller,
appearance geometry preparation, and Core appearance selection. The Core
version diagnostic keeps its separately pinned closeout identity. The original
pins and both older context files remain byte-for-byte unchanged. The new
context is mandatory and code-pinned with the older contexts. Source admission
still rejects every mixture, missing/extra map entry and unsafe source file.
The five protected numeric sections and all bounds/mutations remain unchanged.
The exhaustive selector control now checks 96 maps: four complete contexts
accept and the other 92 reject.

This only admits the declared current source inputs. It does not rerun current
original40 arithmetic or authenticate the new short01 asset tree. Product
asset/CLI/runtime checks provide that separate evidence. `--execute` still
archives only baseline581 and accepts only that context for historical
execution. Historical records and their source hashes remain unchanged.

## Cheap preparation controls

### PreparedRig source compatibility

[input-context-rig119-v1.json](input-context-rig119-v1.json) adds the separately
code-pinned `rig119-unit-handoff-v1` current context. It inherits the exact
short01 map, replaces only the adapter lib identity and explicitly authenticates
three supplements: the adapter README, `src/prepared.rs` and the pinned V3
production source-admission manifest. The current map has20 inputs. The original
four17-input maps and their4 accepted/92 rejected selector controls stay intact.
Missing, changed or symlinked supplements and partial/hybrid maps reject; real
copied-source controls verify the complete positive before mutation and after
restoration. Historical short01 fixtures use the separately pinned old adapter
bytes retained under experiment73; no old source is reconstructed by reversing
current edits.

The new descriptor is included in the runner's copied control package. It
does not change the archived execution source: `--execute` still archives only
baseline581 and admits only that context with `historical_only=True`. The old
archive has neither prepared/V3 marker and retains its original17-input scope.
All old pins, cases, protected numeric sections, bounds and retained execution
receipts remain unchanged. Current source compatibility does not establish fresh
historical or current Rust, render, quality or formal Work workflow acceptance.

From the repository root, without Cargo:

```sh
python3 -B -m unittest discover -s experiments/72-b1-admission-controls -p 'test_*.py'
python3 -B -O -m unittest discover -s experiments/72-b1-admission-controls -p 'test_*.py'
python3 -B experiments/72-b1-admission-controls/run.py --check-inputs
rustfmt --edition 2024 --check experiments/72-b1-admission-controls/compatibility.rs
```

The Python controls exercise exact complete-context selection (all four accept,
all 92 mixed combinations reject), historical-only selection, manifest safety,
every unchanged numeric section, patch identity, original case coverage,
exclusive outputs and fail-closed interpretation of **synthetic log fixtures**. They are
runner-tooling controls, never real Rust mutation-red evidence.

## Deferred actual CPU execution

Root schedules this potentially long job through its approved wefty procedure.
The source root must be a Git checkout containing the pinned baseline commit;
no fetch or missing-history recovery is attempted. A later control-only commit
may change checkout HEAD; the archived product is always the explicit581 commit.
Use Python 3.12 or newer (`tarfile`'s safe extraction filter is required). `cargo`
and the admitted Rust toolchain must be on the child PATH. The selected command
is intentionally workspace/lib filtered, matching the existing production-motion
mutation runner's Bevy feature union; no test is disabled or modified.

```sh
python3 -B experiments/72-b1-admission-controls/run.py \
  --execute \
  --source-root "$PWD" \
  --out "$PWD/.work/admission72-r1"
```

`--out` must be fresh, canonical and absolute. The runner never resumes or
reuses an output. A failure remains failed; inspect its logs before starting a
new named run. No automatic network, wefty invocation, shared target selection,
cache deletion or source checkout mutation is performed by this script.
`--command-timeout` defaults to 3600 seconds per subprocess and is bounded to
1..7200; a timeout terminates only that runner-created process group, preserves
its log, restores the copied production file, and fails the run.

The run creates an exclusive archive of the exact baseline commit and extracts a
full source copy under the output. Only that copy receives the cfg(test) include
and five parameter-mapping faults. Cargo uses a new output-owned target,
`--locked --offline`, jobs1 and dev/test debug0. No shared target or cache is
changed. Root should budget disk for the full baseline archive, its extraction,
and one Bevy target; there is no automatic retention/deletion policy.

Actual order:

1. Verify pinned source inputs; archive and hash the exact baseline; record full
   original file hashes; run the unchanged real signed-endpoint regression green.
2. Inject [compatibility.rs](compatibility.rs) only inside existing `b1::tests` in
   the copy. Run complete exact-zero and original40 production comparisons.
3. Apply each fault separately at the actual signed-target mapping. Require
   actual exit101, the named executed test and its intended POSITION/signed-target
   panic. Compilation failure, source-authentication failure, timeout, wrong
   test, wrong sign witness, unrelated panic and unexpected green are failures.
4. Restore the exact injected baseline and rerun the unchanged endpoint test green
   after **each** fault. Stop after the first failed gate; remaining work is NOT-RUN.
5. Remove the test include from the copied production file, rerun the pristine
   endpoint test green, and require every original archived file hash to match.

`receipt.json`, exact argv/cwd/environment overrides, merged command logs,
`faults.json`, complete original/final source hash inventories, script copies,
compact pre-assertion observations, case measurements and `export-manifest.json` remain in the output.
Original/archive source, runtime baseline, cfg(test) source and every mutant have
separate hashes. Every UV seam render row is retained: array row counts must agree,
while the unique source-ID domain is checked separately (19158 body /1797 garment).
There is no deduplication or one-render-row-per-source assumption. Raw mesh arrays stay in memory; compact records preserve hashes,
coverage and maxima. Each old/new observation is written before numeric assertions
so a failing comparison retains its actual inputs' hashes and case identity. The Rust assertions never replace actual meshes with an
expected/generated frame.

No cache reuse has been certified. The historical failed R1/R2 target paths named
in their retained failure receipts no longer existed at this preparation pass.
If root elects a cache seed, it must arrange a **new owned clone** and a separately
reviewed runner option; this runner currently always uses a fresh target.

## Evidence boundary

A successful run proves only its source-bound actual CPU comparisons and five
production semantic red/restore controls. It is neither the historical57 Blender
full-reference oracle rerun nor sampled40 CI renamed as a full gate. The original
full-source40 evidence and sampled40 CI retain their original identities. This
run binds their original recipe/pose coverage and numerical limits to a complete
baseline581 production old/new comparison. It does not supply missing actual71
cohorts, renderer/GPU pixel readback, performance, GUI, live playback or quality
clearance. #79/#80/M2 HOLD and #3/#4 limits remain unchanged.
