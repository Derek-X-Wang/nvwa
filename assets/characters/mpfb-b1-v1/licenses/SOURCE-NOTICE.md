# Approved B1 sample source notice

Asset ID: `mpfb-hm08-game-engine-female-sportsuit01-v1`.
Manifest SHA256: `abcdbc26e03431c740c5fce98de22902089f985823a3c655db2416d042d62b18`.

The exact thirteen geometry inputs derive from MakeHuman/MPFB CC0 graphical assets: hm08 base helpers, vertex groups, game-engine rig and weights, four local torso/jaw targets, and female_sportsuit01 garment geometry. Source and encoded runtime identities are distinct and recorded in `provenance.json`. No posed mesh or reference matrix output is used to generate the candidate character.

MPFB's retained `MPFB-LICENSE.md` defines graphical assets (including meshes, targets, clothes, rigs and mesh-information JSON) as CC0 and program logic/configuration as GPL. The complete CC0-1.0 text is `CC0-1.0.txt`. The selected garment OBJ/MHCLO retain explicit CC0 notices naming Data Collection AB, Joel Palmius and Jonas Hauquier. These notices are preserved as provenance; do not infer that other addon configuration files are graphical assets from their file extension.

The runtime encodings scale OBJ positions and garment MHCLO offset/reference lengths by 0.1, preserve axes/indices/weights, decode target gzip, author an identity body map, and author empty local-target macro/composite metadata. The target loader applies its existing 0.1 scale and the admitted zero squared-delta threshold. Textures/material parity and arbitrary macro-driven generation are outside this set.

Exactly the thirteen manifest entries are runtime data. The files under this licenses directory are notices/provenance and are excluded from the runtime data allowlist. Do not add fallback geometry, reference arrays, executable addon code or automatic download behavior.
