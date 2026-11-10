# Chest shape diagnostic candidates

This is an isolated **diagnostic experiment**, not a shipped character parameter or a change to the v10 Work format. `--diagnostic-candidate` selects only named, hash-checked byte sequences before the ordinary B1 morph, fitted body and sportsuit, static pose, and CPU frame publication. `--diagnostic-part` selects the skinned body with hidden body triangles restored, the fitted garment, or their normal visible combination. `--diagnostic-style shaded` uses flat neutral lighting and distinct part colors; it is not PBR. Ordinary `render` remains the existing combined flat silhouette path.

The first Mac comparison of exact commit `aded873bd7b1f401aae12f44ca2c0aa66a91875c` produced 108/108 candidate, pose, view and part images. Neutral diagnostic and seven retained default Work renders matched the pre-experiment outputs byte-for-byte. The visual review found that the original body already had a low anterior chest bulge, point projection made a sharp tip, and the official 55% cup target increased lower fullness. The fitted sportsuit joined the lobes into a broad front surface. These are observations, not acceptance of a final design. The archive is in the project's QA evidence collection, SHA256 `37af0700b9ad9c43816ec7c845aa355a4540e5ae4111d0f08932b78bc506b1fa`.

`firm-lift-soft`, `firm-lift-strong`, and `cup35-lift-soft` are **new, locally derived** alternatives. `generate-lift-target.py` deterministically builds two symmetric, smooth spatial corrections from the pinned B1 base OBJ. They retract the lower tip slightly, add volume to the upper half, and lift the anterior breast region. The correction is not an official MPFB target, anatomical standard, or independent public slider. It only becomes a candidate when combined with a fixed adult official source target; `source-manifest.json` fixes byte hashes and provenance. Source-body previews show a stronger upper contour, but cannot predict sportsuit fitting, seams, skinning or animation. A bounded source-mesh check of 518 front-chest quads found no flipped face normals and no face area ratio outside 0.74–1.64 for the strong case; that is not a garment or rendering verdict.

For the next Mac comparison, use an isolated checkout of this experiment's exact commit:

```sh
cargo build --locked -p nvwa-cli --features cpu-render
python3 experiments/84-chest-diagnostic/render-matrix.py \
  --cli target/debug/nvwa-cli --assets assets \
  --output /path/to/new/qa-directory \
  --candidates neutral,cup-firm-55,firm-lift-soft,firm-lift-strong,cup35-lift-soft \
  --poses neutral,shoulder
```

The script rejects an existing output directory, confirms neutral/default image and geometry parity, and saves a Work, PNG, receipt and executable hash for every body, garment and combined front/45-degree/side view. Review the garment surface and combined silhouette at a useful crop, especially the lower pole, central separation, upper transition, and raised-shoulder case. An actual lit native/GPU view and clothing-intersection inspection remain separate required evidence before anything ships. If neither candidate looks natural, revise the source shape or sportsuit asset instead of expanding a slider simply because some pixels changed.
