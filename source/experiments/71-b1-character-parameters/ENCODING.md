# Actual array hash contract

The acceptance gate recomputes hashes from exported arrays. Supplied observer
hash strings and production appearance snapshot strings must both equal the
recomputed value. Matching strings alone did not establish this in R1.

The exact producer seam is `crates/nvwa-runtime/src/appearance/mod.rs::hash`:
`appearance_sha256(serde_json::to_vec(&Value))`. Accessory POSITION, NORMAL and
UV enter this seam as `json!(Vec<[f32; N]>)`; indices are unsigned integers.
The experiment observer hashes its actual `Value` arrays with compact
`Value::to_string()`, which uses the same serializer. Body POSITION and skin UV
also use this production seam and are checked against exported arrays.

The pinned standalone lock has serde_json 1.0.152 and zmij 1.0.23, without
`arbitrary_precision`. The inspected serde_json source constructs a floating
JSON Number from **f32 promoted to f64** (`value/ser.rs::serialize_f32`,
`number.rs::from_f32`), then serializes that f64 through zmij. This is neither
shortest f32 spelling nor Python `json.dumps` spelling.

`hash_encoding.py` accepts only finite numbers exactly representable as f32,
preserves signed zero, uses the shortest f64 decimal digits, and applies the
pinned zmij f64 notation range: fixed notation for decimal exponent -5 through
15 inclusive, `.0` for integral floats in that range, otherwise scientific
notation with a signed exponent and no exponent zero padding. Arrays use
ASCII brackets/commas without spaces. Indices must be u32 integers and retain
integer spelling. The encoder uses no production morph, fit or skin math.

Examples of the typed float encoding:

| Actual value | Hash bytes |
| --- | --- |
| `1.0` | `1.0` |
| negative zero | `-0.0` |
| `2^-16` | `0.0000152587890625` |
| `2^-17` | `7.62939453125e-6` |
| `2^54` | `1.8014398509481984e+16` |

`test_hash_encoding.py` checks these boundaries, rejects nonfinite/non-f32
values and malformed indices, and checks **all eight actual producer hashes**
for retained eye/hair POSITION, NORMAL, UV and indices. The expected digests in
`inputs/production-hash-golden.json` were copied from the production
`appearance_snapshot` in root's actual native68 R2 combined-textured capture;
the corresponding arrays were copied from the bound CPU mesh observation.
They were not generated with the Python encoder or synthetic full-schema
fixture. The fixture records the original capture SHA256, request ID and R2
source freeze. Its capture SHA256 is
`9cde54133d6b24eca8dfa155105c5c9ae7c9d2085e769d5978c22e8cfc184ef6`.
Python's default compact JSON demonstrably fails at least the retained eye
NORMAL golden. This is an executed comparison with existing production output,
not a newly executed Rust serialization test or new71 runtime evidence.

Retain the native raw frame text or the Web `acceptance-frame` textarea's raw
`.value`. Do not parse and re-stringify frames through JavaScript before
retention: that can erase negative zero. Number notation is normalized by the
verifier, but missing precision or erased signed zero cannot be recovered.

# Current identity binding and retained failure

Report/frame equality is necessary but insufficient. The gate also binds
identity Work SHA256 to the retained saved Work text; body entity to actual
base and appearance; clip, timeline, position, playing and completion to the
actual base sample; appearance serial/base asset/character to the full base;
and compact base profile/asset/backend/sample to the full base. Saved Work,
frozen case, base revision/generation/parameters and applied appearance checks
remain in force. No fields absent from the production API are invented.

`FROZEN-SOURCE-r1.json` and `PREPARATION-r1.json` preserve the original R1 state.
`VERIFIER-R1-NEGATIVE-REPRO.json` records that all four array mutations and all
four contradictory identity mutations incorrectly passed that gate. Its13
green Python tests were insufficient. The revised full-schema regressions use
fresh complete envelopes for every mutation; they keep report/frame labels
correlated and require each malformed record to fail. Synthetic fixture hashes
are only fixture construction; the separate actual producer goldens establish
the hash encoding. Rust, fixed Works, build/export code and product sources are
unchanged by this acceptance-gate repair. Actual71 native/Web69 cohorts,
ordinary UI/file exchange/live recordings and GPU/quality remain NOT-RUN by
this worker.
