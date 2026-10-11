//! Desktop Web text delivery. Text, selection and editing stay in egui.
use bevy_egui::egui;

/// DOM final input may repeat compositionend/paste. Consume only its immediate followup.
#[derive(Default)]
struct TextDelivery {
    composing: bool,
    followup: Option<(String, bool)>, // text, paste rather than composition
}

impl TextDelivery {
    fn begin(&mut self) {
        self.composing = true;
        self.followup = None;
    }
    fn preedit(&mut self, _text: String) -> Vec<egui::Event> {
        // The DOM input and OS candidate UI own uncommitted composition.
        // Only a confirmed commit can mutate egui's canonical Work String.
        self.composing = true;
        Vec::new()
    }
    fn end(&mut self, text: String) -> Vec<egui::Event> {
        self.composing = false;
        self.followup = Some((text.clone(), false));
        if text.is_empty() {
            Vec::new()
        } else {
            vec![egui::Event::Ime(egui::ImeEvent::Commit(text))]
        }
    }
    fn input(&mut self, text: String, input_type: &str, composing: bool) -> Vec<egui::Event> {
        if self.composing || composing {
            return Vec::new();
        }
        if let Some((prior, paste)) = self.followup.take() {
            let matching_kind = if paste {
                input_type == "insertFromPaste"
            } else {
                matches!(
                    input_type,
                    "insertFromComposition" | "insertCompositionText" | "insertText"
                )
            };
            if prior == text && matching_kind {
                return Vec::new();
            }
        }
        if text.is_empty() {
            Vec::new()
        } else {
            vec![egui::Event::Text(text)]
        }
    }
    fn paste(&mut self, text: String) -> Vec<egui::Event> {
        let mut events = self.cancel();
        self.followup = Some((text.clone(), true));
        events.push(egui::Event::Paste(text));
        events
    }
    fn cancel(&mut self) -> Vec<egui::Event> {
        self.followup = None;
        self.composing = false;
        Vec::new()
    }
}

/// Only this explicit field opts into the desktop proxy and its composition transaction.
fn work_id() -> egui::Id {
    egui::Id::new("nvwa-work-path")
}

/// A stable target ID is the only addition to the shared egui Work field.
/// The browser's temporary composition never enters this canonical String.
pub(super) fn work_text_edit(ui: &mut egui::Ui, text: &mut String, width: f32) {
    egui::TextEdit::singleline(text)
        .id(work_id())
        .desired_width(width)
        .show(ui);
}

/// The desktop proxy and egui must interpret the same browser platform.
/// This metadata enables egui's own macOS navigation; no edit is implemented here.
fn configure_web_os(context: &egui::Context, user_agent: &str) {
    context.set_os(egui::os::OperatingSystem::from_user_agent(user_agent));
}

fn key_event(
    key: &str,
    pressed: bool,
    repeat: bool,
    modifiers: egui::Modifiers,
    mac: bool,
) -> Option<(Vec<egui::Event>, bool)> {
    // Pinned egui owns the edits. macOS Control navigation does not use Command,
    // and Shift disables those navigation forms; Control deletion works on all OSes.
    let control_navigation = mac && modifiers.ctrl && !modifiers.shift;
    let key = match key {
        "ArrowLeft" => egui::Key::ArrowLeft,
        "ArrowRight" => egui::Key::ArrowRight,
        "ArrowUp" => egui::Key::ArrowUp,
        "ArrowDown" => egui::Key::ArrowDown,
        "Home" => egui::Key::Home,
        "End" => egui::Key::End,
        "PageUp" => egui::Key::PageUp,
        "PageDown" => egui::Key::PageDown,
        "Backspace" => egui::Key::Backspace,
        "Delete" => egui::Key::Delete,
        "Enter" => egui::Key::Enter,
        "Tab" => egui::Key::Tab,
        "Escape" => egui::Key::Escape,
        "a" | "A" if modifiers.command || control_navigation => egui::Key::A,
        "b" | "B" if control_navigation => egui::Key::B,
        "e" | "E" if control_navigation => egui::Key::E,
        "f" | "F" if control_navigation => egui::Key::F,
        "n" | "N" if control_navigation => egui::Key::N,
        "p" | "P" if control_navigation => egui::Key::P,
        "h" | "H" if modifiers.ctrl => egui::Key::H,
        "k" | "K" if modifiers.ctrl => egui::Key::K,
        "u" | "U" if modifiers.ctrl => egui::Key::U,
        "w" | "W" if modifiers.ctrl => egui::Key::W,
        "c" | "C" if modifiers.command => egui::Key::C,
        "x" | "X" if modifiers.command => egui::Key::X,
        "v" | "V" if modifiers.command => egui::Key::V,
        "z" | "Z" if modifiers.command => egui::Key::Z,
        "y" | "Y" if modifiers.command => egui::Key::Y,
        _ => return None,
    };
    let mut events = vec![egui::Event::Key {
        key,
        physical_key: None,
        pressed,
        repeat,
        modifiers,
    }];
    if pressed && modifiers.command {
        if key == egui::Key::C {
            events.push(egui::Event::Copy);
        }
        if key == egui::Key::X {
            events.push(egui::Event::Cut);
        }
    }
    // Browser paste delivers ClipboardEvent; never read clipboard on keydown.
    Some((events, key != egui::Key::V))
}

