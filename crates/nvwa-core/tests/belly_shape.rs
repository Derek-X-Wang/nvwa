use nvwa_core::*;
use std::collections::BTreeMap;

#[test]
fn belly_profile_adds_exactly_one_authenticated_target_to_v10() {
    let predecessor = CharacterProfile::b1_character_chest_placement();
    let profile = CharacterProfile::b1_character_belly_shape();
    assert_eq!(profile.parameters[..25], predecessor.parameters);
    assert_eq!(profile.parameters.len(), 26);
    assert!(!profile.backend.supports_timeline());
    assert_eq!(profile.backend.b1_asset_version(), Some(B1AssetVersion::V15));
    let p = &profile.parameters[25];
    let target = B1AssetVersion::V15.one_sided_target().unwrap();
    assert_eq!((p.id.as_str(), p.morph_index, p.min, p.max, p.default), (target.id, 25, 0.0, 1.0, 0.0));
    assert_eq!(B1AssetVersion::V10.one_sided_target(), None);
    assert_eq!(B1AssetVersion::V11.one_sided_target(), None);
    assert_eq!(target.positive_weight(0.0), None);
    assert_eq!(target.positive_weight(0.25), Some(0.0625));
    assert_eq!(target.positive_weight(0.5), Some(0.125));
    assert_eq!(target.positive_weight(1.0), Some(0.25));
    assert_eq!(target.positive_weight(-0.01), None);
    assert_eq!(target.positive_weight(1.01), None);
    assert_eq!(target.positive_weight(f32::NAN), None);
    let old = B1AssetManifest::from_bytes_for(B1AssetVersion::V10, B1AssetVersion::V10.manifest_bytes()).unwrap();
    let new = B1AssetManifest::from_bytes_for(B1AssetVersion::V15, B1AssetVersion::V15.manifest_bytes()).unwrap();
    assert_eq!(new.files.len(), old.files.len() + 1);
    assert!(old.files.iter().all(|f| new.files.contains(f)));
    let path = format!("targets/{}.target", target.increase);
    let bytes = include_bytes!("../../../assets/characters/mpfb-b1-v15/targets/stomach-pregnant-incr.target");
    new.validate_file_bytes(&path, bytes).unwrap();
    assert!(new.validate_file_bytes(&path, &bytes[..bytes.len() - 1]).is_err());
    assert!(new.validate_file_bytes("targets/stomach-pregnant-decr.target", bytes).is_err());
    let mut forged = profile;
    forged.asset_sha256 = predecessor.asset_sha256;
    assert!(SceneDocument::from_profile(forged).is_err());
}

#[test]
fn belly_shape_edits_roundtrip_and_reject_invalid_values_atomically() {
    let doc = SceneDocument::from_profile(CharacterProfile::b1_character_belly_shape()).unwrap();
    let mut ed = Editor::new(doc.clone()).unwrap();
    for (i, v) in [0.0, 0.25, 0.5, 1.0, -0.01, 1.01, f32::NAN, f32::INFINITY]
        .into_iter()
        .enumerate()
    {
        let before = ed.document().clone();
        let result = ed.apply(CommandEnvelope {
            command_id: format!("belly-{i}"),
            expected_revision: before.revision,
            command: Command::SetParameters {
                character_id: doc.character.id.clone(),
                values: BTreeMap::from([
                    (B1_BELLY_SHAPE_TARGET.id.into(), v),
                    ("waist_circumference".into(), 0.3),
                    ("hip_depth".into(), 0.2),
                    ("breast_spacing".into(), -0.1),
                ]),
            },
        });
        if i < 4 {
            result.unwrap();
            let roundtrip = SceneDocument::from_json(&ed.document().to_json().unwrap()).unwrap();
            assert_eq!(&roundtrip, ed.document());
            assert_eq!(roundtrip.character.parameters[B1_BELLY_SHAPE_TARGET.id], v);
            assert_eq!(roundtrip.character.parameters["waist_circumference"], 0.3);
            assert_eq!(roundtrip.character.parameters["hip_depth"], 0.2);
            assert_eq!(roundtrip.character.parameters["breast_spacing"], -0.1);
        } else {
            assert!(result.is_err());
            assert_eq!(ed.document(), &before);
        }
    }
}
