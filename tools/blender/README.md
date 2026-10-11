# Original M0 fixture tools

Use Blender 3.3.1 or newer. The measured toolchain is Blender 3.3.1 arm64 with
its bundled glTF exporter 3.3.32. No add-on or Python package installation is
needed. All commands run from the repository root.

```sh
/opt/homebrew/bin/blender -b -t 2 --python tools/blender/generate_fixture.py
python3 tools/blender/validate_fixture.py --publish
```

The first command replaces the original fixture `.blend`, GLB, and source
structure metadata. The second validates the actual GLB, then publishes the
contract profile, structural proof, and current hash/provenance manifest.
Never keep a profile hash from an earlier export.

Optional CPU authoring previews:

```sh
NVWA_RENDER_PREVIEWS=1 /opt/homebrew/bin/blender -b -t 2 --python tools/blender/generate_fixture.py
python3 tools/blender/validate_fixture.py --publish
```

The previews show neutral geometry, each morph at its maximum, and a raised-arm
wave pose. They are Blender source authoring stills, not Bevy/Web validation.

Two-export repeatability check:

```sh
python3 tools/blender/check_reproducibility.py
```

This launches two independent Blender processes, checks both GLBs, records their
actual hashes and structures into `experiments/01-character/reexports/run-1`
and `run-2`. It never changes the published main GLB or profile.
The observed GLB and `.blend` bytes differ between processes. See the experiment
report before making a reproducibility claim. Morph delta hashes and structural
metrics matched on the measured host. The saved fixture remains original and
regenerable, but export byte identity is unproven.

Fixture and tool license scope: `assets/fixtures/LICENSE.txt`. User repository
licensing is unchanged. The JSON profile is the contract for consumers; derive
indices from actual exported data instead of assuming action creation order.
