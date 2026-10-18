//! Immutable admitted asset set. No path execution, external resolution, or network access.
use bevy::{
    asset::RenderAssetUsages,
    image::{CompressedImageFormats, ImageSampler, ImageType},
    prelude::*,
    render::render_resource::TextureFormat,
};
use nvwa_core::{B1_APPEARANCE_MANIFEST_BYTES, B1AppearanceManifest};
pub(super) const SKIN_PNG: &[u8] = include_bytes!(
    "../../../../assets/appearances/mpfb-b1-cc0-v1/skins/young_caucasian_female2/young_lightskinned_female_diffuse2.png"
);
pub(super) const FIXED: &[(&str, &[u8])] = &[
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
pub(super) fn authenticate_file(path: &str, bytes: &[u8]) -> Result<(), String> {
    B1AppearanceManifest::from_bytes(B1_APPEARANCE_MANIFEST_BYTES)
        .and_then(|m| m.validate_file_bytes(path, bytes))
        .map_err(|e| e.to_string())
}
pub(super) fn authenticate() -> Result<(), String> {
    let manifest = B1AppearanceManifest::from_bytes(B1_APPEARANCE_MANIFEST_BYTES)
        .map_err(|e| e.to_string())?;
    for (path, bytes) in FIXED {
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
        authenticate().unwrap();
        for (path, bytes) in FIXED {
            let mut bad = bytes.to_vec();
            bad[0] ^= 1;
            assert!(authenticate_file(path, &bad).is_err(), "{path}");
            assert!(
                authenticate_file(path, &bytes[..bytes.len() - 1]).is_err(),
                "{path}"
            );
        }
        assert!(authenticate_file("../arbitrary", b"x").is_err());
    }
}
