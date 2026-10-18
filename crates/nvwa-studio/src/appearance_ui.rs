//! Saved appearance controls use the same portable command as CLI agents.
use bevy_egui::egui;
use nvwa_core::{CharacterAppearance, Command, SceneDocument};

pub(super) fn draw(ui: &mut egui::Ui, document: &SceneDocument) -> Option<Command> {
    if !document.profile.backend.is_b1() {
        return None;
    }
    ui.separator();
    ui.label("外观 / Appearance");
    let (mut skin, mut eyes, mut hair) =
        document.character.appearance.b1_flags().unwrap_or_default();
    let skin_changed = ui.checkbox(&mut skin, "皮肤 / Skin").changed();
    let eyes_changed = ui.checkbox(&mut eyes, "眼睛 / Eyes").changed();
    let hair_changed = ui.checkbox(&mut hair, "头发 / Hair").changed();
    ui.small("随作品保存 / Included in Work");
    if !(skin_changed || eyes_changed || hair_changed) {
        return None;
    }
    Some(Command::SetAppearance {
        character_id: document.character.id.clone(),
        appearance: CharacterAppearance::b1_cc0_for(&document.profile.backend, skin, eyes, hair)
            .ok()?,
    })
}
