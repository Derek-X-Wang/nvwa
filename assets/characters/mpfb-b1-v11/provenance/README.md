# Per-hand size target source extension (v11)

The v11 identity and backend schema 13 avoid the separate, unmerged v10 chest-placement experiment. This hand profile derives from v9 and does not imply chest-placement inheritance.

`hand-size-target-source.json` pins four CC0 MPFB source target files at the fixed commit. Each shipped target is the byte-exact gzip expansion of its included source. `scripts/build-hand-size-v11.py` authenticates compressed SHA256 before expansion. No target amplitudes or vertex IDs are edited; the existing runtime loader scales source coordinates by 0.1 once.

Left and right controls are independent signed relative weights, not centimetres or a measured hand circumference. The preceding v9 manifest and payload list are preserved. All prior runtime payloads remain byte-identical. Hand shape, prop grip, sleeve fit, and continuous motion require separate visual acceptance.
