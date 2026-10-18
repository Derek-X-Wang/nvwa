//! Portable, validated scene documents and atomic editor transactions.
#![forbid(unsafe_code)]

mod appearance;
mod asset;
pub use appearance::*;
mod b1;
pub use b1::*;
mod stage;
pub use stage::{StageAmbient, StageCamera, StageFloor, StageLight, StageQuality, StageSettings};
#[cfg(test)]
mod bounded_history_tests;

use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet, VecDeque};

pub const SCHEMA_VERSION: u32 = 4;
pub const MAX_JSON_BYTES: usize = 2 * 1024 * 1024;

/// Session retention limits. Bytes measure compact JSON payloads, not heap usage.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
pub struct EditorRetentionLimits {
    pub history_snapshots: usize,
    pub history_bytes: usize,
    pub retry_entries: usize,
    pub retry_bytes: usize,
}

pub const EDITOR_RETENTION_LIMITS: EditorRetentionLimits = EditorRetentionLimits {
    history_snapshots: 128,
    history_bytes: 16 * 1024 * 1024,
    retry_entries: 1024,
    retry_bytes: 8 * 1024 * 1024,
};

/// Retained session payloads only; the live document and temporary candidates
/// are excluded. Save/open does not persist these counters or their contents.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
pub struct EditorRetentionStats {
    pub undo_snapshots: usize,
    pub redo_snapshots: usize,
    pub history_bytes: usize,
    pub retry_entries: usize,
    pub retry_bytes: usize,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, thiserror::Error)]
#[error("{code}: {message}")]
#[serde(deny_unknown_fields)]
pub struct CoreError {
    pub code: String,
    pub message: String,
}

impl CoreError {
    pub fn new(code: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            code: code.into(),
            message: message.into(),
        }
    }
}

type Result<T> = std::result::Result<T, CoreError>;

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct SceneDocument {
    pub schema_version: u32,
    pub revision: u64,
    pub profile: CharacterProfile,
    pub character: CharacterRecipe,
    pub timeline: Vec<TimelineClip>,
    pub stage: StageSettings,
}

impl<'de> Deserialize<'de> for SceneDocument {
    fn deserialize<D: serde::Deserializer<'de>>(
        deserializer: D,
    ) -> std::result::Result<Self, D::Error> {
        #[derive(Default)]
        struct StageField(Option<StageSettings>);
        impl<'de> Deserialize<'de> for StageField {
            fn deserialize<D: serde::Deserializer<'de>>(
                deserializer: D,
            ) -> std::result::Result<Self, D::Error> {
                StageSettings::deserialize(deserializer).map(|stage| Self(Some(stage)))
            }
        }
        #[derive(Deserialize)]
        #[serde(deny_unknown_fields)]
        struct Wire {
            schema_version: u32,
            revision: u64,
            profile: ProfileWire,
            character: RecipeWire,
            timeline: Vec<TimelineClip>,
            #[serde(default)]
            stage: StageField,
        }
        let wire = Wire::deserialize(deserializer)?;
        let legacy = match wire.schema_version {
            1 | 2 => true,
            3 | SCHEMA_VERSION => false,
            version => {
                return Err(serde::de::Error::custom(format!(
                    "unsupported_schema_version: schema version {version} is unsupported"
                )));
            }
        };
        let stage = match (wire.schema_version, wire.stage.0) {
            (1, None) => StageSettings::default(),
            (1, Some(_)) => return Err(serde::de::Error::custom("schema 1 does not allow stage")),
            (_, None) => return Err(serde::de::Error::missing_field("stage")),
            (_, Some(stage)) => stage,
        };
        let profile = wire
            .profile
            .into_profile(legacy)
            .map_err(serde::de::Error::custom)?;
        let character = wire
            .character
            .into_recipe(legacy, wire.schema_version < 4)
            .map_err(serde::de::Error::custom)?;
        Ok(Self {
            schema_version: SCHEMA_VERSION,
            revision: wire.revision,
            profile,
            character,
            timeline: wire.timeline,
            stage,
        })
    }
}

