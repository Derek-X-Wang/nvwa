//! Synthetic message replay at the real Bevy-to-egui boundary, not a browser capture.
use bevy_ecs::{message::Messages, prelude::*};
use bevy_egui::{egui, EguiClipboard, EguiContext, input::{EguiInputEvent, ModifierKeysState, WindowToEguiContextMap,
    write_modifiers_keys_state_system, write_keyboard_input_messages_system, write_ime_messages_system}};
use bevy_input::{ButtonState, keyboard::{Key, KeyCode, KeyboardInput, KeyboardFocusLost, NativeKey}};
use bevy_window::Ime;

struct Harness { world: World, schedule: Schedule, window: Entity, context: Entity, ctx: egui::Context, id: egui::Id, text: String }
impl Harness {
    fn new(name: &str) -> Self {
        let mut world = World::new();
        world.init_resource::<Messages<KeyboardInput>>();
        world.init_resource::<Messages<KeyboardFocusLost>>();
        world.init_resource::<Messages<Ime>>();
        world.init_resource::<Messages<EguiInputEvent>>();
        world.init_resource::<ModifierKeysState>();
        world.init_resource::<EguiClipboard>();
        let window = world.spawn_empty().id();
        let context = world.spawn(EguiContext::default()).id();
        let mut map = WindowToEguiContextMap::default();
        map.window_to_contexts.entry(window).or_default().insert(context);
        map.context_to_window.insert(context, window);
        world.insert_resource(map);
        let mut schedule = Schedule::default();
        schedule.add_systems((write_modifiers_keys_state_system, write_keyboard_input_messages_system, write_ime_messages_system).chain());
        let ctx = egui::Context::default();
        let id = egui::Id::new(name);
        ctx.memory_mut(|memory| memory.request_focus(id));
        let mut h = Self { world, schedule, window, context, ctx, id, text: String::new() };
        h.frame(); h
    }
    fn keyboard(&mut self, logical_key: Key, text: Option<&str>) {
        self.world.resource_mut::<Messages<KeyboardInput>>().write(KeyboardInput { window: self.window,
            key_code: KeyCode::KeyA, logical_key, text: text.map(Into::into), repeat: false, state: ButtonState::Pressed });
    }
    fn ime(&mut self, event: Ime) { self.world.resource_mut::<Messages<Ime>>().write(event); }
    fn frame(&mut self) {
        self.frame_with_focus(true);
    }
    fn frame_with_focus(&mut self, focused: bool) {
        self.schedule.run(&mut self.world);
        self.world.resource_mut::<Messages<KeyboardInput>>().clear();
        self.world.resource_mut::<Messages<Ime>>().clear();
        let events: Vec<_> = self.world.resource_mut::<Messages<EguiInputEvent>>().drain().map(|e| {
            assert_eq!(e.context, self.context); e.event
        }).collect();
        println!("[DEBUG-ime08] boundary events={events:?}");
        let mut output = self.ctx.run_ui(egui::RawInput { events, focused, ..Default::default() }, |ui| {
            egui::CentralPanel::default().show(ui, |ui| { egui::TextEdit::singleline(&mut self.text).id(self.id).show(ui); });
        });
        output.textures_delta.clear();
    }
    fn preedit(&mut self) {
        self.ime(Ime::Enabled { window: self.window }); self.frame();
        self.ime(Ime::Preedit { window: self.window, value: "nv".into(), cursor: Some((0,2)) }); self.frame();
    }
    fn commit(&mut self) { self.ime(Ime::Commit { window: self.window, value: "女娲".into() }); self.frame(); }
    fn expect(&self, name: &str, expected: &str) -> bool {
        let pass = self.text == expected;
        println!("{} {name}: expected={expected:?} actual={:?}", if pass {"PASS"} else {"FAIL"}, self.text); pass
    }
}

fn missing_commit() -> bool {
    let mut h = Harness::new("missing_commit");
    h.preedit();
    h.ime(Ime::Disabled { window: h.window }); h.frame();
    h.expect("synthetic_missing_commit_requires_女娲", "女娲")
}

fn main() {
    if std::env::args().any(|a| a == "--red-only") { std::process::exit(if missing_commit() {0} else {1}); }
    println!("Synthetic pinned-library replay only; browser/physical delivery is NOT-RUN.");
    let mut pass = true;
    let mut ascii = Harness::new("ascii"); ascii.keyboard(Key::Character("a".into()), Some("a")); ascii.frame(); pass &= ascii.expect("ascii", "a");
    let mut unicode = Harness::new("logical_unicode"); unicode.keyboard(Key::Character("女娲".into()), Some("女娲")); unicode.frame(); pass &= unicode.expect("logical_unicode", "女娲");
    let mut commit = Harness::new("ime_complete"); commit.preedit(); commit.commit(); commit.ime(Ime::Disabled {window: commit.window}); commit.frame(); pass &= commit.expect("ime_complete", "女娲");
    println!("Diagnostic cases follow; their observed outputs are not assertions of browser behavior:");
    pass &= !missing_commit(); // Required diagnostic sensitivity: missing Commit must fail the user symptom assertion.
    let mut text_only = Harness::new("keyboard_text_only"); text_only.keyboard(Key::Unidentified(NativeKey::Unidentified), Some("女娲")); text_only.frame(); pass &= text_only.expect("keyboard_text_only_ignored", "");
    let mut duplicate = Harness::new("duplicate_commit"); duplicate.preedit(); duplicate.commit(); duplicate.keyboard(Key::Character("女娲".into()), Some("女娲")); duplicate.frame(); pass &= duplicate.expect("ime_plus_keyboard_unicode_duplicate", "女娲女娲");
    let mut blur = Harness::new("blur_before_commit"); blur.preedit(); blur.ctx.memory_mut(|m| m.surrender_focus(blur.id)); blur.commit(); pass &= blur.expect("blur_before_commit_lost", "nv");
    let mut window_blur = Harness::new("raw_window_blur"); window_blur.preedit();
    let prior_range = egui::text_edit::TextEditState::load(&window_blur.ctx, window_blur.id).unwrap().cursor.char_range();
    window_blur.frame_with_focus(false);
    assert!(window_blur.ctx.memory(|m| m.has_focus(window_blur.id)), "raw window blur must not surrender widget focus");
    let range_after_blur = egui::text_edit::TextEditState::load(&window_blur.ctx, window_blur.id).unwrap().cursor.char_range();
    assert_eq!(prior_range, range_after_blur, "raw window blur must preserve text selection");
    window_blur.ime(Ime::Commit { window: window_blur.window, value: "女娲".into() }); window_blur.frame_with_focus(false);
    pass &= window_blur.expect("raw_window_blur_commit_widget_focus_retained", "女娲");
    let mut space = Harness::new("space_after_commit"); space.preedit(); space.commit(); space.keyboard(Key::Space, Some(" ")); space.frame(); pass &= space.expect("space_after_commit", "女娲 ");
    assert!(space.ctx.egui_wants_keyboard_input(), "focused text must keep Space out of viewport playback");
    println!("PASS focused text retains egui keyboard interest after Space; production playback was not executed.");
    std::process::exit(if pass {0} else {1});
}
