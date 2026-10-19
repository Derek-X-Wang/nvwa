# Complete standalone CLI asset package — issue #90

The standalone contract is a local source-built CLI package with a complete
filesystem `assets/` root. It includes the unchanged approved original GLB,
B1 base versions 1/2 and appearance versions 1/2. Studio's embedded appearance
rendering remains separate from CLI filesystem authentication. No runtime,
Work schema, descriptor pin, payload validator or Studio behavior changed.

`scripts/package-cli.py` writes a fresh directory and tar.gz archive. It copies
the binary, complete approved asset directories, three demonstration Works,
offline guides, asset license/provenance files and declared Cargo build inputs.
The supplied CLI authenticates all three staged Works before publication.
`BUNDLE.json` records relative paths, sizes and SHA-256 values for every other
file. It is an inventory, not a new authentication authority or signature.

## Local verification

Source base: `f0572e5f620da8ed31898e2d8165f7472b689837` with this packaging
change. Host: macOS arm64, Rust 1.95.0, Python 3.14.7. The CLI was built with
`--locked --offline`, two Cargo jobs and disabled debug information. The
local build and CLI tests each completed in less than five minutes.

```sh
CARGO_TARGET_DIR="$PWD/.work/issue90/target" CARGO_BUILD_JOBS=2 \
  CARGO_PROFILE_DEV_DEBUG=0 cargo build -p nvwa-cli --locked --offline
CARGO_TARGET_DIR="$PWD/.work/issue90/target" CARGO_BUILD_JOBS=2 \
  CARGO_PROFILE_DEV_DEBUG=0 CARGO_PROFILE_TEST_DEBUG=0 \
  cargo test -p nvwa-cli --locked --offline
python3 -B scripts/test-cli-package.py --binary .work/issue90/target/debug/nvwa-cli
python3 -B -O scripts/test-cli-package.py --binary .work/issue90/target/debug/nvwa-cli
python3 -B scripts/package-cli.py --binary .work/issue90/target/debug/nvwa-cli \
  --output .work/issue90/delivery-r2/nvwa-cli
```

All 24 existing CLI integration tests passed. All nine packaging tests passed
both normally and under Python optimization. The package tests extract the
actual final archive, delete the initial assembled directory, relocate the
extracted root to a path with spaces and run the packaged binary from an
unrelated temporary directory. They check:

- All three supplied Works authenticate, including version1 and version2 B1
  Works with Skin, Eyes and Hair all selected. Validation leaves them unchanged.
- Original GLB creation and all three B1 constructors work with packaged assets.
  Discovery supplies the identity/hash for an actual `set_appearance` command;
  `apply`, subsequent `inspect` and filesystem `validate` pass.
- The prior base-only distribution layout rejects with `asset_missing` at
  `appearances`. This is a filesystem-layout control, not a new Studio build.
  Omitting the root still returns `asset_root_required`; passing the package
  directory instead of its `assets/` also rejects.
- Removing a base/appearance descriptor or body/skin/eye/hair payload rejects
  with `asset_missing`. Same-length corruption rejects with
  `asset_hash_mismatch`. Identical bytes supplied through a symlink reject
  with `unsafe_asset_path`. These controls cover both B1 versions and restore
  and revalidate the original bytes after each case.
- A skin-only Work still rejects corrupted unselected hair. Packaging with
  missing or corrupted source eye bytes rejects before either final output
  is published. Existing destinations and source symlinks reject.
- The extracted inventory, approved asset bytes and retained license files
  match the package. No repository-relative path is needed at use time.
- Real separate packager processes reject four late collisions: a file or
  directory created at either final destination after preflight. Every foreign
  sentinel survives, no other final output remains, and staging is removed.

An additional retained local run invoked the actual extracted delivery binary
with an environment limited to the system `PATH`. Fourteen invocations covered
the three sample validations; missing-root, old-layout, missing-eye and
corrupt-eye red results; restored green; and actual
`new-character → describe-capabilities → apply → validate → save → inspect`.
The final saved Work matched `inspect` and selected all three roles. Raw
invocations, stdout/stderr, Works, logs and archive remain in ignored
`.work/issue90/` for review; no binary or generated asset is committed.

