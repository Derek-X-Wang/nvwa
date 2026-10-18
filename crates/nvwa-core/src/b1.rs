//! Bounded B1 identity and byte validation. No filesystem or renderer dependency.
use crate::{CharacterProfile, ClipSpec, CoreError, ParameterSpec, Result, parse_json};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub const B1_PROFILE_ID: &str = "nvwa-mpfb-b1-v1";
pub const B1_MOTION_PROFILE_ID: &str = "nvwa-mpfb-b1-motion-v1";
pub const B1_MOTION_CLIPS: [&str; 2] = ["b1_arm_rehearsal_v1", "b1_knee_flex_v1"];
pub const B1_MOTION_DURATION_SECONDS: f32 = 4.0;
pub const B1_ASSET_ID: &str = "mpfb-hm08-game-engine-female-sportsuit01-v1";
pub const B1_ASSET_PATH: &str = "characters/mpfb-b1-v1/manifest.json";
pub const B1_ASSET_MANIFEST_SHA256: &str =
    "abcdbc26e03431c740c5fce98de22902089f985823a3c655db2416d042d62b18";
pub const B1_ASSET_MANIFEST_BYTES: &[u8] =
    include_bytes!("../../../assets/characters/mpfb-b1-v1/manifest.json");
pub const B1_DIAGNOSTIC_POSES: [&str; 5] = ["neutral", "shoulder", "elbow", "knee", "combined"];
pub const B1_MAX_MANIFEST_BYTES: usize = 32 * 1024;
pub const B1_MAX_ASSET_BYTES: usize = 4 * 1024 * 1024;
pub const B1_MAX_TOTAL_ASSET_BYTES: usize = 8 * 1024 * 1024;

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum CharacterBackend {
    Glb {
        schema_version: u32,
    },
    B1Cpu {
        schema_version: u32,
        asset_id: String,
    },
}

impl<'de> Deserialize<'de> for CharacterBackend {
    fn deserialize<D: serde::Deserializer<'de>>(
        deserializer: D,
    ) -> std::result::Result<Self, D::Error> {
        // String's decoder rejects explicit null; presence rejects glb asset_id,
        // including null. Derive retains duplicate/unknown-field rejection.
        #[derive(Default)]
        struct AssetId(Option<String>);
        impl<'de> Deserialize<'de> for AssetId {
            fn deserialize<D: serde::Deserializer<'de>>(
                deserializer: D,
            ) -> std::result::Result<Self, D::Error> {
                String::deserialize(deserializer).map(|id| Self(Some(id)))
            }
        }
        #[derive(Deserialize)]
        #[serde(deny_unknown_fields)]
        struct Wire {
            #[serde(rename = "type")]
            kind: String,
            schema_version: u32,
            #[serde(default)]
            asset_id: AssetId,
        }
        let wire = Wire::deserialize(deserializer)?;
        match (wire.kind.as_str(), wire.asset_id.0) {
            ("glb", None) => Ok(Self::Glb {
                schema_version: wire.schema_version,
            }),
            ("glb", Some(_)) => Err(serde::de::Error::custom(
                "glb backend does not allow asset_id",
            )),
            ("b1_cpu", Some(asset_id)) => Ok(Self::B1Cpu {
                schema_version: wire.schema_version,
                asset_id,
            }),
            ("b1_cpu", None) => Err(serde::de::Error::missing_field("asset_id")),
            (kind, _) => Err(serde::de::Error::custom(format!(
                "unsupported_character_backend: unknown character backend {kind}"
            ))),
        }
    }
}

