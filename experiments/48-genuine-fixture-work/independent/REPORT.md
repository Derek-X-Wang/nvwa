# Independent serialized-motion oracle — experiment 48

PASS within the exact admitted raw44/source41/Nvwa18 engineering scope. This
worker authored the independent checker. This is not a formal R2 review of that
checker or of the primary exporter.

The checker reloads the actual generated GLB and compares 90 × 18 rotations,
90 root translations, 90 pelvis world positions, all mapped joint world
positions, and 3,240 signed orientation marker vectors against a separate
raw44 derivation. Maximum observed quaternion component error is
`3.3281079225844223e-8`; joint world error is `3.114200830545144e-8` metre;
signed marker error is `8.767021192346292e-9` metre. These are numeric agreement
measurements under declared engineering gauges. They are not motion quality,
anatomy, contact, official decoder or general rig acceptance.

## Independence and first freeze

Before any primary experiment48 implementation or output exposure, the worker
read only the root admission/contract, raw44 and its genuine generation receipt,
source41 metadata, original fixture/profile, and declared calibration47 policy.
No primary47 math helper, primary48 exporter or vendor module was imported.
The original quaternion oracle was built privately and frozen at
`2026-10-15T23:53:27.737981+00:00`.

- `oracle-first.py.txt`: original private source, SHA-256
  `920ec781ade83dbf6360c0547dfa0f8c3379a5335eed0b289c9c0d083f111416`.
- `first-derivation.json`: original expected-motion receipt, SHA-256
  `256c0713b3a9d62ea6acdc199a4da067a30281633f4ed566e1eb3520067149a3`.
- `first-freeze.json`: immutable exposure checkpoint and those hashes.
- `derivation-reproduction.json`: later public-code reproduction on CPython
  3.14.7. Its expected motion digest matches the original freeze produced on
  CPython3.14.7:
  `ddfc1f8dc426f82bee46dd33e33b13bca73f342033b48622cc94f9c00faf0ab4`.
- `derivation-python314.json` and `derivation-python39.json`: reproductions
  with explicit producing-runtime metadata. The CPython3.9.6 digest is
  `bb51ff8cf49d67c6d62fe08a7bdf9fc5f62bc5e02cba8dc3738fd73e483aad16`.
  The digest covers JSON-encoded binary64 intermediate expectations. It is a
  checkpoint within the named runtime, not a cross-runtime exactness claim.
  Runtime floating point differences do not change the required binary32
  output checks, exact types, or the frozen quaternion/affine tolerances.

Only after this freeze were serialized artifacts inspected. Later public-code
changes added strict structural, profile/Work and provenance checks, negative
controls and readable formatting. The CPython3.14.7 expected motion digest
remained unchanged. A later metadata correction records each producing runtime
without changing the math or transport bounds. The primary exporter was only
hashed and copied as opaque bytes for
an isolated source-pin control fixture; its implementation was not inspected or
executed by this checker.

## Independent calculation and precision

The implementation has its own binary GLB chunk decoder, bounded float accessor
reader, source/target hierarchy parsers, Hamilton XYZW quaternion multiplication,
quaternion/matrix conversions, Gram-Schmidt static frame construction, inverse
3 × 3 affine transform and recursive affine point/vector transport. It uses no
third-party modules. It does not import any experiment implementation.

Source rest positions and rotations come from source41. Target bind transforms
come directly from the original GLB, including all nonunit scales. Directed
target head/tail and guide declarations come from the pinned47 policy; computed
calibration frames, delta bases and marker offsets are not used as expected
numeric results. Static source gauge frames are independently rebuilt from the
source parent graph and declared source endpoint pairs. Target geometric
frames are rebuilt from the declared directed heads/tails. The independent
oracle collapses omitted source rotations through quaternion world products,
then uses parent-relative rest subtraction and static gauge conjugation. Pelvis
rotation stays at bind. Root17 translation subtracts the rotated exact pelvis
bind translation once from absolute raw44 Hips position.

Two signed 0.1 metre gauge marker offsets per joint are independently obtained
by inverting the full exact bind affine transform. Expected and decoded animated
hierarchies preserve every bind scale. Both primary and secondary marker vectors
are compared, including terminal joints. These are engineering diagnostics,
not measured anatomical landmarks.

