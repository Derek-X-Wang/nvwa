# Standalone offline CLI bundle

This local source-built package contains `bin/nvwa-cli`, a complete `assets/`
root, demonstration Works in `works/`, this guide, the command guide in
`docs/cli-authoring.md`, and a `BUNDLE.json` byte inventory. It supports the
original GLB character, static B1, motion B1, and the eight-parameter character.
Both approved B1 base versions and all three appearance sets are included.
The optional short01 set uses the eight-parameter V2 base; existing Works and
creator defaults keep their original appearance selection.
No new assets, models or dependencies are acquired by packaging or use.
The packager runs the supplied native CLI against all four included Works
before writing the final directory and archive. Incomplete or changed
descriptor/payload inputs fail that check.
Use a local filesystem that supports hard links. The packager reserves the
new output directory exclusively, fills it, then creates the archive without
replacing an existing name. A late destination collision fails and preserves
the other writer's data; a failed archive publication removes this attempt's
directory. Consume the outputs after packaging succeeds. This is not a
crash-recovery transaction.

Extract the archive and keep its directories together. Set `NVWA_CLI_HOME` to
the absolute path of the extracted directory. Use absolute paths to keep the
CLI independent of your current directory:

```sh
NVWA_CLI_HOME="/absolute/path/to/nvwa-cli"
CLI="$NVWA_CLI_HOME/bin/nvwa-cli"
ASSETS="$NVWA_CLI_HOME/assets"
WORK_DIR="$(mktemp -d)"

"$CLI" validate "$NVWA_CLI_HOME/works/b1-character.nvwa.json" "$ASSETS"
"$CLI" new-character "$ASSETS" "$WORK_DIR/character.nvwa.json"
"$CLI" describe-capabilities "$WORK_DIR/character.nvwa.json"
"$CLI" inspect "$NVWA_CLI_HOME/works/b1-character.nvwa.json"
"$CLI" validate "$NVWA_CLI_HOME/works/b1-short01.nvwa.json" "$ASSETS"
```

The demonstration selects Skin, Eyes and Hair. New characters start with all
three off. Read `set_appearance.compatible_sets` for complete selectable
appearance objects, then copy one into the discovered command envelope and
`apply` to a new output Work. Each example has all three role flags on; these
flags are selectable defaults, not the loaded Work state. `current` reports
that state. The existing identity/hash fields still describe the base default
(short04); V2 additionally lists short01. V1 has one compatible set and GLB has
none. Existing executable examples remain valid. The retained command guide
describes revisions, atomic batches, errors and session history. Save Works
outside the extracted package. The binary requires the operating system and
architecture for which it was built; this is not a universal binary.

Use `assets/` as the explicit root for `new-character`, `new-b1`,
`new-b1-motion`, and B1 `validate`. For GLB creation, use
`assets/character.profile.json` with `new`. Offline use needs no repository,
Cargo, Python, Studio window, browser, GPU, account or motion weights. Builds
need the pinned Rust toolchain and locally available locked crates.

`validate` authenticates the exact pinned descriptors and every bounded
payload, including appearance roles that are off when another role is on.
The short01 descriptor pins fourteen payloads, including the original four
hair files, full 39,220-byte package metadata and CC0 text; legacy descriptors
still pin thirteen. Missing roots, missing files, changed descriptors and
corrupted payloads still reject. `apply` and `save` edit portable Work metadata; they do not
authenticate filesystem assets or establish rendered appearance readiness.
Work schema and Studio behavior are unchanged.

Studio's native `Contents/Resources/assets` and the Web export's `assets/`
are rendering resources. They do not provide this complete standalone CLI
root: their embedded appearance data does not supply filesystem payloads.
Use this package's `assets/` for CLI validation of appearance Works.

The bundle retains original CC0 license texts, source notices and provenance
beside the B1 base and appearance payloads, plus the original GLB fixture's
license and provenance. These asset notices do not license the CLI itself.
The supplied binary's hash and every packaged file's size/hash are recorded
in `BUNDLE.json` (which excludes itself). This inventory detects changes
against that receipt; it is not a signature or a replacement for the CLI's
independently pinned descriptor/payload authentication.

The root project and first-party crates do not declare a license. The copied
Cargo lockfile and manifests in `notices/build-inputs/` preserve declared
source build inputs; they do not prove the supplied binary's build origin,
enumerate linked code, or provide dependency license coverage. The existing
distribution-notice acceptance remains open. This package is for local
source-built use; it does not approve public binary redistribution or choose
a first-party license. Signing, notarization, clean-machine launch and other
operating systems require separate validation.
