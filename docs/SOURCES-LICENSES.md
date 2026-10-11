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

Cargo.lock identifies all transitive packages. This selected list is not a full redistribution-notice audit. The local app is unsigned and has not been publicly distributed in this round. For a public binary release, produce complete dependency notices.

Chinese text uses the embedded [Nvwa Sans SC Regular](../assets/fonts/README.md), derived from the pinned Google Fonts Noto Sans SC variable font at weight 400. No additional character subset was applied. The derivative has a new family name and keeps the original SIL Open Font License 1.1 and copyright notice. [Provenance](../assets/fonts/PROVENANCE.json) records source and derivative hashes, exact source commit, derivation tool/version and coverage limits; [experiment 06](../experiments/06-cjk-fonts/REPORT.md) records the size comparison and reproduction. The native package copies OFL/NOTICE/provenance to `Contents/Resources/licenses/fonts`; the Web bundle copies them to `licenses/fonts`. Runtime loads the font from the Rust artifact and does not fetch a font or use proprietary local system fonts. Common simplified/traditional text is covered; most supplementary Han, including 𠮷, remains unsupported. Rendering evidence does not establish IME composition support.

Optional model code, checkpoint and encoder licenses are distinct and recorded in experiments/05-ai-motion/REPORT.md. No model runtime or weights were downloaded or bundled. Controlled retarget outputs use only the original fixture. No VaM sample or third-party character was imported.