#[cfg(target_arch = "wasm32")]
mod browser {
    use super::*;
    use bevy::prelude::*;
    use bevy::winit::{EventLoopProxyWrapper, WinitUserEvent};
    use bevy_egui::{
        EguiContext, EguiInput, EguiInputSet, EguiOutput, EguiPostUpdateSet, EguiPreUpdateSet,
        EguiStartupSet, input::EguiInputEvent,
    };
    use std::{cell::RefCell, rc::Rc};
    use wasm_bindgen::{JsCast, closure::Closure};

    #[derive(Clone, Copy, PartialEq, Eq)]
    struct Target {
        context: Entity,
        widget: egui::Id,
    }
    struct Queued {
        target: Target,
        event: egui::Event,
    }
    #[derive(Default)]
    struct State {
        target: Option<Target>,
        delivery: TextDelivery,
        events: Vec<Queued>,
        errors: Vec<String>,
        pointer_intent: bool,
        accepting: bool,
    }
    impl State {
        fn enqueue(&mut self, events: Vec<egui::Event>) {
            if let Some(target) = self.target {
                self.events
                    .extend(events.into_iter().map(|event| Queued { target, event }));
            }
        }
    }
    type Shared = Rc<RefCell<State>>;
    type Wake = Rc<dyn Fn()>;
    struct Listener {
        target: web_sys::EventTarget,
        name: &'static str,
        callback: Option<Closure<dyn FnMut(web_sys::Event)>>,
    }
    impl Drop for Listener {
        fn drop(&mut self) {
            if let Some(callback) = self.callback.take()
                && let Err(error) = self.target.remove_event_listener_with_callback(
                    self.name,
                    callback.as_ref().unchecked_ref(),
                )
            {
                error!("Web text listener teardown {}: {error:?}", self.name);
                // Keep a failed-to-remove callback alive rather than leave a dangling JS function.
                callback.forget();
            }
        }
    }
    struct Agent {
        input: web_sys::HtmlTextAreaElement,
        canvas: web_sys::HtmlElement,
        document: web_sys::Document,
        shared: Shared,
        wake: Wake,
        listeners: Vec<Listener>,
        user_agent: String,
    }
    impl Agent {
        fn listen(
            &mut self,
            target: web_sys::EventTarget,
            name: &'static str,
            handler: impl FnMut(web_sys::Event) + 'static,
        ) -> Result<(), String> {
            let callback = Closure::wrap(Box::new(handler) as Box<dyn FnMut(web_sys::Event)>);
            target
                .add_event_listener_with_callback(name, callback.as_ref().unchecked_ref())
                .map_err(|error| format!("Web text listener {name}: {error:?}"))?;
            self.listeners.push(Listener {
                target,
                name,
                callback: Some(callback),
            });
            Ok(())
        }
        fn own_focus(&self) -> bool {
            self.document
                .active_element()
                .is_some_and(|element| element == *self.input.unchecked_ref::<web_sys::Element>())
        }
        fn canvas_focus(&self) -> bool {
            self.document
                .active_element()
                .is_some_and(|element| element == *self.canvas.unchecked_ref::<web_sys::Element>())
        }
        fn focus(&self) {
            if let Err(error) = self.input.focus() {
                self.shared
                    .borrow_mut()
                    .errors
                    .push(format!("Web text focus: {error:?}"));
            }
        }
        fn style(&self, name: &str, value: &str) {
            if let Err(error) = self.input.style().set_property(name, value) {
                self.shared
                    .borrow_mut()
                    .errors
                    .push(format!("Web text style {name}: {error:?}"));
            }
        }
    }
    impl Drop for Agent {
        fn drop(&mut self) {
            self.listeners.clear();
            if let Some(parent) = self.input.parent_node()
                && let Err(error) = parent.remove_child(&self.input)
            {
                error!("Web text agent teardown: {error:?}");
            }
        }
    }

