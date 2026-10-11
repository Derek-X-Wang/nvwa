# Nvwa

Nvwa is a character creation and animation sandbox. This vocabulary describes the bounded single-character prototype.

## Language

**Work**:
A saved character creation with its appearance and selected animation settings.
_Avoid_: screenshot, video

**Character profile**:
The supported character's available appearance parameters and authored actions, together with its asset identity.
_Avoid_: arbitrary model compatibility

**Character recipe**:
The chosen appearance values for a character in a work.
_Avoid_: mesh, model file

**Morph**:
A real change to the character's surface shape, such as its jaw width or smile.
_Avoid_: color change, UI value

**Authored action**:
A skeletal motion made for the fixture, such as idle or wave.
_Avoid_: AI generation

**Generated action**:
A motion produced by an identified model with recorded generation provenance.
_Avoid_: renamed preset

**Preview**:
The temporary appearance shown during a parameter drag before the edit is committed.
_Avoid_: saved edit