impl CharacterBackend {
    pub fn is_b1(&self) -> bool {
        matches!(self, Self::B1Cpu { .. })
    }
    pub fn is_b1_motion(&self) -> bool {
        matches!(
            self,
            Self::B1Cpu {
                schema_version: 2,
                ..
            }
        )
    }
    pub fn supports_timeline(&self) -> bool {
        self.is_glb() || self.is_b1_motion()
    }
    pub fn is_glb(&self) -> bool {
        matches!(self, Self::Glb { .. })
    }
    pub fn validate(&self) -> Result<()> {
        let version = match self {
            Self::Glb { schema_version } | Self::B1Cpu { schema_version, .. } => *schema_version,
        };
        if version != 1 && !(version == 2 && self.is_b1()) {
            return Err(CoreError::new(
                "unsupported_character_version",
                format!("character backend version {version} is unsupported; expected 1"),
            ));
        }
        if let Self::B1Cpu { asset_id, .. } = self
            && asset_id != B1_ASSET_ID
        {
            return Err(CoreError::new(
                "unsupported_character_asset",
                format!("unsupported B1 asset {asset_id}; expected {B1_ASSET_ID}"),
            ));
        }
        Ok(())
    }
}

impl CharacterProfile {
    /// The only admitted B1 sample. Indices 0/1 are inert legacy metadata on
    /// this backend, never GLB morph indices. Source target pairs are fixed.
    pub fn b1() -> Self {
        Self {
            backend: CharacterBackend::B1Cpu {
                schema_version: 1,
                asset_id: B1_ASSET_ID.into(),
            },
            id: B1_PROFILE_ID.into(),
            asset_path: B1_ASSET_PATH.into(),
            asset_sha256: B1_ASSET_MANIFEST_SHA256.into(),
            license: "CC0-1.0".into(),
            parameters: ["torso_length", "jaw_drop"]
                .into_iter()
                .enumerate()
                .map(|(morph_index, id)| ParameterSpec {
                    id: id.into(),
                    morph_index,
                    min: -1.0,
                    max: 1.0,
                    default: 0.0,
                })
                .collect(),
            clips: Vec::new(),
        }
    }
    /// Authored continuous rehearsal on the same admitted body and sportsuit.
    pub fn b1_motion() -> Self {
        let mut profile = Self::b1();
        profile.backend = CharacterBackend::B1Cpu {
            schema_version: 2,
            asset_id: B1_ASSET_ID.into(),
        };
        profile.id = B1_MOTION_PROFILE_ID.into();
        profile.clips = B1_MOTION_CLIPS
            .into_iter()
            .enumerate()
            .map(|(animation_index, id)| ClipSpec {
                id: id.into(),
                animation_index,
                duration_seconds: B1_MOTION_DURATION_SECONDS,
            })
            .collect();
        profile
    }
    pub(crate) fn validate_b1(&self) -> Result<()> {
        if (self.id == B1_PROFILE_ID && self.backend.is_b1_motion())
            || (self.id == B1_MOTION_PROFILE_ID && !self.backend.is_b1_motion())
        {
            return Err(CoreError::new(
                "unsupported_character_version",
                "B1 backend version does not match its canonical profile identity",
            ));
        }
        let canonical = if self.backend.is_b1_motion() {
            Self::b1_motion()
        } else {
            Self::b1()
        };
        if self != &canonical {
            return Err(CoreError::new(
                "unsupported_character_asset",
                "B1 requires its exact versioned shipped profile, asset identity, parameters and clip catalogue",
            ));
        }
        Ok(())
    }
}

