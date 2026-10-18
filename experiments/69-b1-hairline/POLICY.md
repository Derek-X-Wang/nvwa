# Frozen policy: short04-coverage-mips-v1

**CPU REJECTED; quality HOLD.** This is the original engineering condition,
not an artistic acceptance limit. It was not raised after the failure.
Only the alpha calculation below was executed. No filtered RGB image or
candidate render was produced.

## Input and finite alpha family

Authenticate the existing 2048×2048 RGBA8 `short04_diffuse.png` against the PNG
and decoded-byte SHA-256 values in `PROVENANCE.json`. Mip0 must remain identical.
The proposed render controls retain Mask(0.5), Sample4, source identity, Work,
body/action/time/camera, geometry, weights, UVs, normals, lighting and culling.
Those runtime invariants are **NOT-RUN** for 69 because this preflight rejected it.

Target C/N is the whole original texture's count of alpha8>=128 divided by
its texel count. It is not local hairline coverage, texture interpolation,
projected triangle coverage, MSAA sample coverage or visible rendered area.
For each generated level, sum original alpha bytes over nonoverlapping source
blocks; do not feed corrected or rounded mip bytes into subsequent levels.
Divide each sum by its source-pixel count, rounded half-up, to obtain raw alpha.

Search a single global alpha scale `128/c` for integer `c=1..255`, plus scale 0.
For nonzero scales output `min(255, floor((raw_alpha*128 + floor(c/2))/c))`;
scale 0 outputs 0. The >=128 membership is exactly raw_alpha>=c. Minimize the
integer error `abs(mip_pass_count*N - C*mip_texels)`. Ties choose the scale
closest to 1 using exact rational comparison, then the smaller c. A remaining
tie with scale 0 retains the nonzero scale. No camera, screenshot, manual alpha
threshold or visual tuning enters this search.

Reject the entire candidate if absolute global coverage error exceeds
**0.001 (0.1 percentage point)** at any generated level with width>=64
(levels 1–5 here). This is an engineering coverage condition, not artistic
acceptance. Smaller levels record their residual error but have no coverage
preservation claim. Histograms, selected scales, signed differences and exact
error fractions are retained. No tolerance/cutoff adjustment or second
candidate is permitted in this experiment.

## Unrun color design

The rejected candidate also proposed linear-light filtering of straight-alpha
sRGB bytes: decode RGB through a frozen sRGB lookup table, sum linear RGB
premultiplied by alpha, unpremultiply for output straight RGB, and carry
uncorrected source sums into later levels. Zero-alpha outputs would have RGB 0;
coverage correction would affect alpha only. This proposed handling was meant
to avoid filtering transparent black into strand color. It was **not executed
or verified**. No RGB correctness or edge-color improvement is claimed.

Unfinished Rust/app/export scaffolding and its original full policy are kept
in an ignored private archive with hashes. They are not a published runnable
experiment. The public reproduction requires only Python's standard library
and the already approved PNG; it does not require Cargo, an app or a GPU.