Before reading generated output, the oracle fixed binary32 epsilon at `2^-24`,
quaternion component tolerance at `8 * epsilon` and rotation perturbation bound
at `32 * epsilon`. The affine bound uses at most 18 joints, total fixture bind
reach plus marker reach, and the maximum exact bind scale raised to depth18.
It evaluates to `0.0001706575400125284` metre. It is a conservative floating
point propagation bound. The much tighter local quaternion and root translation
checks also remain required. No observed output error selected these limits.
Times must equal the exact binary32 values of `i/30`, `i=0..89`; no tolerance or
extra sample is allowed.

## Serialized preservation and binding checks

Every original JSON value, scalar type and object ordering is preserved except
`buffers[0].byteLength`; only animations/accessors/bufferViews append entries.
The complete original BIN chunk, including padding, must be an exact prefix.
All three old animations remain unchanged. Clip3 has exactly 18 rotation
channels on the admitted joints and one translation channel on root17. The
checker rejects other paths, targets, duplicate channels, unsafe accessor
bounds/offsets/stride, nonfinite values, quaternion norm drift and sign breaks.

The external profile retains all old parameters/clips and adds the exact clip3
identity and binary32 last-key duration. The complete Work embeds the same
profile, binds its character, and has an explicit nonlooping clip3 timeline.
Source generation and transformation stay separate. The checker binds the
original successful generation receipt and request, raw-array hashes, original
fixture provenance, calibration/script/manifest, root admission/contract,
actual exporter hash, and all three serialized output identities. It rejects
an authored `wave` fallback and forged provenance.

This checker validates the published Python-width Work artifact. Actual Rust
CLI save/reopen document equality is a separate runtime check; Rust schema
binary32 canonicalization must be handled field by field there. The oracle's
motion tolerances are not a general JSON comparison tolerance.

## Controls and reproduction

All 32 controls mutate actual serialized artifacts or pinned source files and
invoke the real `Oracle.check_artifacts` or source-construction boundary. Every
control records its specific rejection and a restored green check. Numeric
GLB controls update profile/Work/ledger output hashes, so checksum-only rejection
cannot hide a failed numeric oracle. Controls cover root23, double root height,
side exchange, XYWZ order, sample index, old BIN and animation edits, JSON boolean
coercion, frame count, accessor bounds/alignment, an invented endpoint,
nonfinite data, quaternion sign discontinuity, source/admission/calibration/raw
identity changes, forged provenance and authored fallback.

From the repository root:

```sh
python3 experiments/48-genuine-fixture-work/independent/check_serialized.py
python3 -O experiments/48-genuine-fixture-work/independent/check_serialized.py
/usr/bin/python3 experiments/48-genuine-fixture-work/independent/check_serialized.py
/usr/bin/python3 -O experiments/48-genuine-fixture-work/independent/check_serialized.py
python3 experiments/48-genuine-fixture-work/independent/test_serialized.py
python3 -O experiments/48-genuine-fixture-work/independent/test_serialized.py
/usr/bin/python3 experiments/48-genuine-fixture-work/independent/test_serialized.py
/usr/bin/python3 -O experiments/48-genuine-fixture-work/independent/test_serialized.py
```

Normal and optimized controls pass on Python3.14.7 and Python3.9.6. Temporary
mutation fixtures are automatically removed. Frozen private derivation and
public receipts remain intentionally retained. No model, inference, dependency,
server, compile, UI, network or additional machine was used. All writes are
inside the assigned independent public/private directories.

The runtime qualification recheck uses exporter SHA-256
`5cc3d8254a0e2ec2e92c92367d7dcf3a4f9b28a7f856c0010ae1086d7a3b425f`
and transformation-ledger SHA-256
`d71e323362b750491f46f1f106a0079eefb015a0271a8460e8a9f11542febe6e`.
The derivative GLB, profile and Work bytes retain their original identities.
The independent math, strict types and binary32 bounds are unchanged.

NOT-RUN — Semantic prompt/human motion quality, official decoder parity,
certified anatomy/contact, general rigs, native/Web playback and save exchange,
product provider adoption, performance. Fresh formal independent review remains
required; this implementation worker does not self-approve that review.

VERIFIED — Serialized raw44 agreement plus 32 mutation-red/restored-green
controls on Python3.9.6 and3.14.7, normal and `-O`.
