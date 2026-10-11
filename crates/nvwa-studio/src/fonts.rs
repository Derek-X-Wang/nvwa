//! One embedded, licensed Chinese fallback for native and Web egui contexts.
use bevy::prelude::*;
use bevy_egui::{EguiContext, egui};
use std::sync::Arc;

const CJK_FONT_NAME: &str = "nvwa-cjk";
const CJK_FONT_BYTES: &[u8] = include_bytes!("../../../assets/fonts/NvwaSansSC-Regular.ttf");

/// Run after egui context creation and before its first pass, including new contexts.
/// `Added` makes this independent of UI multipass execution and avoids per-frame
/// font-definition allocation. The font bytes are borrowed from the executable.
pub(crate) fn install_fonts(mut contexts: Query<&mut EguiContext, Added<EguiContext>>) {
    for mut context in &mut contexts {
        configure_fonts(context.get_mut());
    }
}

fn configure_fonts(context: &egui::Context) {
    let mut fonts = egui::FontDefinitions::default();
    fonts.font_data.insert(
        CJK_FONT_NAME.to_owned(),
        Arc::new(egui::FontData::from_static(CJK_FONT_BYTES)),
    );
    // Preserve the existing Latin/symbol fonts; add the same Chinese fallback
    // for normal labels and monospace fields. This font does not cover all Han.
    for family in [egui::FontFamily::Proportional, egui::FontFamily::Monospace] {
        fonts
            .families
            .entry(family)
            .or_default()
            .push(CJK_FONT_NAME.to_owned());
    }
    context.set_fonts(fonts);
}

#[cfg(test)]
mod tests {
    use super::*;

    fn end_cpu_pass(context: &egui::Context) {
        let mut output = context.end_pass();
        // These tests inspect CPU font parsing/layout without a GPU renderer.
        // Explicitly discard atlas uploads rather than dropping unapplied deltas.
        output.textures_delta.clear();
    }

    fn chinese_is_available(context: &egui::Context) -> bool {
        context.begin_pass(egui::RawInput::default());
        let available = context
            .fonts_mut(|fonts| fonts.has_glyphs(&egui::FontId::proportional(16.0), "作品女娲"));
        end_cpu_pass(context);
        available
    }

    #[test]
    fn bundled_font_parses_and_lays_out_chinese_with_both_default_families() {
        let context = egui::Context::default();
        assert!(!chinese_is_available(&context));
        context.begin_pass(egui::RawInput::default());
        let latin_width =
            context.fonts_mut(|fonts| fonts.glyph_width(&egui::FontId::proportional(16.0), 'W'));
        end_cpu_pass(&context);

        configure_fonts(&context);
        context.begin_pass(egui::RawInput::default());
        context.fonts_mut(|fonts| {
            assert_eq!(
                latin_width,
                fonts.glyph_width(&egui::FontId::proportional(16.0), 'W')
            );
            let mut parsed_fonts = egui::epaint::text::FontsImpl::new(
                egui::epaint::text::TextOptions::default(),
                fonts.definitions().clone(),
            );
            for family in [egui::FontFamily::Proportional, egui::FontFamily::Monospace] {
                let font_id = egui::FontId::new(16.0, family);
                let text =
                    "作品 / Work 女娲 女媧 臺灣 廣東話 龜鬱 龙年春节_最终版（修订二）.nvwa.json";
                // egui 0.36's has_glyph compares face identity with the replacement
                // face, so valid ASCII in Hack yields false for Monospace. Check
                // the actual parsed character maps for every corpus character.
                let mut parsed_family = parsed_fonts.font(&font_id.family);
                let characters = parsed_family.characters();
                let missing: Vec<_> = text
                    .chars()
                    .filter(|character| !characters.contains_key(character))
                    .map(|character| format!("{character:?} U+{:04X}", u32::from(character)))
                    .collect();
                assert!(
                    missing.is_empty(),
                    "family {:?} lacks character mappings: {missing:?}",
                    font_id.family
                );
                assert!(!characters.contains_key(&'𠮷'));
                assert!(!fonts.has_glyph(&font_id, '𠮷'));
                let galley = fonts.layout_no_wrap(text.to_owned(), font_id, egui::Color32::WHITE);
                assert!(galley.rect.width().is_finite() && galley.rect.width() > 0.0);
                assert!(galley.rect.height().is_finite() && galley.rect.height() > 0.0);
                let glyphs: Vec<_> = galley.rows.iter().flat_map(|row| &row.row.glyphs).collect();
                assert_eq!(
                    glyphs.iter().map(|glyph| glyph.chr).collect::<String>(),
                    text
                );
                for glyph in glyphs {
                    assert!(glyph.advance_width.is_finite() && glyph.advance_width > 0.0);
                    if !glyph.chr.is_whitespace() {
                        assert!(
                            !glyph.uv_rect.is_nothing(),
                            "no atlas image for {:?}",
                            glyph.chr
                        );
                    }
                }
            }
        });
        end_cpu_pass(&context);
    }

    #[test]
    fn fonts_install_for_each_new_context_and_do_not_reset_existing_contexts() {
        let mut app = App::new();
        app.add_systems(Update, install_fonts);
        let first = app.world_mut().spawn(EguiContext::default()).id();
        app.update();
        let first_context = app
            .world_mut()
            .get_mut::<EguiContext>(first)
            .unwrap()
            .get_mut()
            .clone();
        assert!(chinese_is_available(&first_context));

        // A later font change must survive ordinary frames: setup is per new
        // context, rather than being repeated in a multipass draw function.
        first_context.set_fonts(egui::FontDefinitions::default());
        let second = app.world_mut().spawn(EguiContext::default()).id();
        app.update();
        assert!(!chinese_is_available(&first_context));
        let second_context = app
            .world_mut()
            .get_mut::<EguiContext>(second)
            .unwrap()
            .get_mut()
            .clone();
        assert!(chinese_is_available(&second_context));
    }
}
