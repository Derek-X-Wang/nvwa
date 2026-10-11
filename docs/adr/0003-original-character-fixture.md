---
status: accepted
---

# Use an original continuous character fixture for M0

M0 needs a distributable character that can expose real skin deformation,
independent face/body morphs, and skeletal playback. Use an original scripted
Blender fixture with one continuous voxel-union primary surface, smooth bone
weights, opaque clothing, four authored morphs, and manually authored
idle/wave/turn presets. This makes the fixture's provenance and deformation
data inspectable without adding a third-party character license decision or
making optional AI motion a prerequisite.

The user authorized an original distributable test fixture. Its
[license statement](../../assets/fixtures/LICENSE.txt) applies CC0-1.0, to the
extent rights can be waived, only to this original fixture and associated
authoring/validation sources, previews, and metadata. It assigns no license to
the repository or authoring tools. No imported character, texture, mocap,
purchased asset, or AI-generated motion was used. The fixture is an engineering
input; this decision does not select a future production character provider.

The [provenance manifest](../../assets/fixtures/provenance-manifest.json)
records the original coordinates, topology, materials, displacement functions,
weights, presets, source tool version, and actual file hashes. The frozen main
GLB SHA-256 is
`f13e0189ae9a1bed17d7cf3e367e495d81ffd31b9a050b76dc1cf2e5bdff6eb6`;
the editable `.blend` SHA-256 is
`ab76175ba9c3fe64823cb3e3872a495ddd0b3abf82ccfeb31f2051a00a231b66`.
Consumers use the published profile's actual morph/animation indices and hash.
Repeat exports belong in isolated experiment directories while those inputs
are frozen for integration.

[Experiment 01](../../experiments/01-character/REPORT.md) distinguishes source
regeneration and measured structural stability from byte reproducibility.
Two independent Blender processes matched the measured structural metrics and
all four exact morph delta hashes, but GLB JSON/binary chunks and `.blend` bytes
differed. The cause remains unisolated. This is not a claim that all exported
bytes or every animation/normal value are equivalent. A future publication
must validate its actual bytes and update the profile/manifest; cross-version
and cross-platform repeatability remain untested.

Consequences: production-quality hands, combination morphs, and raised-armpit
weights still need authoring work. Structural checks and CPU source previews
do not establish native/Web rendering or M0 completion. Optional AI motion
needs separate inference/provenance evidence, and controlled basis-correction
derivatives do not establish arbitrary retargeting support.
