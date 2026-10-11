// Appended to an unmodified copy of production web_input.rs by the tiny runner.
#[cfg(test)]
mod independent_rework_regressions {
    use super::*;
    fn frame(ctx: &egui::Context, old: &mut String, next: &mut String, old_id: egui::Id, next_id: egui::Id, events: Vec<egui::Event>) {
        let mut output = ctx.run_ui(egui::RawInput { events, ..Default::default() }, |ui| {
            egui::CentralPanel::default().show(ui, |ui| {
                assert_eq!(old_id, work_id());
                work_text_edit(ui, old, 220.0);
                egui::TextEdit::singleline(next).id(next_id).show(ui);
            });
        });
        output.textures_delta.clear();
    }
    #[test]
    fn singleline_clipboard_filters_line_breaks_through_actual_delivery() {
        let ctx = egui::Context::default(); let id = work_id(); let next_id = egui::Id::new("next");
        ctx.memory_mut(|m| m.request_focus(id));
        let mut text = String::new(); let mut next = String::new();
        frame(&ctx, &mut text, &mut next, id, next_id, vec![]);
        let mut delivery = TextDelivery::default();
        frame(&ctx, &mut text, &mut next, id, next_id, delivery.paste("one\r\ntwo\nthree".into()));
        assert_eq!(text, "one  two three", "egui replaces each CR/LF with a space");
        assert!(!text.contains(['\r', '\n']));
    }
    #[test]
    fn old_target_cancel_after_focus_change_cannot_leave_preedit_canonical() {
        let ctx = egui::Context::default(); let id = work_id(); let next_id = egui::Id::new("next");
        ctx.memory_mut(|m| m.request_focus(id));
        let mut text = String::from("path"); let mut next = String::from("other");
        frame(&ctx, &mut text, &mut next, id, next_id, vec![]);
        let mut delivery = TextDelivery::default(); delivery.begin();
        frame(&ctx, &mut text, &mut next, id, next_id, delivery.preedit("nv".into()));
        assert_eq!(text, "path", "actual adapter emits no uncommitted preview");
        ctx.memory_mut(|m| m.request_focus(next_id));
        let events = delivery.cancel();
        // The production drain uses this exact predicate and drops the old cancellation.
        let events = if ctx.memory(|m| m.focused()) == Some(id) { events } else { vec![] };
        frame(&ctx, &mut text, &mut next, id, next_id, events);
        assert_eq!(text, "path", "canonical Work text must not retain abandoned preedit");
        assert_eq!(next, "other", "cancel must not alter new target");
    }
    #[test]
    fn studio_horizontal_toolbar_consumes_one_commit_once() {
        let ctx = egui::Context::default();
        ctx.memory_mut(|memory| memory.request_focus(work_id()));
        let mut text = "works/exchanged.nvwa.json".to_owned();
        let mut run = |events: Vec<egui::Event>| {
            let mut output = ctx.run_ui(egui::RawInput {
                screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, egui::vec2(1200.0, 800.0))),
                events, ..Default::default()
            }, |ui| {
                egui::Panel::top("document_toolbar").show(ui, |ui| {
                    ui.horizontal(|ui| {
                        ui.heading("Nvwa"); ui.separator();
                        ui.add(egui::Button::new("Undo")); ui.add(egui::Button::new("Redo"));
                        ui.separator(); ui.label("作品 / Work");
                        work_text_edit(ui, &mut text, 220.0);
                        ui.add(egui::Button::new("Open…")); ui.add(egui::Button::new("Save"));
                        ui.label("Revision 6");
                    });
                });
            });
            println!("horizontal passes={} interrupt={:?}", output.platform_output.num_completed_passes, output.platform_output.ime.map(|ime| ime.should_interrupt_composition));
            output.textures_delta.clear();
        };
        run(vec![]);
        let mut delivery = TextDelivery::default(); delivery.begin(); delivery.preedit("nv".into());
        let mut events = delivery.end("女娲".into());
        events.extend(delivery.input("女娲".into(), "insertFromComposition", false));
        assert_eq!(events.len(), 1);
        run(events);
        assert_eq!(text, "works/exchanged.nvwa.json女娲", "actual horizontal toolbar must consume a single commit once");
    }
    #[test]
    fn forced_discard_pass_consumes_one_commit_once() {
        let ctx = egui::Context::default();
        ctx.memory_mut(|memory| memory.request_focus(work_id()));
        let mut text = "path".to_owned();
        let mut next = String::new();
        frame(&ctx, &mut text, &mut next, work_id(), egui::Id::new("other"), vec![]);
        let mut output = ctx.run_ui(egui::RawInput { events: vec![egui::Event::Ime(egui::ImeEvent::Commit("女娲".into()))], ..Default::default() }, |ui| {
            egui::CentralPanel::default().show(ui, |ui| work_text_edit(ui, &mut text, 220.0));
            if ctx.current_pass_index() == 0 { ctx.request_discard("explicit bounded replay"); }
        });
        assert_eq!(output.platform_output.num_completed_passes, 2);
        output.textures_delta.clear();
        assert_eq!(text, "path女娲");
    }

}
