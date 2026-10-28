# Local source limits and requirements for a later replacement review

No replacement is selected. This rejection does not prove that every mip
method is ineffective or that the asset is the sole cause of the hairline.
The rendered cause remains unknown. No geometry or source alpha was changed.

The existing short04 source consists of four CC0 files totalling 2,423,795 bytes
(see `PROVENANCE.json` for each actual byte count/hash). Its 2048² diffuse PNG
contains partial-alpha strands/cards. The original material requests alpha to
coverage, disabled backface culling and a `shaders/glsl/litsphere` shader with
`litspheres/lit_refl_sharp_aniso_hard.png`. The selected production asset set
does not include that shader/litsphere implementation. These material settings
do not establish appearance parity with the original renderer. Previous 65
native/Web images retain fine hairline jaggies with only a small coverage
improvement from alpha to coverage; they do not isolate a source-only cause.

A later source review should first enumerate only the existing approved CC0
container. Before choosing one bounded replacement, record exact archive member
names, sizes, hashes, author/license metadata, dependencies and any missing
shader/texture resources. Do not infer license from a filename. New downloads,
models, dependencies or a geometry/source-identity change need a separate
explicit decision by root/user; this experiment authorizes none.

A replacement brief must explain the hairline card/alpha detail it changes,
source topology and UVs, hm08 attachment mappings, positive normalized weights,
pose compatibility and handling of scalp intersections. Preserve the original
assets and provide a reversible selection. Confirm source alpha convention,
transparent RGB, sRGB/linear filtering and any supplied mip data. Do not replace
source detail with a guessed offset, arbitrary alpha threshold or lighting
concealment. There is no broad hair-physics/style-system scope here.

Any later render candidate requires the same held body/action/time/camera,
lighting, Sample4, cutoff and cull controls, actual bound-image metadata, and
root's direct native and Web inspection. Compare the local hairline/crown
pixels and failure cases; global texture coverage alone cannot admit quality.
Stop if the fixed source controls cannot be maintained, provenance is missing,
or the local quality improves only by hiding detail. GPU sample ownership,
performance and overall appearance quality require separate evidence.
