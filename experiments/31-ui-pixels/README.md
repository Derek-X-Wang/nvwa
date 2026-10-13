# Independent raster reference for two production tabs

Question: can a literal independent reference reject a real selected-tab
paint-only regression in actual rasterized output?

Release build PASS after one retained egui0.36 panel API failure and an
experiment-only root-Ui repair. Exact frozen binary is retained. No renderer,
GPU, app, or PNG capture has run. Root held this app after both native character
runs failed actual visibility. The GPU/UI lease has returned to root; see
REPORT.md.

The proposed standalone Bevy/bevy_egui app includes the unchanged production
`crates/nvwa-studio/src/editor_layout.rs` as a module and calls its real
`EditorLayout::draw_tabs()`. The installed craft_ui revision is
`5c874d51eeb3de70e735c8ce87a59a7dedd47675`. In this revision craft_ui::Tab calls
the painter supplied by Nvwa; the selected-color closure lives in Nvwa.

Use one window and renderer, fixed1280x720 physical/scale1, Dark theme, raw egui
input time1, no pointer, no animation. Cases are Shape selected, Profile
selected, and Profile selected with active background deliberately changed to
the wrong color. The last change affects only paint. Tab state stays Profile.
The normal and mutant cases use the exact same production source bytes.

The reference checker contains literal expected colors and small interior
regions, independent of production selected state, painter observations, and
the generated screenshot. It reads actual decoded PNG RGB pixels. Missing,
empty, wrong-dimension or ambiguous outputs fail. Normal images must pass;
the mutation must fail while its logged tab state stays Profile. A missing
renderer is a failed attempt or explicit NOT-RUN, never a green skip.

Bevy screenshots provide actual raster/GPU output. A screenshot callback is
not a display timestamp. Separately inspect the PNG images and record source,
renderer/backend, artifact identity, dimensions, format, commands and errors.
This is a tiny experiment, with no full-app GPU/IME/browser/DPR acceptance and
no permanent CI adoption. Experiment28 remains CPU paint-instruction evidence.

Root grants the single Cargo writer and GPU/UI lease, exact target and artifact
paths before execution. Product files, root manifests, Cargo.lock, dependencies,
assets and older experiment archives remain unchanged.

NOT-RUN — actual raster captures, positive/negative controls and renderer
capability. Publication and independent review belong to root.