    pub struct DesktopWebInputPlugin;
    impl Plugin for DesktopWebInputPlugin {
        fn build(&self, app: &mut App) {
            app.add_systems(Startup, install.after(EguiStartupSet::InitContexts))
                .add_systems(
                    PreUpdate,
                    initialize_context_os
                        .after(EguiPreUpdateSet::InitContexts)
                        .before(EguiInputSet::WriteEguiEvents),
                )
                .add_systems(
                    PreUpdate,
                    discard_external_clipboard
                        .before(bevy_egui::web_clipboard::write_web_clipboard_events_system),
                )
                .add_systems(PreUpdate, drain.before(EguiInputSet::WriteEguiEvents))
                .add_systems(
                    PreUpdate,
                    preserve_internal_focus
                        .after(EguiInputSet::WriteEguiEvents)
                        .before(EguiPreUpdateSet::BeginPass),
                )
                .add_systems(PostUpdate, update.after(EguiPostUpdateSet::ProcessOutput));
        }
    }

    fn install(world: &mut World) {
        if let Err(message) = create_agent(world) {
            error!("{message}");
            world.resource_mut::<crate::StudioUi>().error = Some(message);
        }
    }
    fn create_agent(world: &mut World) -> Result<(), String> {
        let window = web_sys::window().ok_or("Web text: no browser window")?;
        let ua = window
            .navigator()
            .user_agent()
            .map_err(|e| format!("Web text user agent: {e:?}"))?;
        if ["Android", "iPhone", "iPad", "iPod", "webOS", "BlackBerry"]
            .iter()
            .any(|device| ua.contains(device))
        {
            return Ok(());
        }
        let document = window.document().ok_or("Web text: no document")?;
        let canvas = document
            .get_element_by_id("nvwa")
            .ok_or("Web text: missing canvas #nvwa")?
            .dyn_into::<web_sys::HtmlElement>()
            .map_err(|_| "Web text: canvas is not an HTML element")?;
        let input = document
            .create_element("textarea")
            .map_err(|e| format!("Web text create: {e:?}"))?
            .dyn_into::<web_sys::HtmlTextAreaElement>()
            .map_err(|_| "Web text: textarea cast failed")?;
        input.set_id("nvwa_text_input");
        input.set_tab_index(-1);
        input.set_hidden(true);
        for (name, value) in [
            ("aria-label", "Nvwa text input"),
            ("autocapitalize", "off"),
            ("autocomplete", "off"),
            ("spellcheck", "false"),
        ] {
            input
                .set_attribute(name, value)
                .map_err(|e| format!("Web text attribute {name}: {e:?}"))?;
        }
        input.set_attribute("style", "position:fixed;width:1px;height:1px;padding:0;border:0;opacity:0;pointer-events:none;resize:none;overflow:hidden;")
            .map_err(|e| format!("Web text initial style: {e:?}"))?;
        let shared = Shared::default();
        let proxy = world
            .get_resource::<EventLoopProxyWrapper>()
            .ok_or("Web text: Winit wake proxy unavailable")?;
        let proxy = (**proxy).clone();
        let wake: Wake = Rc::new(move || {
            if let Err(error) = proxy.send_event(WinitUserEvent::WakeUp) {
                error!("Web text wake failed: {error:?}");
            }
        });
        let mut agent = Agent {
            input,
            canvas,
            document,
            shared,
            wake,
            listeners: Vec::new(),
            user_agent: ua.clone(),
        };
        install_listeners(&mut agent, ua.contains("Mac"))?;
        agent
            .document
            .body()
            .ok_or("Web text: no document body")?
            .append_child(&agent.input)
            .map_err(|e| format!("Web text append: {e:?}"))?;
        world.insert_non_send(agent);
        Ok(())
    }

    fn initialize_context_os(
        agent: Option<NonSend<Agent>>,
        mut contexts: Query<&mut EguiContext, Added<EguiContext>>,
    ) {
        let Some(agent) = agent else {
            return;
        };
        for mut context in &mut contexts {
            configure_web_os(context.get_mut(), &agent.user_agent);
        }
    }

