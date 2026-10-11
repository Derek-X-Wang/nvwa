//! Portable, validated scene documents and atomic editor transactions.
#![forbid(unsafe_code)]

mod asset;

use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

pub const SCHEMA_VERSION: u32 = 1;
pub const MAX_JSON_BYTES: usize = 2 * 1024 * 1024;

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

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SceneDocument {
    pub schema_version: u32,
    pub revision: u64,
    pub profile: CharacterProfile,
    pub character: CharacterRecipe,
    pub timeline: Vec<TimelineClip>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CharacterProfile {
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

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CharacterRecipe {
    pub id: String,
    pub profile_id: String,
    pub parameters: BTreeMap<String, f32>,
    pub scale: f32,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TimelineClip {
    pub id: String,
    pub clip_id: String,
    pub start_seconds: f32,
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
    SetTimeline {
        clips: Vec<TimelineClip>,
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
            SetTimeline {
                clips: Vec<TimelineClip>,
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
            StrictCommand::SetTimeline { clips } => Self::SetTimeline { clips },
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
    serde_json::from_str(input).map_err(|error| CoreError::new("invalid_json", error.to_string()))
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
        let profile: Self = parse_json(input)?;
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
        let timeline = profile
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
        let document = Self {
            schema_version: SCHEMA_VERSION,
            revision: 0,
            character: CharacterRecipe {
                id: "character-1".into(),
                profile_id: profile.id.clone(),
                parameters,
                scale: 1.0,
            },
            profile,
            timeline,
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
        self.profile.validate()?;
        id(&self.character.id, "character id")?;
        if self.character.profile_id != self.profile.id {
            return Err(CoreError::new(
                "invalid_reference",
                "character references an unknown profile",
            ));
        }
        positive(self.character.scale, "character scale")?;
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
        Ok(())
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
            Command::SetTimeline { clips } => {
                for clip in clips {
                    finite(clip.start_seconds, "start")?;
                    finite(clip.duration_seconds, "duration")?;
                    finite(clip.speed, "speed")?;
                }
            }
            Command::Undo | Command::Redo => {}
        }
        serialize_json(self)
    }
}

/// An in-memory editing session. Retry IDs and undo history are session-local.
/// Save/open persists scene content; it does not persist the command journal.
#[derive(Clone, Debug)]
pub struct Editor {
    document: SceneDocument,
    undo: Vec<SceneDocument>,
    redo: Vec<SceneDocument>,
    committed: BTreeMap<String, (CommandEnvelope, CommandResult)>,
}

impl Editor {
    pub fn new(document: SceneDocument) -> Result<Self> {
        document.validate()?;
        Ok(Self {
            document,
            undo: Vec::new(),
            redo: Vec::new(),
            committed: BTreeMap::new(),
        })
    }

    pub fn document(&self) -> &SceneDocument {
        &self.document
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
        if let Some((previous, result)) = self.committed.get(&envelope.command_id) {
            if previous != &envelope {
                return Err(CoreError::new(
                    "command_id_conflict",
                    "command ID was already committed with a different payload",
                ));
            }
            let mut duplicate = result.clone();
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
                    .last()
                    .cloned()
                    .ok_or_else(|| CoreError::new("nothing_to_undo", "no edit to undo"))?,
                "Undo".to_string(),
            ),
            Command::Redo => (
                self.redo
                    .last()
                    .cloned()
                    .ok_or_else(|| CoreError::new("nothing_to_redo", "no edit to redo"))?,
                "Redo".to_string(),
            ),
            command => (self.preview(command)?, command_summary(command)),
        };
        candidate.revision = revision;
        candidate.validate()?;
        // All fallible work is complete. Commit state and journal together.
        match &envelope.command {
            Command::Undo => {
                self.undo.pop();
                self.redo.push(self.document.clone());
            }
            Command::Redo => {
                self.redo.pop();
                self.undo.push(self.document.clone());
            }
            _ => {
                self.undo.push(self.document.clone());
                self.redo.clear();
            }
        }
        self.document = candidate;
        let result = CommandResult {
            revision,
            summary,
            duplicate: false,
        };
        self.committed
            .insert(envelope.command_id.clone(), (envelope, result.clone()));
        Ok(result)
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
        Command::SetTimeline { clips } => document.timeline = clips.clone(),
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
        Command::SetTimeline { clips } => format!("Set {} timeline clip(s)", clips.len()),
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
