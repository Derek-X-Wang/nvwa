//! Portable appearance selection and authentication for the fixed shipped set.
use crate::{
    B1_ASSET_ID, B1_ASSET_MANIFEST_SHA256, CharacterBackend, CoreError, Result, parse_json,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

pub const B1_APPEARANCE_ID: &str = "mpfb-b1-cc0-appearance-v1";
pub const B1_APPEARANCE_MANIFEST_SHA256: &str =
    "c3cf2b1040eed083fb1a328f0494b0c978cec42c71f3b7c826e14992f97cef04";
pub const B1_APPEARANCE_MANIFEST_BYTES: &[u8] =
    include_bytes!("../../../assets/appearances/mpfb-b1-cc0-v1/manifest.json");
pub const B1_APPEARANCE_MANIFEST_PATH: &str = "appearances/mpfb-b1-cc0-v1/manifest.json";
pub const B1_APPEARANCE_MAX_MANIFEST_BYTES: usize = 32 * 1024;
pub const B1_APPEARANCE_MAX_ASSET_BYTES: usize = 4 * 1024 * 1024;
pub const B1_APPEARANCE_MAX_TOTAL_ASSET_BYTES: usize = 8 * 1024 * 1024;

/// SHA-256 identity for caller-owned appearance descriptor and payload bytes.
pub fn appearance_sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum CharacterAppearance {
    #[default]
    None,
    B1Cc0 {
        schema_version: u32,
        asset_set_id: String,
        asset_set_sha256: String,
        skin: bool,
        eyes: bool,
        hair: bool,
    },
}

impl<'de> Deserialize<'de> for CharacterAppearance {
    fn deserialize<D: serde::Deserializer<'de>>(
        deserializer: D,
    ) -> std::result::Result<Self, D::Error> {
        // The empty struct variant rejects extra fields on None. Typed fields
        // reject missing/null/duplicate values without a lossy Value map.
        #[derive(Deserialize)]
        #[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
        enum Wire {
            None {},
            B1Cc0 {
                schema_version: u32,
                asset_set_id: String,
                asset_set_sha256: String,
                skin: bool,
                eyes: bool,
                hair: bool,
            },
        }
        let appearance = match Wire::deserialize(deserializer)? {
            Wire::None {} => Self::None,
            Wire::B1Cc0 {
                schema_version,
                asset_set_id,
                asset_set_sha256,
                skin,
                eyes,
                hair,
            } => Self::B1Cc0 {
                schema_version,
                asset_set_id,
                asset_set_sha256,
                skin,
                eyes,
                hair,
            },
        };
        appearance.validate().map_err(serde::de::Error::custom)?;
        Ok(appearance)
    }
}

impl CharacterAppearance {
    /// Construct a canonical independent selection; no selected roles is None.
    pub fn b1_cc0(skin: bool, eyes: bool, hair: bool) -> Self {
        if !(skin || eyes || hair) {
            return Self::None;
        }
        Self::B1Cc0 {
            schema_version: 1,
            asset_set_id: B1_APPEARANCE_ID.into(),
            asset_set_sha256: B1_APPEARANCE_MANIFEST_SHA256.into(),
            skin,
            eyes,
            hair,
        }
    }

    pub fn b1_flags(&self) -> Option<(bool, bool, bool)> {
        match self {
            Self::None => None,
            Self::B1Cc0 {
                skin, eyes, hair, ..
            } => Some((*skin, *eyes, *hair)),
        }
    }

    pub(crate) fn validate(&self) -> Result<()> {
        if let Self::B1Cc0 {
            schema_version,
            asset_set_id,
            asset_set_sha256,
            skin,
            eyes,
            hair,
        } = self
        {
            if *schema_version != 1 {
                return Err(CoreError::new(
                    "unsupported_appearance_version",
                    "B1 CC0 appearance requires schema version 1",
                ));
            }
            if asset_set_id != B1_APPEARANCE_ID || asset_set_sha256 != B1_APPEARANCE_MANIFEST_SHA256
            {
                return Err(CoreError::new(
                    "unsupported_appearance_asset",
                    "B1 CC0 appearance requires the exact shipped asset set and manifest hash",
                ));
            }
            if !(*skin || *eyes || *hair) {
                return Err(CoreError::new(
                    "invalid_appearance",
                    "B1 CC0 requires at least one selected role; use none for no appearance",
                ));
            }
        }
        Ok(())
    }

