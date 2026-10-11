//! Headless replay through the pinned bevy_egui public input systems.
//! This does not inject physical/OS/CUA events or access the clipboard.
use bevy_ecs::{message::Messages, prelude::*};
use bevy_egui::{EguiClipboard, EguiContext, egui, input::{
    EguiInputEvent, ModifierKeysState, WindowToEguiContextMap,
    write_keyboard_input_messages_system, write_modifiers_keys_state_system,
}};
use bevy_input::{ButtonState, keyboard::{Key, KeyCode, KeyboardInput, KeyboardFocusLost}};

fn event(window: Entity, command: bool, pressed: bool) -> KeyboardInput {
    KeyboardInput {
        window,
        key_code: if command { KeyCode::SuperLeft } else { KeyCode::KeyA },
        logical_key: if command { Key::Super } else { Key::Character("a".into()) },
        state: if pressed { ButtonState::Pressed } else { ButtonState::Released },
        text: None,
        repeat: false,
    }
}

struct Harness {
    world: World,
    schedule: Schedule,
    window: Entity,
    context: Entity,
}

impl Harness {
    fn new() -> Self {
        let mut world = World::new();
        world.init_resource::<Messages<KeyboardInput>>();
        world.init_resource::<Messages<KeyboardFocusLost>>();
        world.init_resource::<Messages<EguiInputEvent>>();
        world.init_resource::<ModifierKeysState>();
        // Lazy default: the A branch never initializes or reads arboard.
        world.init_resource::<EguiClipboard>();
        let window = world.spawn_empty().id();
        let context = world.spawn(EguiContext::default()).id();
        let mut map = WindowToEguiContextMap::default();
        map.window_to_contexts.entry(window).or_default().insert(context);
        map.context_to_window.insert(context, window);
        world.insert_resource(map);
        let mut schedule = Schedule::default();
        // EguiPlugin InitReading precedes ReadBevyMessages; invoke the real systems.
        schedule.add_systems((write_modifiers_keys_state_system, write_keyboard_input_messages_system).chain());
        Self { world, schedule, window, context }
    }

    fn frame(&mut self, keys: &[(bool, bool)]) -> Vec<egui::Event> {
        for &(command, pressed) in keys {
            self.world.resource_mut::<Messages<KeyboardInput>>().write(event(self.window, command, pressed));
        }
        self.schedule.run(&mut self.world);
        self.world.resource_mut::<Messages<KeyboardInput>>().clear();
        self.world.resource_mut::<Messages<EguiInputEvent>>().drain().map(|message| {
            assert_eq!(message.context, self.context);
            message.event
        }).collect()
    }
}

fn text_frame(ctx: &egui::Context, text: &mut String, events: Vec<egui::Event>, id: egui::Id) -> egui::text::CCursorRange {
    let input = egui::RawInput { events, ..Default::default() };
    let mut range = None;
    let mut output = ctx.run_ui(input, |ui| {
        egui::CentralPanel::default().show(ui, |ui| {
            range = egui::TextEdit::singleline(text).id(id).show(ui).cursor_range;
        });
    });
    // This headless probe deliberately has no renderer or texture uploads.
    output.textures_delta.clear();
    range.expect("TextEdit must retain focused cursor")
}

fn run_case(name: &str, frames: &[&[(bool, bool)]], expected_command: bool, expected_text: &str) {
    let mut harness = Harness::new();
    let ctx = egui::Context::default();
    let id = egui::Id::new(name);
    ctx.memory_mut(|memory| memory.request_focus(id));
    let mut text = String::from("jaw target");
    let _ = text_frame(&ctx, &mut text, vec![], id);
    // Establish the same initial cursor at end for every scenario.
    let mut state = egui::text_edit::TextEditState::load(&ctx, id).expect("text state");
    state.cursor.set_char_range(Some(egui::text::CCursorRange::one(egui::text::CCursor::new(text.chars().count()))));
    state.store(&ctx, id);
    let mut command_at_a = None;
    let mut selection = None;
    for (index, frame) in frames.iter().enumerate() {
        let events = harness.frame(frame);
        println!("{name} frame={index} modifier_state={:?} events={events:?}", harness.world.resource::<ModifierKeysState>());
        for event in &events {
            if let egui::Event::Key { key: egui::Key::A, pressed: true, modifiers, .. } = event {
                command_at_a = Some(modifiers.command);
            }
        }
        selection = Some(text_frame(&ctx, &mut text, events, id));
    }
    assert_eq!(command_at_a, Some(expected_command), "{name}: Command state at A");
    let range = selection.expect("at least one frame");
    let selected = range.slice_str(&text).to_owned();
    assert_eq!(selected == "jaw target", expected_command, "{name}: select-all downstream");
    text_frame(&ctx, &mut text, vec![egui::Event::Text("SENTINEL".into())], id);
    assert_eq!(text, expected_text, "{name}: downstream replacement");
    println!("PASS {name}: command_at_a={expected_command} selected={selected:?} replacement_result={text:?}");
}

fn main() {
    assert!(cfg!(target_os = "macos"), "This Command probe requires a macOS build");
    run_case("plain_a", &[&[(false, true), (false, false)]], false, "jaw targetaSENTINEL");
    run_case("command_a_one_frame", &[&[(true, true), (false, true), (false, false), (true, false)]], false, "jaw targetaSENTINEL");
    run_case("command_a_held_frames", &[&[(true, true)], &[(false, true), (false, false)], &[(true, false)]], true, "SENTINEL");
    println!("PASS all 3 library replay cases. OS/CUA delivery and physical keyboard behavior were not tested.");
}
