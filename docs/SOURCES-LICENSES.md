# Sources and licenses

The frozen original humanoid and authored clips are CC0-1.0, scoped by assets/fixtures/LICENSE.txt and provenance-manifest.json. Blender source/script and exports remain reproducible; byte-identical reexports are not established.

Selected exact downloaded crate metadata:

| Package | Declared license |
|---|---|
| bevy-0.19.1 | MIT OR Apache-2.0 |
| bevy_egui-0.42.0 | MIT |
| egui-0.36.2 | MIT OR Apache-2.0 |
| epaint_default_fonts-0.36.2 | (MIT OR Apache-2.0) AND OFL-1.1 AND Ubuntu-font-1.0 |
| gltf-1.4.1 | MIT OR Apache-2.0 |
| serde-1.0.228 | MIT OR Apache-2.0 |
| sha2-0.10.9 | MIT OR Apache-2.0 |
| arboard-3.6.1 | MIT OR Apache-2.0 |
| craft-ui (git rev `5c874d51eeb3de70e735c8ce87a59a7dedd47675`) | MIT OR Apache-2.0 |

Cargo.lock identifies all transitive packages. This selected list is not a full redistribution-notice audit. The local app is unsigned and has not been publicly distributed in this round. For a public binary release, produce complete dependency notices.

The private editor layout adapter uses tabs and a resize handle from [Storytold craft-libs](https://github.com/storytold/craft-libs/tree/5c874d51eeb3de70e735c8ce87a59a7dedd47675). Its source declares `MIT OR Apache-2.0`. The existing packaged MIT notice is retained in [licenses/craft-ui/LICENSE-MIT.txt](../licenses/craft-ui/LICENSE-MIT.txt) and copied to native `Contents/Resources/licenses/craft-ui` and Web `licenses/craft-ui`. [Experiment36](../experiments/36-distribution-notices/REPORT.md) separately preserves both upstream license texts, NOTICE and ATTRIBUTION at the exact revision. This corrects the source declaration; it does not select a new licensing branch or install the candidate notices into either package. Its existing egui 0.36.2 edge shares the pinned egui dependency; no other dependency version changed.

The first-party crates have no declared license and the repository has no root `LICENSE`. Their license remains **UNKNOWN** until the owner chooses one. The experiment36 pack has unresolved dependency-text, asset, generated-code and distribution scope gaps. Signing, notarization and clean-machine launch remain **NOT-RUN**; green integrity checks do not establish redistribution compliance.

The limited B1 character integration retains the admitted Humentity source and its recorded Rust patches in `vendor/humentity`, with original MIT/Apache notice and full Apache text. The approved `bevy_obj` and `wobj` source archives retain their full MIT/Apache licenses. Exactly thirteen geometry-only MakeHuman/MPFB body, rig, target and sportsuit inputs live in `assets/characters/mpfb-b1-v1`, with complete CC0 text, source notices and a hashed manifest. No MPFB program, downloaded macro configuration, textures or reference pose outputs are part of this runtime input. Native and Web packaging copy these character notices and source-library licenses. [Source admission](evidence/b1-work/SOURCE-ADMISSION.md) records the exact scope and provenance. This adds bounded source/data admission, while the existing public binary release gaps above remain open.

The optional [short01 appearance set](../assets/appearances/mpfb-b1-cc0-v2-short01-v1/SOURCE.json)
uses the already approved MakeHuman CC0 system-assets archive. It retains the
four original short01 files, full upstream metadata, selected-item attribution
and CC0 text. Its existing skin and low-poly eyes are byte-identical to the
legacy set. The [manifest](../assets/appearances/mpfb-b1-cc0-v2-short01-v1/manifest.json)
authenticates all fourteen payloads. Native/Web packaging copies its descriptor,
source notices, provenance and license; the standalone CLI package also carries
the exact filesystem payloads. These notices do not close the public binary
release gaps above.

Chinese text uses the embedded [Nvwa Sans SC Regular](../assets/fonts/README.md), derived from the pinned Google Fonts Noto Sans SC variable font at weight 400. No additional character subset was applied. The derivative has a new family name and keeps the original SIL Open Font License 1.1 and copyright notice. [Provenance](../assets/fonts/PROVENANCE.json) records source and derivative hashes, exact source commit, derivation tool/version and coverage limits; [experiment 06](../experiments/06-cjk-fonts/REPORT.md) records the size comparison and reproduction. The native package copies OFL/NOTICE/provenance to `Contents/Resources/licenses/fonts`; the Web bundle copies them to `licenses/fonts`. Runtime loads the font from the Rust artifact and does not fetch a font or use proprietary local system fonts. Common simplified/traditional text is covered; most supplementary Han, including 𠮷, remains unsupported. Rendering evidence does not establish IME composition support.

Optional model code, checkpoint and encoder licenses are distinct and recorded in experiments/05-ai-motion/REPORT.md. No model runtime or weights were downloaded or bundled. Controlled retarget outputs use only the original fixture. No VaM sample or third-party character was imported.