    fn install_listeners(agent: &mut Agent, mac: bool) -> Result<(), String> {
        let target: web_sys::EventTarget = agent.input.clone().into();
        for name in ["compositionstart", "compositionupdate", "compositionend"] {
            let shared = agent.shared.clone();
            let wake = agent.wake.clone();
            let input = agent.input.clone();
            agent.listen(target.clone(), name, move |event| {
                let Some(event) = event.dyn_ref::<web_sys::CompositionEvent>() else {
                    return;
                };
                let mut state = shared.borrow_mut();
                if !state.accepting {
                    return;
                }
                let events = match name {
                    "compositionstart" => {
                        state.delivery.begin();
                        Vec::new()
                    }
                    "compositionupdate" => state.delivery.preedit(event.data().unwrap_or_default()),
                    _ => {
                        input.set_value("");
                        state.delivery.end(event.data().unwrap_or_default())
                    }
                };
                state.enqueue(events);
                drop(state);
                wake();
            })?;
        }
        let shared = agent.shared.clone();
        let wake = agent.wake.clone();
        let input = agent.input.clone();
        agent.listen(target.clone(), "input", move |event| {
            let Some(event) = event.dyn_ref::<web_sys::InputEvent>() else {
                return;
            };
            let mut state = shared.borrow_mut();
            if !state.accepting {
                return;
            }
            let text = event.data().unwrap_or_else(|| input.value());
            let events = state
                .delivery
                .input(text, &event.input_type(), event.is_composing());
            if !event.is_composing() && !state.delivery.composing {
                input.set_value("");
            }
            state.enqueue(events);
            drop(state);
            wake();
        })?;
        for name in ["keydown", "keyup"] {
            let shared = agent.shared.clone();
            let wake = agent.wake.clone();
            agent.listen(target.clone(), name, move |event| {
                let Some(event) = event.dyn_ref::<web_sys::KeyboardEvent>() else {
                    return;
                };
                let mut state = shared.borrow_mut();
                if !state.accepting
                    || state.delivery.composing
                    || event.is_composing()
                    || event.key_code() == 229
                {
                    return;
                }
                if name == "keydown" {
                    state.delivery.followup = None;
                }
                let modifiers = egui::Modifiers {
                    alt: event.alt_key(),
                    ctrl: event.ctrl_key(),
                    shift: event.shift_key(),
                    mac_cmd: mac && event.meta_key(),
                    command: if mac {
                        event.meta_key()
                    } else {
                        event.ctrl_key() && !event.alt_key()
                    },
                };
                if let Some((events, prevent)) = key_event(
                    &event.key(),
                    name == "keydown",
                    event.repeat(),
                    modifiers,
                    mac,
                ) {
                    if prevent {
                        event.prevent_default();
                    }
                    state.enqueue(events);
                }
                drop(state);
                wake();
            })?;
        }
        for name in ["paste", "copy", "cut"] {
            let shared = agent.shared.clone();
            let wake = agent.wake.clone();
            agent.listen(target.clone(), name, move |event| {
                let Some(event) = event.dyn_ref::<web_sys::ClipboardEvent>() else {
                    return;
                };
                let mut state = shared.borrow_mut();
                if !state.accepting {
                    return;
                }
                // Own this event before bevy_egui's document-level listener can duplicate it.
                event.prevent_default();
                event.stop_propagation();
                let events = match name {
                    "copy" => vec![egui::Event::Copy],
                    "cut" => vec![egui::Event::Cut],
                    _ => match event
                        .clipboard_data()
                        .ok_or("clipboard payload unavailable")
                        .and_then(|data| {
                            data.get_data("text/plain")
                                .map_err(|_| "clipboard payload read failed")
                        }) {
                        Ok(text) => state.delivery.paste(text),
                        Err(error) => {
                            state.errors.push(format!("Web paste: {error}"));
                            Vec::new()
                        }
                    },
                };
                state.enqueue(events);
                drop(state);
                wake();
            })?;
        }
        let shared = agent.shared.clone();
        let wake = agent.wake.clone();
        agent.listen(agent.canvas.clone().into(), "pointerdown", move |_| {
            shared.borrow_mut().pointer_intent = true;
            wake();
        })?;
        // Blur itself is not a widget-focus surrender; update distinguishes internal/external focus.
        let wake = agent.wake.clone();
        agent.listen(target, "blur", move |_| wake())?;
        let wake = agent.wake.clone();
        agent.listen(agent.input.clone().into(), "focus", move |_| wake())?;
        let wake = agent.wake.clone();
        if let Some(window) = web_sys::window() {
            agent.listen(window.into(), "focus", move |_| wake())?;
        }
        Ok(())
    }

