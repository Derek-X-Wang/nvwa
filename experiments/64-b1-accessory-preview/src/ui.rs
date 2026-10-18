//! Native and Web controls use the same request queue as the external test interface.
use crate::Preview;
use bevy::prelude::*;
use bevy_egui::{EguiContexts, egui};
use serde_json::json;
#[derive(Resource)]
pub struct Controls {
    torso: f32,
    jaw: f32,
    seconds: f32,
    knee: bool,
    serial: u64,
}
impl Default for Controls {
    fn default() -> Self {
        Self {
            torso: 0.,
            jaw: 0.,
            seconds: 0.,
            knee: false,
            serial: 0,
        }
    }
}
pub fn controls(mut contexts: EguiContexts, mut p: ResMut<Preview>, mut c: ResMut<Controls>) {
    let Ok(ctx) = contexts.ctx_mut() else {
        return;
    };
    egui::Window::new("Experimental appearance · NOT SAVED")
        .default_pos(egui::pos2(600., 52.))
        .default_width(320.)
        .show(ctx, |ui| {
            ui.label("64 · baseline / skin / eyes + hair");
            ui.label("Temporary preview. Work saves shape and motion only.");
            let mut action = None;
            ui.horizontal(|ui| {
                if ui.button("Baseline").clicked() {
                    action = Some("baseline");
                }
                if ui.button("Skin").clicked() {
                    action = Some("skin");
                }
                if ui.button("Skin + eyes + hair").clicked() {
                    action = Some("accessories");
                }
            });
            ui.horizontal(|ui| {
                for (label, name) in [
                    ("Full", "view_full"),
                    ("Face", "view_face"),
                    ("Back", "view_back"),
                ] {
                    if ui.button(label).clicked() {
                        action = Some(name);
                    }
                }
            });
            ui.collapsing("Sample and playback", |ui| {
                ui.add(egui::Slider::new(&mut c.torso, -1.0..=1.0).text("Torso"));
                ui.add(egui::Slider::new(&mut c.jaw, 0.0..=1.0).text("Jaw"));
                ui.checkbox(&mut c.knee, "Knee clip (otherwise arm)");
                ui.add(egui::Slider::new(&mut c.seconds, 0.0..=4.0).text("Seconds"));
                ui.horizontal(|ui| {
                    if ui.button("Sample").clicked() {
                        action = Some("sample");
                    }
                    if ui.button("Play").clicked() {
                        action = Some("play");
                    }
                    if ui.button("Pause").clicked() {
                        action = Some("pause");
                    }
                    if ui.button("Report").clicked() {
                        action = Some("report");
                    }
                });
            });
            ui.label(format!(
                "Appearance: {}",
                if p.accessories {
                    "skin + eyes + hair"
                } else if p.desired {
                    "skin"
                } else {
                    "baseline"
                }
            ));
            ui.label(format!(
                "Proof: {}",
                p.report["phase"].as_str().unwrap_or("waiting")
            ));
            if let Some(e) = p.report["error"].as_str() {
                ui.colored_label(egui::Color32::LIGHT_RED, e);
            }
            if let Some(e) = &p.accessory.error {
                ui.colored_label(egui::Color32::LIGHT_RED, e);
            }
            ui.small("Simple diffuse / alpha cutout 0.5. Clothes & M2 HOLD.");
            if let Some(action) = action {
                c.serial += 1;
                let mut v = json!({"request_id":format!("ui-{}",c.serial),"action":action});
                if action == "sample" {
                    v["clip_id"] = json!(if c.knee {
                        "b1_knee_flex_v1"
                    } else {
                        "b1_arm_rehearsal_v1"
                    });
                    v["seconds"] = json!(c.seconds);
                    v["torso_length"] = json!(c.torso);
                    v["jaw_drop"] = json!(c.jaw);
                }
                p.pending = None;
                p.queue.clear();
                p.frame = None;
                p.report = json!({"phase":"pending","request":v});
                p.queue.push_back(v);
            }
        });
}