// Presence wrappers preserve strict legacy/current shapes, including explicit null.
#[derive(Default)]
struct BackendField(Option<CharacterBackend>);
impl<'de> Deserialize<'de> for BackendField {
    fn deserialize<D: serde::Deserializer<'de>>(
        deserializer: D,
    ) -> std::result::Result<Self, D::Error> {
        CharacterBackend::deserialize(deserializer).map(|backend| Self(Some(backend)))
    }
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ProfileWire {
    id: String,
    asset_path: String,
    asset_sha256: String,
    license: String,
    parameters: Vec<ParameterSpec>,
    clips: Vec<ClipSpec>,
    #[serde(default)]
    backend: BackendField,
}
impl ProfileWire {
    fn into_profile(self, legacy: bool) -> std::result::Result<CharacterProfile, String> {
        let backend = match (legacy, self.backend.0) {
            (true, None) => CharacterBackend::Glb { schema_version: 1 },
            (true, Some(_)) => return Err("legacy schema does not allow backend".into()),
            (false, None) => return Err("missing field `backend`".into()),
            (false, Some(backend)) => backend,
        };
        Ok(CharacterProfile {
            id: self.id,
            asset_path: self.asset_path,
            asset_sha256: self.asset_sha256,
            license: self.license,
            parameters: self.parameters,
            clips: self.clips,
            backend,
        })
    }
}
#[derive(Default)]
struct PoseField(Option<Option<String>>);
impl<'de> Deserialize<'de> for PoseField {
    fn deserialize<D: serde::Deserializer<'de>>(
        deserializer: D,
    ) -> std::result::Result<Self, D::Error> {
        Option::<String>::deserialize(deserializer).map(|pose| Self(Some(pose)))
    }
}
#[derive(Default)]
struct AppearanceField(Option<CharacterAppearance>);
impl<'de> Deserialize<'de> for AppearanceField {
    fn deserialize<D: serde::Deserializer<'de>>(
        deserializer: D,
    ) -> std::result::Result<Self, D::Error> {
        CharacterAppearance::deserialize(deserializer).map(|appearance| Self(Some(appearance)))
    }
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RecipeWire {
    id: String,
    profile_id: String,
    parameters: BTreeMap<String, f32>,
    scale: f32,
    #[serde(default)]
    diagnostic_pose: PoseField,
    #[serde(default)]
    appearance: AppearanceField,
}
impl RecipeWire {
    fn into_recipe(
        self,
        legacy: bool,
        legacy_appearance: bool,
    ) -> std::result::Result<CharacterRecipe, String> {
        let appearance = match (legacy_appearance, self.appearance.0) {
            (true, None) => CharacterAppearance::None,
            (true, Some(_)) => return Err("legacy schema does not allow appearance".into()),
            (false, None) => return Err("missing field `appearance`".into()),
            (false, Some(appearance)) => appearance,
        };
        let diagnostic_pose = match (legacy, self.diagnostic_pose.0) {
            (true, None) => None,
            (true, Some(_)) => return Err("legacy schema does not allow diagnostic_pose".into()),
            (false, None) => return Err("missing field `diagnostic_pose`".into()),
            (false, Some(pose)) => pose,
        };
        Ok(CharacterRecipe {
            id: self.id,
            profile_id: self.profile_id,
            parameters: self.parameters,
            scale: self.scale,
            diagnostic_pose,
            appearance,
        })
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CharacterProfile {
    pub backend: CharacterBackend,
    pub id: String,
    pub asset_path: String,
    pub asset_sha256: String,
    pub license: String,
    pub parameters: Vec<ParameterSpec>,
    pub clips: Vec<ClipSpec>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ParameterSpec {
    pub id: String,
    /// GLB morph index. On B1 this is canonical inert compatibility metadata, never a mesh index.
    pub morph_index: usize,
    pub min: f32,
    pub max: f32,
    pub default: f32,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ClipSpec {
    pub id: String,
    pub animation_index: usize,
    pub duration_seconds: f32,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct CharacterRecipe {
    pub id: String,
    pub profile_id: String,
    pub parameters: BTreeMap<String, f32>,
    pub scale: f32,
    pub diagnostic_pose: Option<String>,
    pub appearance: CharacterAppearance,
}

impl<'de> Deserialize<'de> for CharacterRecipe {
    fn deserialize<D: serde::Deserializer<'de>>(
        deserializer: D,
    ) -> std::result::Result<Self, D::Error> {
        RecipeWire::deserialize(deserializer)?
            .into_recipe(false, false)
            .map_err(serde::de::Error::custom)
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TimelineClip {
    pub id: String,
    pub clip_id: String,
    pub start_seconds: f32,
    /// Wall-time span. Source pose time advances by `speed` within this span.
    pub duration_seconds: f32,
    pub speed: f32,
    pub looping: bool,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CommandEnvelope {
    pub command_id: String,
    pub expected_revision: u64,
    pub command: Command,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
pub enum Command {
    SetParameters {
        character_id: String,
        values: BTreeMap<String, f32>,
    },
    SetScale {
        character_id: String,
        scale: f32,
    },
    SetDiagnosticPose {
        character_id: String,
        pose_id: String,
    },
    SetAppearance {
        character_id: String,
        appearance: CharacterAppearance,
    },
    SetTimeline {
        clips: Vec<TimelineClip>,
    },
    SetStage {
        stage: StageSettings,
    },
    Undo,
    Redo,
}

// Serde internally tagged unit variants otherwise accept arbitrary extra fields.
// Empty struct variants in this private decoding shape enforce strictness while
// retaining the ergonomic public Command::Undo / Command::Redo API.
impl<'de> Deserialize<'de> for Command {
    fn deserialize<D: serde::Deserializer<'de>>(
        deserializer: D,
    ) -> std::result::Result<Self, D::Error> {
        #[derive(Deserialize)]
        #[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
        enum StrictCommand {
            SetParameters {
                character_id: String,
                values: BTreeMap<String, f32>,
            },
            SetScale {
                character_id: String,
                scale: f32,
            },
            SetDiagnosticPose {
                character_id: String,
                pose_id: String,
            },
            SetAppearance {
                character_id: String,
                appearance: CharacterAppearance,
            },
            SetTimeline {
                clips: Vec<TimelineClip>,
            },
            SetStage {
                stage: StageSettings,
            },
            Undo {},
            Redo {},
        }
        Ok(match StrictCommand::deserialize(deserializer)? {
            StrictCommand::SetParameters {
                character_id,
                values,
            } => Self::SetParameters {
                character_id,
                values,
            },
            StrictCommand::SetScale {
                character_id,
                scale,
            } => Self::SetScale {
                character_id,
                scale,
            },
            StrictCommand::SetDiagnosticPose {
                character_id,
                pose_id,
            } => Self::SetDiagnosticPose {
                character_id,
                pose_id,
            },
            StrictCommand::SetAppearance {
                character_id,
                appearance,
            } => Self::SetAppearance {
                character_id,
                appearance,
            },
            StrictCommand::SetTimeline { clips } => Self::SetTimeline { clips },
            StrictCommand::SetStage { stage } => Self::SetStage { stage },
            StrictCommand::Undo {} => Self::Undo,
            StrictCommand::Redo {} => Self::Redo,
        })
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CommandResult {
    pub revision: u64,
    pub summary: String,
    pub duplicate: bool,
}

fn id(value: &str, label: &str) -> Result<()> {
    if value.trim().is_empty() {
        return Err(CoreError::new(
            "invalid_id",
            format!("{label} must not be empty"),
        ));
    }
    Ok(())
}

fn finite(value: f32, label: &str) -> Result<()> {
    if !value.is_finite() {
        return Err(CoreError::new(
            "nonfinite_value",
            format!("{label} must be finite"),
        ));
    }
    Ok(())
}

fn positive(value: f32, label: &str) -> Result<()> {
    finite(value, label)?;
    if value <= 0.0 {
        return Err(CoreError::new(
            "out_of_range",
            format!("{label} must be greater than zero"),
        ));
    }
    Ok(())
}

fn unique<'a>(values: impl Iterator<Item = &'a str>, label: &str) -> Result<()> {
    let mut seen = BTreeSet::new();
    for value in values {
        id(value, label)?;
        if !seen.insert(value) {
            return Err(CoreError::new(
                "duplicate_id",
                format!("duplicate {label}: {value}"),
            ));
        }
    }
    Ok(())
}

fn parse_json<T: for<'de> Deserialize<'de>>(input: &str) -> Result<T> {
    if input.len() > MAX_JSON_BYTES {
        return Err(CoreError::new(
            "input_too_large",
            "JSON exceeds the 2 MiB limit",
        ));
    }
    // Reject duplicate object keys before typed decoding (maps otherwise overwrite).
    serde_json::from_str::<UniqueJson>(input)
        .map_err(|error| CoreError::new("invalid_json", error.to_string()))?;
    serde_json::from_str(input).map_err(|error| {
        let message = error.to_string();
        let code = [
            "unsupported_character_backend",
            "unsupported_schema_version",
            "unsupported_appearance_version",
            "unsupported_appearance_asset",
            "invalid_appearance",
        ]
        .into_iter()
        .find(|code| message.starts_with(&format!("{code}:")))
        .unwrap_or("invalid_json");
        CoreError::new(code, message)
    })
}

fn serialize_json<T: Serialize>(value: &T) -> Result<String> {
    let output = serde_json::to_string_pretty(value)
        .map_err(|error| CoreError::new("invalid_json", error.to_string()))?;
    if output.len() > MAX_JSON_BYTES {
        return Err(CoreError::new(
            "input_too_large",
            "JSON exceeds the 2 MiB limit",
        ));
    }
    Ok(output)
}

impl CharacterProfile {
    pub fn validate(&self) -> Result<()> {
        self.backend.validate()?;
        if self.backend.is_b1() {
            return self.validate_b1();
        }
        id(&self.id, "profile id")?;
        if self.asset_path.is_empty()
            || self
                .asset_path
                .chars()
                .any(|c| c.is_control() || matches!(c, '\\' | ':' | '?' | '#' | '%'))
            || self
                .asset_path
                .split('/')
                .any(|part| part.is_empty() || part == "." || part == "..")
        {
            return Err(CoreError::new(
                "unsafe_asset_path",
                "asset_path must be a safe relative path using forward slashes",
            ));
        }
        if self.asset_sha256.len() != 64
            || !self.asset_sha256.bytes().all(|c| c.is_ascii_hexdigit())
        {
            return Err(CoreError::new(
                "invalid_asset_hash",
                "asset_sha256 must contain 64 hexadecimal digits",
            ));
        }
        if self.license.trim().is_empty() {
            return Err(CoreError::new(
                "invalid_license",
                "asset license must not be empty",
            ));
        }
        unique(
            self.parameters.iter().map(|p| p.id.as_str()),
            "parameter id",
        )?;
        unique(self.clips.iter().map(|c| c.id.as_str()), "clip id")?;
        let mut indices = BTreeSet::new();
        for parameter in &self.parameters {
            finite(parameter.min, "parameter minimum")?;
            finite(parameter.max, "parameter maximum")?;
            finite(parameter.default, "parameter default")?;
            if parameter.min > parameter.max
                || parameter.default < parameter.min
                || parameter.default > parameter.max
            {
                return Err(CoreError::new(
                    "out_of_range",
                    format!("invalid bounds/default for parameter {}", parameter.id),
                ));
            }
            if !indices.insert(parameter.morph_index) {
                return Err(CoreError::new(
                    "duplicate_morph_index",
                    format!(
                        "morph index {} is mapped more than once",
                        parameter.morph_index
                    ),
                ));
            }
        }
        for clip in &self.clips {
            positive(clip.duration_seconds, "clip duration")?;
        }
        Ok(())
    }

    pub fn from_json(input: &str) -> Result<Self> {
        let wire: ProfileWire = parse_json(input)?;
        let legacy = wire.backend.0.is_none();
        let profile = wire
            .into_profile(legacy)
            .map_err(|message| CoreError::new("invalid_json", message))?;
        profile.validate()?;
        Ok(profile)
    }

    pub fn to_json(&self) -> Result<String> {
        self.validate()?;
        serialize_json(self)
    }
}

impl SceneDocument {
    pub fn from_profile(profile: CharacterProfile) -> Result<Self> {
        profile.validate()?;
        let parameters = profile
            .parameters
            .iter()
            .map(|p| (p.id.clone(), p.default))
            .collect();
        let mut timeline = profile
            .clips
            .iter()
            .find(|c| c.id == "idle")
            .map(|clip| {
                vec![TimelineClip {
                    id: "timeline-1".into(),
                    clip_id: clip.id.clone(),
                    start_seconds: 0.0,
                    duration_seconds: clip.duration_seconds,
                    speed: 1.0,
                    looping: true,
                }]
            })
            .unwrap_or_default();
        if profile.backend.is_b1_motion() {
            let clip = &profile.clips[0];
            timeline = vec![TimelineClip {
                id: "timeline-1".into(),
                clip_id: clip.id.clone(),
                start_seconds: 0.0,
                duration_seconds: clip.duration_seconds,
                speed: 1.0,
                looping: true,
            }];
        }
        let document = Self {
            schema_version: SCHEMA_VERSION,
            revision: 0,
            character: CharacterRecipe {
                id: "character-1".into(),
                profile_id: profile.id.clone(),
                parameters,
                scale: 1.0,
                diagnostic_pose: profile.backend.is_b1().then(|| "neutral".into()),
                appearance: CharacterAppearance::None,
            },
            profile,
            timeline,
            stage: StageSettings::default(),
        };
        document.validate()?;
        Ok(document)
    }

    pub fn validate(&self) -> Result<()> {
        if self.schema_version != SCHEMA_VERSION {
            return Err(CoreError::new(
                "unsupported_schema_version",
                format!(
                    "schema version {} is unsupported; expected {SCHEMA_VERSION}",
                    self.schema_version
                ),
            ));
        }
        self.stage.validate()?;
        self.profile.validate()?;
        self.character
            .appearance
            .validate_for(&self.profile.backend)?;
        id(&self.character.id, "character id")?;
        if self.character.profile_id != self.profile.id {
            return Err(CoreError::new(
                "invalid_reference",
                "character references an unknown profile",
            ));
        }
        positive(self.character.scale, "character scale")?;
        match (
            &self.profile.backend,
            self.character.diagnostic_pose.as_deref(),
        ) {
            (CharacterBackend::Glb { .. }, None) => {}
            (CharacterBackend::Glb { .. }, Some(_)) => {
                return Err(CoreError::new(
                    "unsupported_character_operation",
                    "GLB characters do not support diagnostic poses",
                ));
            }
            (CharacterBackend::B1Cpu { .. }, Some(pose)) => validate_b1_pose(pose)?,
            (CharacterBackend::B1Cpu { .. }, None) => {
                return Err(CoreError::new(
                    "unsupported_pose",
                    "B1 requires a diagnostic pose",
                ));
            }
        }
        if !self.profile.backend.supports_timeline() && !self.timeline.is_empty() {
            return Err(CoreError::new(
                "unsupported_character_operation",
                "B1 diagnostic characters do not support animation timelines",
            ));
        }
        for (parameter_id, value) in &self.character.parameters {
            self.validate_parameter(parameter_id, *value)?;
        }
        for parameter in &self.profile.parameters {
            if !self.character.parameters.contains_key(&parameter.id) {
                return Err(CoreError::new(
                    "missing_parameter",
                    format!("character is missing parameter {}", parameter.id),
                ));
            }
        }
        unique(self.timeline.iter().map(|c| c.id.as_str()), "timeline id")?;
        for clip in &self.timeline {
            if !self
                .profile
                .clips
                .iter()
                .any(|spec| spec.id == clip.clip_id)
            {
                return Err(CoreError::new(
                    "invalid_reference",
                    format!("unknown animation clip {}", clip.clip_id),
                ));
            }
            finite(clip.start_seconds, "timeline start")?;
            if clip.start_seconds < 0.0 {
                return Err(CoreError::new(
                    "out_of_range",
                    "timeline start must not be negative",
                ));
            }
            positive(clip.duration_seconds, "timeline duration")?;
            positive(clip.speed, "timeline speed")?;
            finite(clip.start_seconds + clip.duration_seconds, "timeline end")?;
            finite(
                clip.duration_seconds * clip.speed,
                "timeline playback duration",
            )?;
        }
        // A bounded sequence has one action at a time. Array order is storage
        // order; start times define playback order. Gaps are valid holds.
        let mut ordered: Vec<_> = self.timeline.iter().collect();
        ordered.sort_by(|a, b| a.start_seconds.total_cmp(&b.start_seconds));
        for pair in ordered.windows(2) {
            if pair[1].start_seconds < pair[0].start_seconds + pair[0].duration_seconds {
                return Err(CoreError::new(
                    "overlapping_timeline",
                    format!("timeline entries {} and {} overlap", pair[0].id, pair[1].id),
                ));
            }
        }
        Ok(())
    }

    /// End of the final wall-time span; gaps count toward this duration.
    pub fn timeline_duration_seconds(&self) -> f32 {
        self.timeline
            .iter()
            .map(|clip| clip.start_seconds + clip.duration_seconds)
            .fold(0.0, f32::max)
    }

    /// Preserve the M0 start-zero single-action loop as an indefinite preview.
    pub fn is_single_loop(&self) -> bool {
        self.timeline.len() == 1
            && self.timeline[0].start_seconds == 0.0
            && self.timeline[0].looping
    }

    fn validate_parameter(&self, parameter_id: &str, value: f32) -> Result<()> {
        let spec = self
            .profile
            .parameters
            .iter()
            .find(|p| p.id == parameter_id)
            .ok_or_else(|| {
                CoreError::new(
                    "invalid_reference",
                    format!("unknown parameter {parameter_id}"),
                )
            })?;
        finite(value, parameter_id)?;
        if value < spec.min || value > spec.max {
            return Err(CoreError::new(
                "out_of_range",
                format!(
                    "parameter {parameter_id} must be between {} and {}",
                    spec.min, spec.max
                ),
            ));
        }
        Ok(())
    }

    pub fn from_json(input: &str) -> Result<Self> {
        let document: Self = parse_json(input)?;
        document.validate()?;
        Ok(document)
    }

    pub fn to_json(&self) -> Result<String> {
        self.validate()?;
        serialize_json(self)
    }
}

impl CommandEnvelope {
    pub fn from_json(input: &str) -> Result<Self> {
        let envelope: Self = parse_json(input)?;
        id(&envelope.command_id, "command id")?;
        Ok(envelope)
    }

    /// Parse a complete command batch with the same byte limit and strict
    /// duplicate-key rejection as a single envelope. Every ID is checked before
    /// any envelope is returned; this method does not apply the commands.
    pub fn batch_from_json(input: &str) -> Result<Vec<Self>> {
        let envelopes: Vec<Self> = parse_json(input)?;
        for envelope in &envelopes {
            id(&envelope.command_id, "command id")?;
        }
        Ok(envelopes)
    }

    pub fn to_json(&self) -> Result<String> {
        id(&self.command_id, "command id")?;
        // Serde serializes nonfinite floats as null. Check before serializing.
        match &self.command {
            Command::SetParameters { values, .. } => {
                for (key, value) in values {
                    finite(*value, key)?;
                }
            }
            Command::SetScale { scale, .. } => finite(*scale, "scale")?,
            Command::SetAppearance { appearance, .. } => appearance.validate()?,
            Command::SetStage { stage } => stage.validate()?,
            Command::SetTimeline { clips } => {
                for clip in clips {
                    finite(clip.start_seconds, "start")?;
                    finite(clip.duration_seconds, "duration")?;
                    finite(clip.speed, "speed")?;
                }
            }
            Command::SetDiagnosticPose { .. } | Command::Undo | Command::Redo => {}
        }
        serialize_json(self)
    }
}

/// An in-memory editing session with [`EDITOR_RETENTION_LIMITS`] FIFO retention.
/// Snapshot eviction removes farthest reachable states. An adjacent snapshot
/// larger than the byte budget clears that direction's history (a barrier),
/// without rejecting the edit. Retry reads do not refresh retention. An expired
/// original envelope gets `revision_conflict`; its ID can be used again with a
/// fresh valid envelope. Oversized retry entries expire immediately.
/// Save/open persists scene content; it does not persist session history.
#[derive(Clone, Debug)]
pub struct Editor {
    document: SceneDocument,
    undo: VecDeque<Snapshot>,
    redo: VecDeque<Snapshot>,
    history_bytes: usize,
    committed: VecDeque<RetryEntry>,
    retry_bytes: usize,
}

#[derive(Clone, Debug)]
struct Snapshot {
    document: SceneDocument,
    bytes: usize,
    inserted_revision: u64,
}

#[derive(Clone, Debug)]
struct RetryEntry {
    envelope: CommandEnvelope,
    result: CommandResult,
    bytes: usize,
}

// Count serialized bytes without allocating another copy of a large payload.
fn compact_json_bytes(value: &impl Serialize) -> Result<usize> {
    #[derive(Default)]
    struct Counter(usize);
    impl std::io::Write for Counter {
        fn write(&mut self, bytes: &[u8]) -> std::io::Result<usize> {
            self.0 = self
                .0
                .checked_add(bytes.len())
                .ok_or_else(|| std::io::Error::other("serialized byte count overflow"))?;
            Ok(bytes.len())
        }
        fn flush(&mut self) -> std::io::Result<()> {
            Ok(())
        }
    }
    let mut counter = Counter::default();
    serde_json::to_writer(&mut counter, value)
        .map_err(|error| CoreError::new("invalid_json", error.to_string()))?;
    Ok(counter.0)
}

impl Editor {
    pub fn new(document: SceneDocument) -> Result<Self> {
        document.validate()?;
        Ok(Self {
            document,
            undo: VecDeque::new(),
            redo: VecDeque::new(),
            history_bytes: 0,
            committed: VecDeque::new(),
            retry_bytes: 0,
        })
    }

    pub fn document(&self) -> &SceneDocument {
        &self.document
    }

    pub fn retention_stats(&self) -> EditorRetentionStats {
        EditorRetentionStats {
            undo_snapshots: self.undo.len(),
            redo_snapshots: self.redo.len(),
            history_bytes: self.history_bytes,
            retry_entries: self.committed.len(),
            retry_bytes: self.retry_bytes,
        }
    }

    /// Validate temporary slider values without advancing revision or history.
    pub fn preview(&self, command: &Command) -> Result<SceneDocument> {
        let mut candidate = self.document.clone();
        apply_edit(&mut candidate, command)?;
        candidate.validate()?;
        Ok(candidate)
    }

    pub fn apply(&mut self, envelope: CommandEnvelope) -> Result<CommandResult> {
        id(&envelope.command_id, "command id")?;
        if let Some(previous) = self
            .committed
            .iter()
            .find(|entry| entry.envelope.command_id == envelope.command_id)
        {
            if previous.envelope != envelope {
                return Err(CoreError::new(
                    "command_id_conflict",
                    "command ID was already committed with a different payload",
                ));
            }
            let mut duplicate = previous.result.clone();
            duplicate.duplicate = true;
            return Ok(duplicate);
        }
        if envelope.expected_revision != self.document.revision {
            return Err(CoreError::new(
                "revision_conflict",
                format!(
                    "expected revision {}, current revision is {}",
                    envelope.expected_revision, self.document.revision
                ),
            ));
        }
        let revision = self.document.revision.checked_add(1).ok_or_else(|| {
            CoreError::new(
                "revision_overflow",
                "revision cannot advance beyond u64::MAX",
            )
        })?;
        let (mut candidate, summary) = match &envelope.command {
            Command::Undo => (
                self.undo
                    .back()
                    .map(|snapshot| snapshot.document.clone())
                    .ok_or_else(|| CoreError::new("nothing_to_undo", "no edit to undo"))?,
                "Undo".to_string(),
            ),
            Command::Redo => (
                self.redo
                    .back()
                    .map(|snapshot| snapshot.document.clone())
                    .ok_or_else(|| CoreError::new("nothing_to_redo", "no edit to redo"))?,
                "Redo".to_string(),
            ),
            command => (self.preview(command)?, command_summary(command)),
        };
        candidate.revision = revision;
        candidate.validate()?;
        let snapshot_bytes = compact_json_bytes(&self.document)?;
        let result = CommandResult {
            revision,
            summary,
            duplicate: false,
        };
        let retry_bytes = compact_json_bytes(&(&envelope, &result))?;
        // All fallible work is complete. Commit state and journal together.
        match &envelope.command {
            Command::Undo => {
                self.history_bytes -= self.undo.pop_back().unwrap().bytes;
                self.retain_snapshot(true, snapshot_bytes, revision);
            }
            Command::Redo => {
                self.history_bytes -= self.redo.pop_back().unwrap().bytes;
                self.retain_snapshot(false, snapshot_bytes, revision);
            }
            _ => {
                self.history_bytes -= self
                    .redo
                    .iter()
                    .map(|snapshot| snapshot.bytes)
                    .sum::<usize>();
                self.redo.clear();
                self.retain_snapshot(false, snapshot_bytes, revision);
            }
        }
        self.document = candidate;
        if retry_bytes <= EDITOR_RETENTION_LIMITS.retry_bytes {
            while self.committed.len() >= EDITOR_RETENTION_LIMITS.retry_entries
                || self.retry_bytes > EDITOR_RETENTION_LIMITS.retry_bytes - retry_bytes
            {
                self.retry_bytes -= self.committed.pop_front().unwrap().bytes;
            }
            self.retry_bytes += retry_bytes;
            self.committed.push_back(RetryEntry {
                envelope,
                result: result.clone(),
                bytes: retry_bytes,
            });
        } else {
            // FIFO reaches the oversized newest entry only after every older
            // entry expires. The edit still succeeds without retry retention.
            self.committed.clear();
            self.retry_bytes = 0;
        }
        Ok(result)
    }

    fn retain_snapshot(&mut self, to_redo: bool, bytes: usize, revision: u64) {
        if bytes > EDITOR_RETENTION_LIMITS.history_bytes {
            // Keeping older states behind this absent adjacent state would
            // make undo/redo jump across an edit, so clear the whole direction.
            let stack = if to_redo {
                &mut self.redo
            } else {
                &mut self.undo
            };
            self.history_bytes -= stack.iter().map(|snapshot| snapshot.bytes).sum::<usize>();
            stack.clear();
            return;
        }
        while self.undo.len() + self.redo.len() >= EDITOR_RETENTION_LIMITS.history_snapshots
            || self.history_bytes > EDITOR_RETENTION_LIMITS.history_bytes - bytes
        {
            // Each stack is ordered by insertion. Its front is also its
            // farthest reachable state, so FIFO eviction preserves adjacency.
            let from_undo = match (self.undo.front(), self.redo.front()) {
                (Some(undo), Some(redo)) => undo.inserted_revision < redo.inserted_revision,
                (Some(_), None) => true,
                (None, Some(_)) => false,
                (None, None) => unreachable!("nonempty history exceeds retention"),
            };
            let oldest = if from_undo {
                self.undo.pop_front()
            } else {
                self.redo.pop_front()
            };
            self.history_bytes -= oldest.unwrap().bytes;
        }
        let snapshot = Snapshot {
            document: self.document.clone(),
            bytes,
            inserted_revision: revision,
        };
        self.history_bytes += bytes;
        if to_redo {
            self.redo.push_back(snapshot);
        } else {
            self.undo.push_back(snapshot);
        }
    }
}

fn apply_edit(document: &mut SceneDocument, command: &Command) -> Result<()> {
    match command {
        Command::SetParameters {
            character_id,
            values,
        } => {
            check_character(document, character_id)?;
            for (parameter_id, value) in values {
                document.validate_parameter(parameter_id, *value)?;
            }
            document.character.parameters.extend(values.clone());
        }
        Command::SetScale {
            character_id,
            scale,
        } => {
            check_character(document, character_id)?;
            positive(*scale, "character scale")?;
            document.character.scale = *scale;
        }
        Command::SetDiagnosticPose {
            character_id,
            pose_id,
        } => {
            check_character(document, character_id)?;
            if !document.profile.backend.is_b1() {
                return Err(CoreError::new(
                    "unsupported_character_operation",
                    "GLB characters do not support diagnostic poses",
                ));
            }
            validate_b1_pose(pose_id)?;
            document.character.diagnostic_pose = Some(pose_id.clone());
            if document.profile.backend.is_b1_motion() {
                document.timeline.clear();
            }
        }
        Command::SetAppearance {
            character_id,
            appearance,
        } => {
            check_character(document, character_id)?;
            appearance.validate_for(&document.profile.backend)?;
            document.character.appearance = appearance.clone();
        }
        Command::SetTimeline { clips } => document.timeline = clips.clone(),
        Command::SetStage { stage } => {
            stage.validate()?;
            document.stage = stage.clone();
        }
        Command::Undo | Command::Redo => {
            return Err(CoreError::new(
                "invalid_preview",
                "undo/redo must be applied as committed commands",
            ));
        }
    }
    Ok(())
}

fn check_character(document: &SceneDocument, character_id: &str) -> Result<()> {
    if character_id != document.character.id {
        return Err(CoreError::new(
            "invalid_reference",
            format!("unknown character {character_id}"),
        ));
    }
    Ok(())
}

fn command_summary(command: &Command) -> String {
    match command {
        Command::SetParameters { values, .. } => format!("Set {} parameter(s)", values.len()),
        Command::SetScale { scale, .. } => format!("Set scale to {scale}"),
        Command::SetDiagnosticPose { pose_id, .. } => format!("Set diagnostic pose to {pose_id}"),
        Command::SetAppearance { .. } => "Set character appearance".into(),
        Command::SetTimeline { clips } => format!("Set {} timeline clip(s)", clips.len()),
        Command::SetStage { .. } => "Set rehearsal stage".into(),
        Command::Undo => "Undo".into(),
        Command::Redo => "Redo".into(),
    }
}

// A zero-allocation-value prepass retains only object keys while traversing JSON.
// Serde's normal recursion limit also protects this pass against deep nesting.
struct UniqueJson;

impl<'de> Deserialize<'de> for UniqueJson {
    fn deserialize<D: serde::Deserializer<'de>>(
        deserializer: D,
    ) -> std::result::Result<Self, D::Error> {
        struct Visitor;
        impl<'de> serde::de::Visitor<'de> for Visitor {
            type Value = UniqueJson;
            fn expecting(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                f.write_str("JSON without duplicate object keys")
            }
            fn visit_bool<E: serde::de::Error>(
                self,
                _: bool,
            ) -> std::result::Result<UniqueJson, E> {
                Ok(UniqueJson)
            }
            fn visit_i64<E: serde::de::Error>(self, _: i64) -> std::result::Result<UniqueJson, E> {
                Ok(UniqueJson)
            }
            fn visit_u64<E: serde::de::Error>(self, _: u64) -> std::result::Result<UniqueJson, E> {
                Ok(UniqueJson)
            }
            fn visit_f64<E: serde::de::Error>(self, _: f64) -> std::result::Result<UniqueJson, E> {
                Ok(UniqueJson)
            }
            fn visit_str<E: serde::de::Error>(self, _: &str) -> std::result::Result<UniqueJson, E> {
                Ok(UniqueJson)
            }
            fn visit_unit<E: serde::de::Error>(self) -> std::result::Result<UniqueJson, E> {
                Ok(UniqueJson)
            }
            fn visit_seq<A: serde::de::SeqAccess<'de>>(
                self,
                mut seq: A,
            ) -> std::result::Result<UniqueJson, A::Error> {
                while seq.next_element::<UniqueJson>()?.is_some() {}
                Ok(UniqueJson)
            }
            fn visit_map<A: serde::de::MapAccess<'de>>(
                self,
                mut map: A,
            ) -> std::result::Result<UniqueJson, A::Error> {
                let mut keys = BTreeSet::new();
                while let Some(key) = map.next_key::<String>()? {
                    if !keys.insert(key.clone()) {
                        return Err(serde::de::Error::custom(format!(
                            "duplicate object key: {key}"
                        )));
                    }
                    map.next_value::<UniqueJson>()?;
                }
                Ok(UniqueJson)
            }
        }
        deserializer.deserialize_any(Visitor)
    }
}

#[cfg(test)]
mod b1_motion_tests;

#[cfg(test)]
mod b1_character_tests;