    fn discard_external_clipboard(
        agent: Option<NonSend<Agent>>,
        clipboard: Res<bevy_egui::EguiClipboard>,
    ) {
        let Some(agent) = agent else {
            return;
        };
        if !agent.own_focus() && !agent.canvas_focus() {
            // The upstream listeners are document-wide. Other DOM controls keep
            // their normal event/default behavior, but cannot edit egui's String.
            while clipboard.try_receive_clipboard_event().is_some() {}
        }
    }

    fn drain(
        agent: Option<NonSendMut<Agent>>,
        mut contexts: Query<&mut EguiContext>,
        mut writer: MessageWriter<EguiInputEvent>,
        mut ui: ResMut<crate::StudioUi>,
    ) {
        let Some(agent) = agent else {
            return;
        };
        let mut state = agent.shared.borrow_mut();
        for queued in state.events.drain(..) {
            if let Ok(mut context) = contexts.get_mut(queued.target.context)
                && context.get_mut().memory(|memory| memory.focused()) == Some(queued.target.widget)
            {
                writer.write(EguiInputEvent {
                    context: queued.target.context,
                    event: queued.event,
                });
            }
        }
        for message in state.errors.drain(..) {
            error!("{message}");
            ui.error = Some(message);
        }
    }
    fn preserve_internal_focus(agent: Option<NonSend<Agent>>, mut inputs: Query<&mut EguiInput>) {
        let Some(agent) = agent else {
            return;
        };
        if agent.document.has_focus().unwrap_or(false)
            && agent.own_focus()
            && let Some(target) = agent.shared.borrow().target
            && let Ok(mut input) = inputs.get_mut(target.context)
        {
            input.focused = true;
        }
    }
    fn update(
        agent: Option<NonSend<Agent>>,
        mut contexts: Query<(Entity, &EguiOutput, &mut EguiContext)>,
    ) {
        let Some(agent) = agent else {
            return;
        };
        let request = contexts
            .iter_mut()
            .find_map(|(entity, output, mut context)| {
                let ime = output.platform_output.ime?;
                let widget = context.get_mut().memory(|m| m.focused())?;
                if widget != work_id() {
                    return None;
                }
                Some((
                    Target {
                        context: entity,
                        widget,
                    },
                    ime,
                    context.get_mut().pixels_per_point(),
                ))
            });
        let page_focused = match agent.document.has_focus() {
            Ok(focused) => focused,
            Err(error) => {
                agent
                    .shared
                    .borrow_mut()
                    .errors
                    .push(format!("Web document focus: {error:?}"));
                false
            }
        };
        let own = agent.own_focus();
        let canvas = agent.canvas_focus();
        let mut state = agent.shared.borrow_mut();
        let pointer_intent = std::mem::take(&mut state.pointer_intent);
        if let Some((target, ime, pixels_per_point)) = request {
            let changed = state.target != Some(target);
            if changed || ime.should_interrupt_composition {
                let events = state.delivery.cancel();
                state.enqueue(events);
                agent.input.set_value("");
            }
            state.target = Some(target);
            if !page_focused || !(own || canvas) {
                let events = state.delivery.cancel();
                let redraw = !events.is_empty();
                state.enqueue(events);
                state.accepting = false;
                // A real window blur must not hide the focused proxy and reset
                // activeElement to body. Refocus can then recover naturally.
                if page_focused {
                    agent.input.set_hidden(true);
                }
                drop(state);
                if redraw {
                    (agent.wake)();
                }
                return;
            }
            state.accepting = true;
            let rect = agent.canvas.get_bounding_client_rect();
            // egui points → canvas backing pixels → canvas CSS pixels.
            let width = agent
                .canvas
                .get_attribute("width")
                .and_then(|v| v.parse::<f64>().ok())
                .unwrap_or(rect.width());
            let height = agent
                .canvas
                .get_attribute("height")
                .and_then(|v| v.parse::<f64>().ok())
                .unwrap_or(rect.height());
            let x = rect.left()
                + f64::from(ime.cursor_rect.left() * pixels_per_point) * rect.width()
                    / width.max(1.0);
            let y = rect.top()
                + f64::from(ime.cursor_rect.bottom() * pixels_per_point) * rect.height()
                    / height.max(1.0);
            agent.input.set_hidden(false);
            drop(state);
            agent.style("left", &format!("{x}px"));
            agent.style("top", &format!("{y}px"));
            // Initial text focus, a target change, or deliberate canvas interaction can transfer focus.
            if !own && (changed || pointer_intent || canvas) {
                agent.focus();
            }
        } else {
            let events = state.delivery.cancel();
            state.enqueue(events);
            state.accepting = false;
            state.target = None;
            agent.input.set_value("");
            agent.input.set_hidden(true);
            drop(state);
            if own
                && page_focused
                && let Err(error) = agent.canvas.focus()
            {
                agent
                    .shared
                    .borrow_mut()
                    .errors
                    .push(format!("Web canvas focus restore: {error:?}"));
            }
        }
    }
}

