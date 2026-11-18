//! Saved appearance controls use the same portable command as CLI agents.
use bevy_egui::egui;
use nvwa_core::{B1AppearanceSet, B1AssetVersion, CharacterAppearance, Command, SceneDocument};

pub(super) fn draw(ui: &mut egui::Ui, document: &SceneDocument) -> Option<Command> {
    if !document.profile.backend.is_b1() {
        return None;
    }
    if matches!(
        document.profile.backend.b1_asset_version(),
        Some(
            B1AssetVersion::V5
                | B1AssetVersion::V6
                | B1AssetVersion::V7
                | B1AssetVersion::V8
                | B1AssetVersion::V9
                | B1AssetVersion::V11
                | B1AssetVersion::V12
        )
    ) {
        ui.small(
            "静态体型轮廓：尚未接入皮肤、眼睛或头发 / Static shape: no appearance set admitted.",
        );
        return None;
    }
    ui.separator();
    ui.label("外观 / Appearance");
    let (mut skin, mut eyes, mut hair) =
        document.character.appearance.b1_flags().unwrap_or_default();
    let skin_changed = ui.checkbox(&mut skin, "皮肤 / Skin").changed();
    let eyes_changed = ui.checkbox(&mut eyes, "眼睛 / Eyes").changed();
    let hair_changed = ui.checkbox(&mut hair, "头发 / Hair").changed();
    let mut set = document.character.appearance.b1_set();
    let hairstyle_changed =
        if let Some(base @ (B1AssetVersion::V2 | B1AssetVersion::V3 | B1AssetVersion::V4)) =
            document.profile.backend.b1_asset_version()
        {
            let short04_set = B1AppearanceSet::for_base(base)
                .expect("listed legacy base has an admitted appearance set");
            let short01_set = match base {
                B1AssetVersion::V4 => B1AppearanceSet::V4Short01,
                B1AssetVersion::V3 => B1AppearanceSet::V3Short01,
                _ => B1AppearanceSet::V2Short01,
            };
            let mut selected = set.unwrap_or(short04_set);
            let changed = ui
                .add_enabled_ui(hair, |ui| {
                    ui.label("发型 / Hairstyle");
                    ui.horizontal(|ui| {
                        let short04 = ui
                            .selectable_value(&mut selected, short04_set, "short04")
                            .changed();
                        let short01 = ui
                            .selectable_value(&mut selected, short01_set, "short01")
                            .changed();
                        short04 || short01
                    })
                    .inner
                })
                .inner;
            set = Some(selected);
            changed
        } else {
            false
        };
    ui.small("随作品保存 / Included in Work");
    if !(skin_changed || eyes_changed || hair_changed || hairstyle_changed) {
        return None;
    }
    let appearance = match set {
        Some(set) => {
            CharacterAppearance::b1_cc0_for_set(&document.profile.backend, set, skin, eyes, hair)
        }
        None => CharacterAppearance::b1_cc0_for(&document.profile.backend, skin, eyes, hair),
    }
    .ok()?;
    Some(Command::SetAppearance {
        character_id: document.character.id.clone(),
        appearance,
    })
}