pub(crate) fn validate_b1_pose(pose: &str) -> Result<()> {
    if !B1_DIAGNOSTIC_POSES.contains(&pose) {
        return Err(CoreError::new(
            "unsupported_pose",
            format!(
                "unsupported B1 diagnostic pose {pose}; expected neutral, shoulder, elbow, knee or combined"
            ),
        ));
    }
    Ok(())
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct B1AssetFile {
    pub path: String,
    pub bytes: usize,
    pub sha256: String,
    pub license: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct B1AssetManifest {
    pub format: String,
    pub schema_version: u32,
    pub asset_id: String,
    pub common_manifest_sha256: String,
    pub adapter_receipt_sha256: String,
    pub files: Vec<B1AssetFile>,
}

impl B1AssetManifest {
    /// Authenticate the exact shipped descriptor before interpreting its paths.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self> {
        if bytes.is_empty() {
            return Err(CoreError::new(
                "asset_missing",
                "B1 manifest is empty or missing",
            ));
        }
        if bytes.len() > B1_MAX_MANIFEST_BYTES {
            return Err(CoreError::new(
                "invalid_asset",
                "B1 manifest exceeds 32 KiB",
            ));
        }
        if format!("{:x}", Sha256::digest(bytes)) != B1_ASSET_MANIFEST_SHA256 {
            return Err(CoreError::new(
                "asset_hash_mismatch",
                "B1 manifest differs from the shipped descriptor",
            ));
        }
        let manifest = Self::decode(bytes)?;
        manifest.validate()?;
        Ok(manifest)
    }

    fn decode(bytes: &[u8]) -> Result<Self> {
        let text = std::str::from_utf8(bytes)
            .map_err(|e| CoreError::new("invalid_asset", e.to_string()))?;
        parse_json(text).map_err(|e| CoreError::new("invalid_asset", e.message))
    }

    /// Public fields do not grant callers authority to change the authenticated
    /// file set, hashes, paths or bounds used by validate_file_bytes.
    pub fn validate(&self) -> Result<()> {
        let canonical = Self::decode(B1_ASSET_MANIFEST_BYTES)?;
        if self != &canonical
            || self.format != "nvwa-b1-assets"
            || self.schema_version != 1
            || self.asset_id != B1_ASSET_ID
            || self.files.len() != 13
        {
            return Err(CoreError::new(
                "invalid_asset",
                "B1 descriptor must contain the exact shipped thirteen-file set and identities",
            ));
        }
        let mut total = 0usize;
        let mut previous: Option<&str> = None;
        for file in &self.files {
            if file.bytes == 0
                || file.bytes > B1_MAX_ASSET_BYTES
                || file.license != "CC0-1.0"
                || previous.is_some_and(|p| p >= file.path.as_str())
                || file
                    .path
                    .split('/')
                    .any(|p| p.is_empty() || p == "." || p == "..")
                || file
                    .path
                    .chars()
                    .any(|c| c.is_control() || matches!(c, '\\' | ':' | '?' | '#' | '%'))
            {
                return Err(CoreError::new(
                    "invalid_asset",
                    format!("invalid B1 asset descriptor entry {}", file.path),
                ));
            }
            previous = Some(&file.path);
            total = total
                .checked_add(file.bytes)
                .ok_or_else(|| CoreError::new("invalid_asset", "B1 asset total overflow"))?;
        }
        if total > B1_MAX_TOTAL_ASSET_BYTES {
            return Err(CoreError::new(
                "invalid_asset",
                "B1 asset total exceeds 8 MiB",
            ));
        }
        Ok(())
    }

    /// Validate caller-owned bytes, which a loader can then consume directly.
    /// This never reopens a path and never trusts a changed public descriptor.
    pub fn validate_file_bytes(&self, path: &str, bytes: &[u8]) -> Result<()> {
        self.validate()?;
        let file = self
            .files
            .iter()
            .find(|file| file.path == path)
            .ok_or_else(|| {
                CoreError::new(
                    "invalid_asset",
                    format!("unrecognized B1 asset path {path}"),
                )
            })?;
        if bytes.is_empty() {
            return Err(CoreError::new(
                "asset_missing",
                format!("B1 asset {path} is empty or missing"),
            ));
        }
        if bytes.len() > B1_MAX_ASSET_BYTES || bytes.len() != file.bytes {
            return Err(CoreError::new(
                "invalid_asset",
                format!(
                    "B1 asset {path} size mismatch; expected {} bytes, received {}",
                    file.bytes,
                    bytes.len()
                ),
            ));
        }
        if format!("{:x}", Sha256::digest(bytes)) != file.sha256 {
            return Err(CoreError::new(
                "asset_hash_mismatch",
                format!("B1 asset {path} SHA-256 mismatch"),
            ));
        }
        Ok(())
    }
}
