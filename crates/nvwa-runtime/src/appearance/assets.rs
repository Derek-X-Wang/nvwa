//! Immutable admitted asset set. No path execution, external resolution, or network access.
use bevy::{
    asset::RenderAssetUsages,
    image::{CompressedImageFormats, ImageSampler, ImageType},
    prelude::*,
    render::render_resource::TextureFormat,
};
use nvwa_core::{B1AppearanceManifest, B1AppearanceSet};
#[cfg(test)]
pub(super) const SKIN_PNG: &[u8] = include_bytes!(
    "../../../../assets/appearances/mpfb-b1-cc0-v1/skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png"
);
const FIXED_V1: &[(&str, &[u8])] = &[
    (
        "SOURCE.json",
        include_bytes!("../../../../assets/appearances/mpfb-b1-cc0-v1/SOURCE.json"),
    ),
    (
        "eyes/low-poly/low-poly.mhclo",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v1/eyes/low-poly/low-poly.mhclo"
        ),
    ),
    (
        "eyes/low-poly/low-poly.obj",
        include_bytes!("../../../../assets/appearances/mpfb-b1-cc0-v1/eyes/low-poly/low-poly.obj"),
    ),
    (
        "eyes/materials/brown.mhmat",
        include_bytes!("../../../../assets/appearances/mpfb-b1-cc0-v1/eyes/materials/brown.mhmat"),
    ),
    (
        "eyes/materials/brown_eye.png",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v1/eyes/materials/brown_eye.png"
        ),
    ),
    (
        "hair/short04/short04.mhclo",
        include_bytes!("../../../../assets/appearances/mpfb-b1-cc0-v1/hair/short04/short04.mhclo"),
    ),
    (
        "hair/short04/short04.mhmat",
        include_bytes!("../../../../assets/appearances/mpfb-b1-cc0-v1/hair/short04/short04.mhmat"),
    ),
    (
        "hair/short04/short04.obj",
        include_bytes!("../../../../assets/appearances/mpfb-b1-cc0-v1/hair/short04/short04.obj"),
    ),
    (
        "hair/short04/short04_diffuse.png",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v1/hair/short04/short04_diffuse.png"
        ),
    ),
    (
        "licenses/CC0-1.0.txt",
        include_bytes!("../../../../assets/appearances/mpfb-b1-cc0-v1/licenses/CC0-1.0.txt"),
    ),
    (
        "provenance/selected-items.json",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v1/provenance/selected-items.json"
        ),
    ),
    (
        "skins/young_caucasian_female2/young_caucasian_female2.mhmat",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v1/skins/young_caucasian_female2/young_caucasian_female2.mhmat"
        ),
    ),
    (
        "skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v1/skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png"
        ),
    ),
];
const FIXED_V2: &[(&str, &[u8])] = &[
    (
        "SOURCE.json",
        include_bytes!("../../../../assets/appearances/mpfb-b1-cc0-v2/SOURCE.json"),
    ),
    (
        "eyes/low-poly/low-poly.mhclo",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2/eyes/low-poly/low-poly.mhclo"
        ),
    ),
    (
        "eyes/low-poly/low-poly.obj",
        include_bytes!("../../../../assets/appearances/mpfb-b1-cc0-v2/eyes/low-poly/low-poly.obj"),
    ),
    (
        "eyes/materials/brown.mhmat",
        include_bytes!("../../../../assets/appearances/mpfb-b1-cc0-v2/eyes/materials/brown.mhmat"),
    ),
    (
        "eyes/materials/brown_eye.png",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2/eyes/materials/brown_eye.png"
        ),
    ),
    (
        "hair/short04/short04.mhclo",
        include_bytes!("../../../../assets/appearances/mpfb-b1-cc0-v2/hair/short04/short04.mhclo"),
    ),
    (
        "hair/short04/short04.mhmat",
        include_bytes!("../../../../assets/appearances/mpfb-b1-cc0-v2/hair/short04/short04.mhmat"),
    ),
    (
        "hair/short04/short04.obj",
        include_bytes!("../../../../assets/appearances/mpfb-b1-cc0-v2/hair/short04/short04.obj"),
    ),
    (
        "hair/short04/short04_diffuse.png",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2/hair/short04/short04_diffuse.png"
        ),
    ),
    (
        "licenses/CC0-1.0.txt",
        include_bytes!("../../../../assets/appearances/mpfb-b1-cc0-v2/licenses/CC0-1.0.txt"),
    ),
    (
        "provenance/selected-items.json",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2/provenance/selected-items.json"
        ),
    ),
    (
        "skins/young_caucasian_female2/young_caucasian_female2.mhmat",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2/skins/young_caucasian_female2/young_caucasian_female2.mhmat"
        ),
    ),
    (
        "skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2/skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png"
        ),
    ),
];
const FIXED_V2_SHORT01: &[(&str, &[u8])] = &[
    (
        "SOURCE.json",
        include_bytes!("../../../../assets/appearances/mpfb-b1-cc0-v2-short01-v1/SOURCE.json"),
    ),
    (
        "eyes/low-poly/low-poly.mhclo",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2-short01-v1/eyes/low-poly/low-poly.mhclo"
        ),
    ),
    (
        "eyes/low-poly/low-poly.obj",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2-short01-v1/eyes/low-poly/low-poly.obj"
        ),
    ),
    (
        "eyes/materials/brown.mhmat",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2-short01-v1/eyes/materials/brown.mhmat"
        ),
    ),
    (
        "eyes/materials/brown_eye.png",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2-short01-v1/eyes/materials/brown_eye.png"
        ),
    ),
    (
        "hair/short01/short01.mhclo",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2-short01-v1/hair/short01/short01.mhclo"
        ),
    ),
    (
        "hair/short01/short01.mhmat",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2-short01-v1/hair/short01/short01.mhmat"
        ),
    ),
    (
        "hair/short01/short01.obj",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2-short01-v1/hair/short01/short01.obj"
        ),
    ),
    (
        "hair/short01/short01_diffuse.png",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2-short01-v1/hair/short01/short01_diffuse.png"
        ),
    ),
    (
        "licenses/CC0-1.0.txt",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2-short01-v1/licenses/CC0-1.0.txt"
        ),
    ),
    (
        "provenance/makehuman_system_assets.json",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2-short01-v1/provenance/makehuman_system_assets.json"
        ),
    ),
    (
        "provenance/selected-items.json",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2-short01-v1/provenance/selected-items.json"
        ),
    ),
    (
        "skins/young_caucasian_female2/young_caucasian_female2.mhmat",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2-short01-v1/skins/young_caucasian_female2/young_caucasian_female2.mhmat"
        ),
    ),
    (
        "skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png",
        include_bytes!(
            "../../../../assets/appearances/mpfb-b1-cc0-v2-short01-v1/skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png"
        ),
    ),
];
pub(super) fn fixed(set: B1AppearanceSet) -> &'static [(&'static str, &'static [u8])] {
    match set {
        B1AppearanceSet::V1 => FIXED_V1,
        B1AppearanceSet::V2 => FIXED_V2,
        B1AppearanceSet::V2Short01 => FIXED_V2_SHORT01,
    }
}
pub(super) fn payload(set: B1AppearanceSet, path: &str) -> Result<&'static [u8], String> {
    fixed(set)
        .iter()
        .find(|(candidate, _)| *candidate == path)
        .map(|(_, bytes)| *bytes)
        .ok_or_else(|| format!("appearance: missing fixed payload {path}"))
}
pub(super) fn authenticate_file(
    set: B1AppearanceSet,
    path: &str,
    bytes: &[u8],
) -> Result<(), String> {
    B1AppearanceManifest::from_bytes_for(set, set.manifest_bytes())
        .and_then(|m| m.validate_file_bytes(path, bytes))
        .map_err(|e| e.to_string())
}
pub(super) fn authenticate(set: B1AppearanceSet) -> Result<(), String> {
    let manifest = B1AppearanceManifest::from_bytes_for(set, set.manifest_bytes())
        .map_err(|e| e.to_string())?;
    let fixed = fixed(set);
    if fixed
        .iter()
        .map(|(path, _)| *path)
        .ne(manifest.files.keys().map(String::as_str))
    {
        return Err("appearance: embedded payload coverage mismatch".into());
    }
    for (path, bytes) in fixed {
        manifest
            .validate_file_bytes(path, bytes)
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}
pub(super) fn decode(bytes: &[u8], size: u32) -> Result<Image, String> {
    let image = Image::from_buffer(
        bytes,
        ImageType::Extension("png"),
        CompressedImageFormats::NONE,
        true,
        ImageSampler::default(),
        RenderAssetUsages::default(),
    )
    .map_err(|e| format!("appearance PNG decode: {e}"))?;
    if image.width() != size
        || image.height() != size
        || image.texture_descriptor.format != TextureFormat::Rgba8UnormSrgb
        || image
            .data
            .as_ref()
            .is_none_or(|d| d.len() != size as usize * size as usize * 4)
    {
        return Err("appearance decoded sRGB RGBA image domain mismatch".into());
    }
    Ok(image)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn every_fixed_byte_is_authenticated() {
        for set in [
            B1AppearanceSet::V1,
            B1AppearanceSet::V2,
            B1AppearanceSet::V2Short01,
        ] {
            authenticate(set).unwrap();
            assert_eq!(
                fixed(set).len(),
                if set == B1AppearanceSet::V2Short01 {
                    14
                } else {
                    13
                }
            );
            for (path, bytes) in fixed(set) {
                let mut bad = bytes.to_vec();
                bad[0] ^= 1;
                assert!(authenticate_file(set, path, &bad).is_err(), "{path}");
                assert!(
                    authenticate_file(set, path, &bytes[..bytes.len() - 1]).is_err(),
                    "{path}"
                );
            }
            assert!(authenticate_file(set, "../arbitrary", b"x").is_err());
        }
    }
}
