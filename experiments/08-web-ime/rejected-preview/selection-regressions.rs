// Appended to the exact frozen 4db production module. Expected to fail.
#[cfg(test)]
mod omitted_selection_regressions {
    use super::*;
    fn frame(ctx: &egui::Context, text: &mut String, events: Vec<egui::Event>) {
        let mut output = ctx.run_ui(egui::RawInput { events, ..Default::default() }, |ui| {
            egui::CentralPanel::default().show(ui, |ui| work_text_edit(ui, text, 220.0));
        });
        output.textures_delta.clear();
    }
    fn selection() -> Vec<egui::Event> {
        key_event("a", true, false, egui::Modifiers { command: true, mac_cmd: true, ..Default::default() }).unwrap().0
    }
    #[test]
    fn selected_original_must_survive_canceled_preedit() {
        let ctx = egui::Context::default(); ctx.memory_mut(|m| m.request_focus(work_id()));
        let mut text = "path".to_owned(); frame(&ctx, &mut text, vec![]);
        let mut delivery = TextDelivery::default(); delivery.begin();
        let mut events = selection(); events.extend(delivery.preedit("hao".into()));
        frame(&ctx, &mut text, events); frame(&ctx, &mut text, delivery.cancel());
        assert_eq!(text, "path", "selected original cannot disappear on cancel");
    }
    #[test]
    fn intermediate_commit_must_survive_selected_new_preedit_cancel() {
        let ctx = egui::Context::default(); ctx.memory_mut(|m| m.request_focus(work_id()));
        let mut text = "path".to_owned(); frame(&ctx, &mut text, vec![]);
        let mut delivery = TextDelivery::default(); delivery.begin();
        frame(&ctx, &mut text, delivery.preedit("nv".into()));
        let mut events = delivery.end("女娲".into()); events.extend(selection());
        delivery.begin(); events.extend(delivery.preedit("hao".into()));
        frame(&ctx, &mut text, events); frame(&ctx, &mut text, delivery.cancel());
        assert_eq!(text, "path女娲", "intermediate commit cannot disappear on cancel");
    }
}