    pub fn validate_for(&self, backend: &CharacterBackend) -> Result<()> {
        self.validate()?;
        if matches!(self, Self::B1Cc0 { .. }) {
            backend.validate()?;
            if !backend.is_b1() {
                return Err(CoreError::new(
                    "unsupported_character_operation",
                    "B1 CC0 appearance requires the B1 character backend",
                ));
            }
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct B1AppearanceFile {
    pub bytes: usize,
    pub license: String,
    pub sha256: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct B1AppearanceManifest {
    pub format: String,
    pub schema_version: u32,
    pub asset_set_id: String,
    pub base_asset_id: String,
    pub base_manifest_sha256: String,
    pub material_policy: String,
    pub files: BTreeMap<String, B1AppearanceFile>,
}

impl B1AppearanceManifest {
    /// Authenticate immutable descriptor bytes before interpreting any path.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self> {
        if bytes.is_empty() {
            return Err(CoreError::new(
                "asset_missing",
                "B1 appearance manifest is empty or missing",
            ));
        }
        if bytes.len() > B1_APPEARANCE_MAX_MANIFEST_BYTES {
            return Err(CoreError::new(
                "invalid_asset",
                "B1 appearance manifest exceeds 32 KiB",
            ));
        }
        if appearance_sha256(bytes) != B1_APPEARANCE_MANIFEST_SHA256 {
            return Err(CoreError::new(
                "asset_hash_mismatch",
                "B1 appearance manifest differs from the shipped descriptor",
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

    /// Public fields cannot grant authority to replace paths, sizes or hashes.
    pub fn validate(&self) -> Result<()> {
        let canonical = Self::decode(B1_APPEARANCE_MANIFEST_BYTES)?;
        if self != &canonical
            || self.format != "nvwa-b1-appearance"
            || self.schema_version != 1
            || self.asset_set_id != B1_APPEARANCE_ID
            || self.base_asset_id != B1_ASSET_ID
            || self.base_manifest_sha256 != B1_ASSET_MANIFEST_SHA256
            || self.files.len() != 13
        {
            return Err(CoreError::new(
                "invalid_asset",
                "B1 appearance requires the exact shipped thirteen-file descriptor and base identity",
            ));
        }
        let mut total = 0usize;
        for (path, file) in &self.files {
            if file.bytes == 0
                || file.bytes > B1_APPEARANCE_MAX_ASSET_BYTES
                || file.license != "CC0-1.0"
                || path
                    .split('/')
                    .any(|part| part.is_empty() || part == "." || part == "..")
                || path
                    .chars()
                    .any(|c| c.is_control() || matches!(c, '\\' | ':' | '?' | '#' | '%'))
            {
                return Err(CoreError::new(
                    "invalid_asset",
                    format!("invalid B1 appearance entry {path}"),
                ));
            }
            total = total
                .checked_add(file.bytes)
                .ok_or_else(|| CoreError::new("invalid_asset", "B1 appearance size overflow"))?;
        }
        if total > B1_APPEARANCE_MAX_TOTAL_ASSET_BYTES {
            return Err(CoreError::new(
                "invalid_asset",
                "B1 appearance assets exceed 8 MiB",
            ));
        }
        Ok(())
    }

    pub fn validate_file_bytes(&self, path: &str, bytes: &[u8]) -> Result<()> {
        self.validate()?;
        let file = self.files.get(path).ok_or_else(|| {
            CoreError::new(
                "invalid_asset",
                format!("unrecognized B1 appearance path {path}"),
            )
        })?;
        if bytes.is_empty() {
            return Err(CoreError::new(
                "asset_missing",
                format!("B1 appearance asset {path} is empty or missing"),
            ));
        }
        if bytes.len() != file.bytes || bytes.len() > B1_APPEARANCE_MAX_ASSET_BYTES {
            return Err(CoreError::new(
                "invalid_asset",
                format!("B1 appearance asset {path} size mismatch"),
            ));
        }
        if appearance_sha256(bytes) != file.sha256 {
            return Err(CoreError::new(
                "asset_hash_mismatch",
                format!("B1 appearance asset {path} SHA-256 mismatch"),
            ));
        }
        Ok(())
    }
}
