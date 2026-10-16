"""Create only a task-private Blender extension lookup; no install or download."""
from pathlib import Path


root = Path(__file__).resolve().parents[3]
addon = root / ".work/character-approved-20261016/mpfb-addon"
assert addon.is_dir()
target = root / ".work/b1-pose-reference/blender-user/extensions/user_default/mpfb"
target.parent.mkdir(parents=True, exist_ok=True)
if target.is_symlink():
    assert target.resolve() == addon.resolve()
else:
    assert not target.exists()
    target.symlink_to(addon, target_is_directory=True)
print(target)
