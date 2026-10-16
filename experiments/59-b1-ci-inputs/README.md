# Portable original B1 CI inputs

This experiment publishes already-approved local bytes for offline extraction
on a fresh checkout. It downloads nothing, builds nothing, and starts no GPU,
Blender or model process. Python's standard library is sufficient. No private
`.work` input is needed to consume the checked-in archive.

```sh
python3 experiments/59-b1-ci-inputs/prepare_ci_inputs.py --out NEWDIR
python3 -m unittest discover -s experiments/59-b1-ci-inputs -p 'test_*.py' -v
```

The output directory must be new. Its parent must already exist and neither it
nor its ancestors may be symlinks. The extractor authenticates the pinned
manifest, archive and every member before it creates output. Existing outputs,
unsafe paths, symlinks, hardlinks, devices, duplicate/missing members, changed
content, changed permissions and noncanonical metadata are rejected. It never
calls `tar.extract` or `extractall`. Existing output sentinels survive rejection.
The CLI returns exit 2 with `CI_INPUT_REJECTED` for rejected input.

| Output beneath NEWDIR | Contents | Boundary |
| --- | --- | --- |
| `source/humentity/` | Exactly 45 original files at commit `286d33124648501535655a0de811cef55152b9fd` | Original upstream source; no lock, assets or patches |
| `crates/bevy_obj-0.19.0/` | Original approved crate archive members | Complete MIT and Apache licenses included |
| `crates/wobj-0.3.0/` | Original approved crate archive members | Complete MIT and Apache licenses included |
| `sample/` | Exactly 13 geometry-only experiment 55 derived files | Byte-identical to `data-adapter.json`; includes empty local-target metadata |
| `regression/reference.json` | Samples from all 40 actual Blender cases and all 53 bones per case | Sampled CI regression only |
| `provenance/` | Original upstream inventory, data adapter receipt and authored poses | Source, derived and reference identities |
| `licenses/Apache-2.0.txt` | Full standard Apache text from the approved dependency | Supplement to Humentity's unchanged original license notice |

The two dependency source directories are extracted unchanged from the
approved `.crate` archives, including each package's full `LICENSE-MIT` and
`LICENSE-APACHE`. Humentity's original `LICENSE` remains unchanged. Geometry
inputs and numeric reference data use approved CC0 assets. No MPFB/GPL source,
generator, `macro.json`, textures, downloaded example character or motion is
included. Humentity's 45-file source inventory includes its own shader/source
files; those remain source bytes and are not executed by extraction.

The per-file manifest records canonical path, SHA256, size, normalized `0644`
permission, license, role and provenance. Source provenance includes original
Git blob identity and pinned commit. Dependency provenance includes approved
archive SHA256 and exact original member. Derived data provenance binds the
common manifest, conversion receipt and original derived filename. Numeric
reference provenance binds the full reference manifest and every original
full-case SHA256. The archive uses sorted regular files, zero uid/gid/mtime,
empty owner/group names, no pax records, and a gzip header with zero timestamp
and no original filename.

## Frozen identities

- Archive: `approved-inputs.tar.gz`, **2,142,500 bytes**, 93 regular files.
- Archive SHA256: `4ee03913687b47f8a7379b2ba00f00a005e2129e3dd2a7f9bdda28a3c99054c5`.
- Manifest SHA256: `925688915e0ff918ba9c373c3aba39a5dbc1d4b93cabb65a3b51398fdfab3bcb`.
- Common approved manifest: `2e8566a4f12de710ead88f6aa2d71fc44e0680761a4f2fdc48a844b6f3534ab7`.
- Full experiment 56 reference: `98ffb4b7947101bdd2107055beed866d7f040b33f699fb859c090c4c03242636`.

The sampled reference contains 67 body source IDs, including diagnostic IDs
`18712`, `18989` and `7633`, and 42 garment source IDs per case. It preserves
their actual rest/posed positions, normals and complete deform weights. Every
case includes all original 53 bone records with parents, heads, tails and
rest/pose/basis/skin matrices. Coordinates use Blender Z-up metres and row-major
matrices multiplying column vectors. Sampling is fixed by `build_bundle.py`.

**This sampled CI regression is not full character acceptance.** The full
40-case comparison over all 19,158 body and 1,797 garment source vertices
retains the original experiment 56 tolerances and local arrays. Neither the
sampled reference nor its matrices may generate candidate character output.
The candidate must compute from original source/data before comparison.

Experiment 57 owns source patches, frame conversion and the full-influence
runtime bridge. This archive contains original source only. A caller prepares
its own isolated candidate from `source/humentity/` and local `crates/`; it
does not treat this extraction as a successful candidate build or execution.
The archive covers these two previously approved missing dependencies; all
other Cargo dependencies still need the normal cache or CI dependency setup.

## Rebuild and evidence

Rebuilding the archive needs the retained approved local inputs and original
full reference arrays. It does not download or regenerate them:

```sh
python3 experiments/59-b1-ci-inputs/build_bundle.py --out NEW_PACKAGE_DIRECTORY
```

Two independent packaging runs produced byte-identical archive and manifest
hashes. A clean standalone copy containing only the extractor, archive and
manifest successfully prepared every file. Eighteen portable controls exercised
the real extractor, including successful verification of all 93 output hashes
and permissions, plus real CLI archive/manifest corruption failures. Detailed
hashes and commands are recorded in `verification.json`.

**VERIFIED — Portable deterministic inputs and real offline extraction controls.**
Candidate compilation, character comparison, browser execution and GPU output
are NOT-RUN by this packaging task. No CI workflow or experiment 57/58 file changed.