#[cfg(target_arch = "wasm32")]
pub use browser::DesktopWebInputPlugin;

#[cfg(test)]
mod tests {
    use super::*;
    fn frame(ctx: &egui::Context, text: &mut String, events: Vec<egui::Event>) {
        let mut output = ctx.run_ui(
            egui::RawInput {
                events,
                ..Default::default()
            },
            |ui| {
                egui::CentralPanel::default().show(ui, |ui| work_text_edit(ui, text, 220.0));
            },
        );
        output.textures_delta.clear();
    }
    fn fixture() -> (egui::Context, String, TextDelivery) {
        let ctx = egui::Context::default();
        ctx.memory_mut(|memory| memory.request_focus(work_id()));
        let mut text = "path".to_owned();
        frame(&ctx, &mut text, vec![]);
        (ctx, text, TextDelivery::default())
    }
    fn select_all() -> Vec<egui::Event> {
        key_event(
            "a",
            true,
            false,
            egui::Modifiers {
                command: true,
                mac_cmd: true,
                ..Default::default()
            },
            true,
        )
        .unwrap()
        .0
    }
    fn selection(ctx: &egui::Context) -> egui::text::CCursorRange {
        egui::text_edit::TextEditState::load(ctx, work_id())
            .unwrap()
            .cursor
            .char_range()
            .unwrap()
    }
    fn keyboard_fixture(text: &str, os: egui::os::OperatingSystem) -> (egui::Context, String) {
        let ctx = egui::Context::default();
        let user_agent = match os {
            egui::os::OperatingSystem::Mac => "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            egui::os::OperatingSystem::Windows => "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            _ => "unrecognized desktop platform",
        };
        configure_web_os(&ctx, user_agent);
        assert_eq!(ctx.os(), os);
        ctx.memory_mut(|memory| memory.request_focus(work_id()));
        let mut text = text.to_owned();
        frame(&ctx, &mut text, vec![]);
        (ctx, text)
    }
    fn transport_key(
        ctx: &egui::Context,
        text: &mut String,
        key: &str,
        modifiers: egui::Modifiers,
    ) {
        // A dropped DOM key must reach the behavior assertion as no editor change.
        let events = key_event(
            key,
            true,
            false,
            modifiers,
            ctx.os() == egui::os::OperatingSystem::Mac,
        )
        .map(|(events, prevent)| {
            assert!(
                prevent,
                "editor operations must prevent temporary-textarea edits"
            );
            events
        })
        .unwrap_or_default();
        frame(ctx, text, events);
    }
    fn position_cursor(ctx: &egui::Context, text: &mut String, index: usize) {
        transport_key(ctx, text, "Home", egui::Modifiers::NONE);
        for _ in 0..index {
            transport_key(ctx, text, "ArrowRight", egui::Modifiers::NONE);
        }
    }
    #[test]
    fn control_deletion_shortcuts_edit_canonical_work() {
        for os in [
            egui::os::OperatingSystem::Mac,
            egui::os::OperatingSystem::Windows,
        ] {
            let ctrl = egui::Modifiers {
                ctrl: true,
                command: os != egui::os::OperatingSystem::Mac,
                ..Default::default()
            };
            for (key, initial, cursor, expected) in [
                ("h", "abc", 3, "ab"),
                ("K", "abc", 1, "a"),
                ("u", "abc", 2, "c"),
                ("W", "one two", 7, "one "),
            ] {
                let (ctx, mut text) = keyboard_fixture(initial, os);
                position_cursor(&ctx, &mut text, cursor);
                transport_key(&ctx, &mut text, key, ctrl);
                assert_eq!(text, expected, "Control+{key} on {os:?}");
                assert!(selection(&ctx).is_empty());
            }
            let (ctx, mut text) = keyboard_fixture("one two", os);
            frame(&ctx, &mut text, select_all());
            transport_key(&ctx, &mut text, "w", ctrl);
            assert_eq!(text, "", "Control+W must delete the canonical selection");
        }
    }
    #[test]
    fn control_navigation_moves_canonical_work_cursor_on_mac() {
        let ctrl = egui::Modifiers {
            ctrl: true,
            ..Default::default()
        };
        for (key, before, after) in [
            ("a", 2, 0),
            ("E", 1, 3),
            ("b", 2, 1),
            ("F", 1, 2),
            ("p", 2, 0),
            ("N", 1, 3),
        ] {
            let (ctx, mut text) = keyboard_fixture("abc", egui::os::OperatingSystem::Mac);
            position_cursor(&ctx, &mut text, before);
            transport_key(&ctx, &mut text, key, ctrl);
            assert_eq!(text, "abc", "Control+{key} must only move the cursor");
            assert_eq!(
                selection(&ctx).as_sorted_char_range(),
                egui::text::CharIndex(after)..egui::text::CharIndex(after),
                "Control+{key} must move the canonical cursor"
            );
        }
    }
    #[test]
    fn desktop_web_platform_metadata_preserves_unsupported_shortcuts() {
        let (ctx, mut text) = keyboard_fixture("abc", egui::os::OperatingSystem::Unknown);
        position_cursor(&ctx, &mut text, 2);
        let ctrl = egui::Modifiers {
            ctrl: true,
            ..Default::default()
        };
        for key in ["a", "b", "e", "f", "n", "p"] {
            assert!(key_event(key, true, false, ctrl, false).is_none());
        }
        let shifted_ctrl = egui::Modifiers {
            shift: true,
            ..ctrl
        };
        for key in ["a", "b", "e", "f", "n", "p"] {
            assert!(key_event(key, true, false, shifted_ctrl, true).is_none());
        }
        frame(&ctx, &mut text, vec![]);
        assert_eq!(text, "abc");
        assert_eq!(
            selection(&ctx).as_sorted_char_range(),
            egui::text::CharIndex(2)..egui::text::CharIndex(2)
        );
    }
    #[test]
    fn control_repeat_release_and_command_paste_keep_editor_ownership() {
        let (ctx, mut text) = keyboard_fixture("abc", egui::os::OperatingSystem::Mac);
        position_cursor(&ctx, &mut text, 3);
        let ctrl = egui::Modifiers {
            ctrl: true,
            shift: true,
            ..Default::default()
        };
        let (events, prevent) = key_event("H", true, true, ctrl, true).unwrap_or_default();
        frame(&ctx, &mut text, events);
        assert_eq!(
            text, "ab",
            "repeated Control+H must edit once using event modifiers"
        );
        assert!(prevent);
        let (events, prevent) = key_event("H", false, false, ctrl, true).unwrap();
        frame(&ctx, &mut text, events);
        assert_eq!(text, "ab", "key release cannot delete another character");
        assert!(prevent);
        frame(&ctx, &mut text, select_all());
        let command = egui::Modifiers {
            command: true,
            mac_cmd: true,
            ..Default::default()
        };
        let (events, prevent) = key_event("v", true, false, command, true).unwrap();
        assert!(
            !prevent,
            "Command+V must retain browser ClipboardEvent delivery"
        );
        frame(&ctx, &mut text, events);
        assert_eq!(text, "ab");
        frame(
            &ctx,
            &mut text,
            TextDelivery::default().paste("pasted".into()),
        );
        assert_eq!(text, "pasted", "Command+A selection remains egui-owned");
        for key in ["a", "b", "e", "f", "h", "k", "n", "p", "u", "w", " "] {
            assert!(key_event(key, true, false, egui::Modifiers::NONE, true).is_none());
        }
    }
    #[test]
    fn canceled_preedit_never_mutates_canonical_path_or_cursor() {
        let (ctx, mut text, mut delivery) = fixture();
        let cursor = selection(&ctx);
        delivery.begin();
        frame(&ctx, &mut text, delivery.preedit("nv".into()));
        assert_eq!(
            text, "path",
            "OS-only preedit cannot enter the canonical String"
        );
        assert_eq!(selection(&ctx), cursor);
        frame(&ctx, &mut text, delivery.cancel());
        assert_eq!(text, "path");
        assert_eq!(selection(&ctx), cursor);
    }
    #[test]
    fn batched_commit_then_new_preedit_cancel_preserves_intermediate_commit() {
        let (ctx, mut text, mut delivery) = fixture();
        delivery.begin();
        frame(&ctx, &mut text, delivery.preedit("nv".into()));
        let mut events = delivery.end("女娲".into());
        events.extend(delivery.input("女娲".into(), "insertFromComposition", false));
        delivery.begin();
        events.extend(delivery.preedit("hao".into()));
        frame(&ctx, &mut text, events);
        assert_eq!(text, "path女娲");
        ctx.memory_mut(|memory| memory.surrender_focus(work_id()));
        frame(&ctx, &mut text, delivery.cancel());
        assert_eq!(
            text, "path女娲",
            "cancel cannot remove an earlier confirmed commit"
        );
    }
    #[test]
    fn select_all_then_preedit_cancel_preserves_original_selection_and_text() {
        let (ctx, mut text, mut delivery) = fixture();
        let mut events = select_all();
        delivery.begin();
        events.extend(delivery.preedit("hao".into()));
        frame(&ctx, &mut text, events);
        let selected = selection(&ctx);
        assert_eq!(
            selected.as_sorted_char_range(),
            egui::text::CharIndex(0)..egui::text::CharIndex(4)
        );
        frame(&ctx, &mut text, delivery.cancel());
        assert_eq!(text, "path");
        assert_eq!(selection(&ctx), selected);
    }
    #[test]
    fn commit_select_all_then_preedit_cancel_preserves_commit_and_selection() {
        let (ctx, mut text, mut delivery) = fixture();
        delivery.begin();
        frame(&ctx, &mut text, delivery.preedit("nv".into()));
        let mut events = delivery.end("女娲".into());
        events.extend(select_all());
        delivery.begin();
        events.extend(delivery.preedit("hao".into()));
        frame(&ctx, &mut text, events);
        let selected = selection(&ctx);
        assert_eq!(
            selected.as_sorted_char_range(),
            egui::text::CharIndex(0)..egui::text::CharIndex(6)
        );
        frame(&ctx, &mut text, delivery.cancel());
        assert_eq!(text, "path女娲");
        assert_eq!(selection(&ctx), selected);
    }
    #[test]
    fn confirmed_selected_text_replaces_once_and_space_is_ordinary_text() {
        let (ctx, mut text, mut delivery) = fixture();
        frame(&ctx, &mut text, select_all());
        delivery.begin();
        frame(&ctx, &mut text, delivery.preedit("nv".into()));
        assert_eq!(text, "path");
        frame(&ctx, &mut text, delivery.end("女娲".into()));
        frame(
            &ctx,
            &mut text,
            delivery.input("女娲".into(), "insertFromComposition", false),
        );
        assert_eq!(text, "女娲");
        frame(
            &ctx,
            &mut text,
            delivery.input(" ".into(), "insertText", false),
        );
        assert_eq!(text, "女娲 ");
        assert!(ctx.egui_wants_keyboard_input());
    }
    #[test]
    fn paste_normalizes_singleline_and_deduplicates_followup() {
        let (ctx, mut text, mut delivery) = fixture();
        frame(&ctx, &mut text, select_all());
        delivery.begin();
        frame(&ctx, &mut text, delivery.preedit("ignored".into()));
        frame(&ctx, &mut text, delivery.paste("one\r\ntwo\nthree".into()));
        assert_eq!(text, "one  two three");
        assert!(!text.contains(['\r', '\n']));
        frame(
            &ctx,
            &mut text,
            delivery.input("one\r\ntwo\nthree".into(), "insertFromPaste", false),
        );
        assert_eq!(text, "one  two three");
    }
    #[test]
    fn composition_input_and_repeated_commits_have_one_owner() {
        let mut delivery = TextDelivery::default();
        delivery.begin();
        assert!(delivery.preedit("nv".into()).is_empty());
        assert!(
            delivery
                .input("nv".into(), "insertCompositionText", true)
                .is_empty()
        );
        assert!(
            matches!(&delivery.end("女娲".into())[0], egui::Event::Ime(egui::ImeEvent::Commit(text)) if text == "女娲")
        );
        assert!(
            delivery
                .input("女娲".into(), "insertFromComposition", false)
                .is_empty()
        );
        delivery.begin();
        assert_eq!(delivery.end("女娲".into()).len(), 1);
        delivery.begin();
        assert!(delivery.cancel().is_empty());
        assert!(delivery.end(String::new()).is_empty());
    }
    #[test]
    fn command_keys_use_event_modifiers_and_browser_paste_delivery() {
        let modifiers = egui::Modifiers {
            command: true,
            mac_cmd: true,
            shift: true,
            ..Default::default()
        };
        let (events, prevent) = key_event("a", true, false, modifiers, true).unwrap();
        assert!(prevent);
        assert!(
            matches!(events[0], egui::Event::Key { key: egui::Key::A, modifiers: actual, pressed: true, .. } if actual == modifiers)
        );
        assert!(!key_event("v", true, false, modifiers, true).unwrap().1);
        assert!(key_event("a", true, false, egui::Modifiers::NONE, true).is_none());
        assert!(key_event(" ", true, false, egui::Modifiers::NONE, true).is_none());
    }
}
