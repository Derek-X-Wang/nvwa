use crate::{CharacterProfile, CoreError, MAX_JSON_BYTES, Result};
use serde_json::Value;
use sha2::{Digest, Sha256};

impl CharacterProfile {
    /// Verify caller-supplied asset bytes. File IO and root containment belong to
    /// the platform caller. This method has no filesystem, GPU, or Bevy dependency.
    pub fn validate_asset_bytes(&self, bytes: &[u8]) -> Result<()> {
        self.validate()?;
        if bytes.is_empty() {
            return Err(CoreError::new("missing_asset", "asset is empty or missing"));
        }
        let actual = format!("{:x}", Sha256::digest(bytes));
        if !actual.eq_ignore_ascii_case(&self.asset_sha256) {
            return Err(CoreError::new(
                "asset_hash_mismatch",
                format!(
                    "asset SHA-256 mismatch: expected {}, received {actual}",
                    self.asset_sha256
                ),
            ));
        }
        let json = glb_json(bytes)?;
        if json.pointer("/asset/version").and_then(Value::as_str) != Some("2.0") {
            return Err(invalid("GLB must contain a glTF 2.0 asset"));
        }
        // This portable profile identifies one self-contained binary asset.
        for collection in ["buffers", "images"] {
            if let Some(items) = json.get(collection).and_then(Value::as_array) {
                for item in items {
                    if let Some(uri) = item.get("uri")
                        && !uri.as_str().is_some_and(|s| s.starts_with("data:"))
                    {
                        return Err(CoreError::new(
                            "external_asset_reference",
                            "GLB contains an external resource URI",
                        ));
                    }
                }
            }
        }
        let animations = json.get("animations").and_then(Value::as_array);
        for clip in &self.clips {
            if !animations.is_some_and(|items| {
                items.get(clip.animation_index).is_some_and(|animation| {
                    animation
                        .get("channels")
                        .and_then(Value::as_array)
                        .is_some_and(|c| !c.is_empty())
                })
            }) {
                return Err(CoreError::new(
                    "invalid_animation_index",
                    format!(
                        "clip {} references missing/empty animation {}",
                        clip.id, clip.animation_index
                    ),
                ));
            }
        }
        let morph_count = json
            .get("meshes")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
            .flat_map(|mesh| {
                mesh.get("primitives")
                    .and_then(Value::as_array)
                    .into_iter()
                    .flatten()
            })
            .filter_map(|primitive| {
                primitive
                    .get("targets")
                    .and_then(Value::as_array)
                    .map(Vec::len)
            })
            .max()
            .unwrap_or(0);
        for parameter in &self.parameters {
            if parameter.morph_index >= morph_count {
                return Err(CoreError::new(
                    "invalid_morph_index",
                    format!(
                        "parameter {} references missing morph {} (asset has {morph_count})",
                        parameter.id, parameter.morph_index
                    ),
                ));
            }
        }
        Ok(())
    }
}

fn invalid(message: &str) -> CoreError {
    CoreError::new("invalid_asset", message)
}

fn word(bytes: &[u8], offset: usize) -> Result<u32> {
    let slice = bytes
        .get(offset..offset + 4)
        .ok_or_else(|| invalid("truncated GLB header/chunk"))?;
    let array: [u8; 4] = slice
        .try_into()
        .map_err(|_| invalid("truncated GLB word"))?;
    Ok(u32::from_le_bytes(array))
}

fn glb_json(bytes: &[u8]) -> Result<Value> {
    if bytes.get(..4) != Some(b"glTF") || word(bytes, 4)? != 2 {
        return Err(invalid("asset must be a GLB version 2 binary"));
    }
    if word(bytes, 8)? as usize != bytes.len() {
        return Err(invalid("GLB declared length does not match asset length"));
    }
    let mut offset = 12usize;
    let mut json = None;
    let mut binary_seen = false;
    while offset < bytes.len() {
        let length = word(bytes, offset)? as usize;
        let kind = word(bytes, offset + 4)?;
        if !length.is_multiple_of(4) {
            return Err(invalid("GLB chunk length must be aligned to four bytes"));
        }
        let start = offset
            .checked_add(8)
            .ok_or_else(|| invalid("GLB length overflow"))?;
        let end = start
            .checked_add(length)
            .ok_or_else(|| invalid("GLB length overflow"))?;
        let chunk = bytes
            .get(start..end)
            .ok_or_else(|| invalid("truncated GLB chunk"))?;
        match kind {
            0x4e4f534a if offset == 12 && json.is_none() => {
                if length > MAX_JSON_BYTES {
                    return Err(invalid("GLB JSON exceeds the 2 MiB limit"));
                }
                let input =
                    std::str::from_utf8(chunk).map_err(|_| invalid("GLB JSON is not UTF-8"))?;
                json =
                    Some(crate::parse_json::<Value>(input).map_err(|error| {
                        invalid(&format!("invalid GLB JSON: {}", error.message))
                    })?);
            }
            0x004e4942 if json.is_some() && !binary_seen => binary_seen = true,
            _ => return Err(invalid("unexpected, duplicated, or out-of-order GLB chunk")),
        }
        offset = end;
    }
    json.ok_or_else(|| invalid("GLB has no JSON chunk"))
}