| Local artifact | Identity |
| --- | --- |
| `delivery-r2/nvwa-cli.tar.gz` | 17,477,666 bytes; SHA-256 `2f55f5bcaf712681cd63db59c960da74970e76cf0f57458c72b67f0adb2d31ca` |
| Extracted directory | 95 files; 31,112,976 total file bytes |
| `bin/nvwa-cli` | 1,716,864 bytes; SHA-256 `7b0f728cd64f0ac0f3d051c614114703c75e2d1dfb7f71c8ddd762409508fb4f` |
| `BUNDLE.json` | SHA-256 `e78ae16acc776f52d90329a82dbb0c8516eccdf83e3ccf780fe6f38480f211c1` |

These identities describe this local debug artifact. Release builds and other
source heads will have their own binary/archive identities. The binary is
Mach-O arm64 and refers to macOS `libiconv` and `libSystem`; another platform
requires its own native build and validation.

## Review correction and actual prior exports

The independent R2 review reproduced a publication race in the first version:
a concurrent archive file was overwritten, and an archive-directory collision
left the package directory behind despite exit 1. New real-process controls
reproduced both failures before the fix; the retained red log is
`.work/issue90/collision-controls-red.log`. The corrected packager atomically
reserves a new directory with `mkdir`, moves staged content only into that
owned namespace, then creates the archive with a no-clobber hard link. If
archive publication fails, rollback checks the reserved directory's device
and inode before removing it. Another attempt's output is preserved.
Unsupported hard-link filesystems fail safely without a rename fallback.
Receipts are computed before publication. This does not claim recovery from
process termination or power loss; consume outputs only after success.

The unchanged controls now pass normally and under `-O`, with no skipped or
disabled case. Each control observes the real child process's staging window,
stops that exact child, creates the late collision, resumes the child, then
checks exit 1, byte-identical foreign sentinels and absence of this attempt's
outputs. The original reviewed archive remains retained as
`delivery/nvwa-cli.tar.gz` with SHA-256
`847a1e7201684a73be6ea4c513ad91cfa126e4d3ba1d2fff84149b257f45bf1a`;
the final archive above adds the publication contract to its included guide.
Its binary and approved asset bytes are unchanged.
The four corrected subprocess receipts, including stdout/stderr and preserved
foreign-data checks, are in `.work/issue90/collision-controls-green.json`.

The root agent additionally invoked the exact CLI against all three retained
desktop/Web exchanged Works and actual prior R4 exports from
`b1-character-quality/.../build85-r4/`, rather than an inferred layout:

| Actual selected root | Calls | Result |
| --- | --- | --- |
| Complete extracted standalone `assets/` | 3 | All authenticate, exit 0 |
| Prior native `product-native/Nvwa.app/Contents/Resources/assets` | 3 | All reject missing `appearances`, exit 1 / `asset_missing` |
| Prior Web `product-web/assets` | 3 | All reject missing `appearances`, exit 1 / `asset_missing` |

The nine calls are retained in `.work/issue90/root-old-export-check.json`,
SHA-256 `a7c9b8f2e8c664ca8a8dcd83317130511b3d3268077d044c301bdba6daa105a9`.
This worker checked that receipt's counts, diagnostics and successful
`asset_checked` responses; the calls are root-produced evidence. This does
not infer a new Studio build or GUI run. The retained prior Web Wasm hash is
`96d858804f59c46a44d6b23bf9557d7d14522efb046ce17dcffb7fd72c8f03e0`.

## Notices and acceptance limits

The package retains the original B1 CC0 legal texts, source notices and
provenance in both base/appearance directories, including the version2 base
binding receipt. The original GLB retains its license and provenance. Fonts,
Studio renderer libraries and their notices are outside this CLI package.
No asset's legal text or attribution changed.

First-party license metadata and a root project license remain absent. The
copied lockfile/manifests identify declared source build inputs; they are not
a CLI dependency-license audit, binary build-origin proof or redistribution
approval. The existing issue #10 public-distribution/legal boundary remains.
No first-party license was chosen. Public installer publication, signing,
notarization, clean-machine execution, other operating systems and rendering
are NOT-RUN here.

The bounded CI addition is in the portable job after its existing Core/CLI
checks: build `nvwa-cli --locked --offline`, then run both Python packaging
commands against `target/debug/nvwa-cli`. This adds no crate, model or asset
download and needs no GPU or Studio build. The YAML parses locally. The parent
owns independent re-review, hosted CI, PR and final merged-head validation.

VERIFIED — Local complete archive authentication and creation/editing pass;
old-layout, missing/corrupt payloads and path violations retain their failures.
Hosted CI, release and GUI evidence remain separate.
