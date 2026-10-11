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
    fn preedit(&mut self, text: String) -> Vec<egui::Event> {
        self.composing = true;
        vec![egui::Event::Ime(egui::ImeEvent::Preedit {
            text,
            active_range_chars: None,
        })]
    }
    fn end(&mut self, text: String) -> Vec<egui::Event> {
        self.composing = false;
        self.followup = Some((text.clone(), false));
        vec![egui::Event::Ime(egui::ImeEvent::Commit(text))]
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
        if std::mem::take(&mut self.composing) {
            vec![egui::Event::Ime(egui::ImeEvent::Commit(String::new()))]
        } else {
            Vec::new()
        }
    }
}

/// Only this explicit field opts into the desktop proxy and its composition transaction.
fn work_id() -> egui::Id {
    egui::Id::new("nvwa-work-path")
}

#[derive(Clone)]
struct CompositionSnapshot {
    committed: String,
    preview: String,
    cursor: egui::text_edit::TextEditState,
}

fn snapshot_id() -> egui::Id {
    work_id().with("composition")
}

/// egui temporarily places preedit in the caller's String. Guard that same String
/// until commit; no second Work model or editing algorithm is introduced.
pub(super) fn work_text_edit(ui: &mut egui::Ui, text: &mut String, width: f32) {
    finish_work_text(ui.ctx(), text);
    let id = work_id();
    let owns = ui.ctx().memory(|m| m.focused()) == Some(id);
    let events = ui.input(|input| input.events.clone());
    // DOM callbacks can batch a commit and the next composition in one pass.
    // Follow their order; a terminal event cannot finalize a later preedit.
    let mut preedit = None;
    let mut finalized = false;
    let mut rebase = false;
    if owns {
        for event in &events {
            match event {
                // The pinned singleline IME handler ignores CR/LF payloads.
                egui::Event::Ime(egui::ImeEvent::Preedit { text, .. })
                | egui::Event::Ime(egui::ImeEvent::Commit(text))
                    if text == "\n" || text == "\r" => {}
                egui::Event::Ime(egui::ImeEvent::Preedit { text, .. }) if !text.is_empty() => {
                    preedit = Some(text);
                    rebase |= finalized;
                    finalized = false;
                }
                egui::Event::Ime(egui::ImeEvent::Commit(_))
                | egui::Event::Ime(egui::ImeEvent::Preedit { .. })
                | egui::Event::Text(_)
                | egui::Event::Paste(_)
                | egui::Event::Cut
                | egui::Event::Key { pressed: true, .. } => {
                    preedit = None;
                    finalized = true;
                }
                _ => {}
            }
        }
    }
    let existing = ui
        .ctx()
        .data_mut(|data| data.get_temp::<CompositionSnapshot>(snapshot_id()));
    if preedit.is_some() && existing.is_none() {
        let old = egui::text_edit::TextEditState::load(ui.ctx(), id).unwrap_or_default();
        // The undoer is internally shared, so copy it into a fresh state's owner.
        let mut cursor = egui::text_edit::TextEditState::default();
        cursor.cursor = old.cursor;
        cursor.set_undoer(old.undoer());
        ui.ctx().data_mut(|data| {
            data.insert_temp(
                snapshot_id(),
                CompositionSnapshot {
                    committed: text.clone(),
                    preview: text.clone(),
                    cursor,
                },
            )
        });
    }
    let output = egui::TextEdit::singleline(&mut *text)
        .id(id)
        .desired_width(width)
        .show(ui);
    if finalized && output.response.changed() {
        ui.ctx()
            .data_mut(|data| data.remove::<CompositionSnapshot>(snapshot_id()));
    } else if let Some(mut snapshot) = ui
        .ctx()
        .data_mut(|data| data.get_temp::<CompositionSnapshot>(snapshot_id()))
    {
        if rebase
            && let Some(preedit) = preedit
            && let Some(range) = output.state.cursor.char_range()
            && egui::TextBuffer::char_range(text, range.as_sorted_char_range()) == preedit
        {
            // egui identifies the actual composing region. Remove only that
            // region from the rollback baseline, preserving prior commits/edits.
            // Keep the isolated pre-session undoer, never its preedit snapshots.
            snapshot.committed = text.clone();
            egui::TextBuffer::delete_char_range(
                &mut snapshot.committed,
                range.as_sorted_char_range(),
            );
            let cursor = egui::text::CCursorRange::one(range.sorted_cursors()[0]);
            snapshot.cursor.cursor.set_char_range(Some(cursor));
            let mut undoer = snapshot.cursor.undoer();
            undoer.feed_state(
                ui.input(|input| input.time),
                &(cursor, snapshot.committed.clone()),
            );
            snapshot.cursor.set_undoer(undoer);
        }
        snapshot.preview = text.clone();
        ui.ctx()
            .data_mut(|data| data.insert_temp(snapshot_id(), snapshot));
    }
    finish_work_text(ui.ctx(), text);
}

/// Also run after the rest of the UI, before Open/Save can capture this String.
pub(super) fn finish_work_text(ctx: &egui::Context, text: &mut String) {
    let Some(mut snapshot) =
        ctx.data_mut(|data| data.get_temp::<CompositionSnapshot>(snapshot_id()))
    else {
        return;
    };
    if *text != snapshot.preview {
        // A loaded/new path or an edit outside this composition owns the current String.
        ctx.data_mut(|data| data.remove::<CompositionSnapshot>(snapshot_id()));
        return;
    }
    if ctx.memory(|memory| memory.focused()) == Some(work_id()) {
        return;
    }
    *text = snapshot.committed;
    if let Some(mut range) = snapshot.cursor.cursor.char_range() {
        let count = egui::text::CharIndex(text.chars().count());
        range.primary.index = range.primary.index.min(count);
        range.secondary.index = range.secondary.index.min(count);
        snapshot.cursor.cursor.set_char_range(Some(range));
    }
    snapshot.cursor.store(ctx, work_id());
    ctx.data_mut(|data| data.remove::<CompositionSnapshot>(snapshot_id()));
}

fn key_event(
    key: &str,
    pressed: bool,
    repeat: bool,
    modifiers: egui::Modifiers,
) -> Option<(Vec<egui::Event>, bool)> {
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
        "a" | "A" if modifiers.command => egui::Key::A,
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
                if let Some((events, prevent)) =
                    key_event(&event.key(), name == "keydown", event.repeat(), modifiers)
                {
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
    fn apply(ctx: &egui::Context, text: &mut String, id: egui::Id, events: Vec<egui::Event>) {
        let mut output = ctx.run_ui(
            egui::RawInput {
                events,
                ..Default::default()
            },
            |ui| {
                egui::CentralPanel::default().show(ui, |ui| {
                    egui::TextEdit::singleline(text).id(id).show(ui);
                });
            },
        );
        output.textures_delta.clear();
    }
    fn work_frame(
        ctx: &egui::Context,
        text: &mut String,
        next: &mut String,
        events: Vec<egui::Event>,
        surrender_after_draw: bool,
    ) {
        let mut output = ctx.run_ui(
            egui::RawInput {
                events,
                ..Default::default()
            },
            |ui| {
                egui::CentralPanel::default().show(ui, |ui| {
                    work_text_edit(ui, text, 220.0);
                    let next_id = egui::Id::new("next-work-regression");
                    egui::TextEdit::singleline(next).id(next_id).show(ui);
                    if surrender_after_draw {
                        ui.memory_mut(|memory| memory.request_focus(next_id));
                    }
                    // This is also the Open/Save capture seam in the real Studio UI.
                    finish_work_text(ui.ctx(), text);
                });
            },
        );
        output.textures_delta.clear();
    }
    fn work_fixture() -> (egui::Context, String, String, TextDelivery) {
        let ctx = egui::Context::default();
        ctx.memory_mut(|memory| memory.request_focus(work_id()));
        let mut text = "path".to_owned();
        let mut next = "other".to_owned();
        work_frame(&ctx, &mut text, &mut next, vec![], false);
        (ctx, text, next, TextDelivery::default())
    }
    #[test]
    fn work_focus_surrender_rolls_back_before_path_capture_and_restores_cursor() {
        let (ctx, mut text, mut next, mut delivery) = work_fixture();
        delivery.begin();
        work_frame(
            &ctx,
            &mut text,
            &mut next,
            delivery.preedit("nv".into()),
            false,
        );
        assert_eq!(text, "pathnv");
        work_frame(&ctx, &mut text, &mut next, vec![], true);
        assert_eq!(text, "path");
        assert_eq!(next, "other");
        let state = egui::text_edit::TextEditState::load(&ctx, work_id()).unwrap();
        let range = state.cursor.char_range().unwrap();
        assert_eq!(range.primary.index, egui::text::CharIndex(4));
        assert_eq!(range.secondary.index, egui::text::CharIndex(4));
        assert!(
            ctx.data_mut(|data| data.get_temp::<CompositionSnapshot>(snapshot_id()))
                .is_none()
        );
    }
    #[test]
    fn work_batched_commit_then_new_preedit_preserves_intermediate_commit() {
        let (ctx, mut text, mut next, mut delivery) = work_fixture();
        delivery.begin();
        work_frame(
            &ctx,
            &mut text,
            &mut next,
            delivery.preedit("nv".into()),
            false,
        );
        let mut events = delivery.end("女娲".into());
        delivery.begin();
        events.extend(delivery.preedit("hao".into()));
        work_frame(&ctx, &mut text, &mut next, events, false);
        assert_eq!(text, "path女娲hao");
        work_frame(&ctx, &mut text, &mut next, vec![], true);
        assert_eq!(
            text, "path女娲",
            "rollback removes only the new uncommitted composition"
        );
        assert_eq!(next, "other");
    }
    #[test]
    fn work_commit_before_focus_surrender_remains_committed() {
        let (ctx, mut text, mut next, mut delivery) = work_fixture();
        delivery.begin();
        work_frame(
            &ctx,
            &mut text,
            &mut next,
            delivery.preedit("nv".into()),
            false,
        );
        work_frame(
            &ctx,
            &mut text,
            &mut next,
            delivery.end("女娲".into()),
            true,
        );
        assert_eq!(text, "path女娲");
        finish_work_text(&ctx, &mut text);
        assert_eq!(
            text, "path女娲",
            "cleanup must not undo committed characters"
        );
    }
    #[test]
    fn work_ordinary_edit_and_new_loaded_path_are_not_replaced_by_snapshot() {
        let (ctx, mut text, mut next, mut delivery) = work_fixture();
        delivery.begin();
        work_frame(
            &ctx,
            &mut text,
            &mut next,
            delivery.preedit("nv".into()),
            false,
        );
        work_frame(
            &ctx,
            &mut text,
            &mut next,
            vec![egui::Event::Text("x".into())],
            true,
        );
        assert_eq!(text, "pathx", "ordinary edit remains canonical");
        ctx.memory_mut(|memory| memory.request_focus(work_id()));
        work_frame(&ctx, &mut text, &mut next, vec![], false);
        delivery.begin();
        work_frame(
            &ctx,
            &mut text,
            &mut next,
            delivery.preedit("stale".into()),
            false,
        );
        text = "newly-loaded女娲.json".into();
        ctx.memory_mut(|memory| memory.surrender_focus(work_id()));
        finish_work_text(&ctx, &mut text);
        assert_eq!(text, "newly-loaded女娲.json");
    }
    #[test]
    fn work_clipboard_uses_singleline_paste_semantics_after_command_selection() {
        let (ctx, mut text, mut next, mut delivery) = work_fixture();
        let modifiers = egui::Modifiers {
            command: true,
            mac_cmd: true,
            ..Default::default()
        };
        work_frame(
            &ctx,
            &mut text,
            &mut next,
            key_event("a", true, false, modifiers).unwrap().0,
            false,
        );
        work_frame(
            &ctx,
            &mut text,
            &mut next,
            delivery.paste("one\r\ntwo\nthree".into()),
            false,
        );
        assert_eq!(text, "one  two three");
        assert!(!text.contains(['\r', '\n']));
        work_frame(
            &ctx,
            &mut text,
            &mut next,
            delivery.input("one\r\ntwo\nthree".into(), "insertFromPaste", false),
            false,
        );
        assert_eq!(
            text, "one  two three",
            "clipboard followup must not duplicate"
        );
    }
    #[test]
    fn delivered_composition_replaces_preedit_in_real_egui_once_and_cancel_removes_it() {
        let ctx = egui::Context::default();
        let id = egui::Id::new("web-input-regression");
        ctx.memory_mut(|m| m.request_focus(id));
        let mut text = String::new();
        apply(&ctx, &mut text, id, Vec::new());
        let mut state = TextDelivery::default();
        state.begin();
        apply(&ctx, &mut text, id, state.preedit("nv".into()));
        apply(&ctx, &mut text, id, state.end("女娲".into()));
        apply(
            &ctx,
            &mut text,
            id,
            state.input("女娲".into(), "insertFromComposition", false),
        );
        assert_eq!(text, "女娲");
        state.begin();
        apply(&ctx, &mut text, id, state.preedit("cancel".into()));
        apply(&ctx, &mut text, id, state.cancel());
        assert_eq!(text, "女娲", "cancel must remove only uncommitted preedit");
    }
    #[test]
    fn composition_commit_and_followup_input_deliver_once() {
        let mut state = TextDelivery::default();
        state.begin();
        assert!(matches!(
            state.preedit("nv".into())[0],
            egui::Event::Ime(egui::ImeEvent::Preedit { .. })
        ));
        assert!(
            state
                .input("nv".into(), "insertCompositionText", true)
                .is_empty()
        );
        assert!(
            matches!(&state.end("女娲".into())[0], egui::Event::Ime(egui::ImeEvent::Commit(text)) if text == "女娲")
        );
        assert!(
            state
                .input("女娲".into(), "insertFromComposition", false)
                .is_empty()
        );
        state.begin();
        assert_eq!(
            state.end("女娲".into()).len(),
            1,
            "a new identical composition must commit again"
        );
    }
    #[test]
    fn cancellation_and_paste_do_not_duplicate_or_leave_preedit() {
        let mut state = TextDelivery::default();
        state.begin();
        state.preedit("nv".into());
        assert!(
            matches!(&state.cancel()[0], egui::Event::Ime(egui::ImeEvent::Commit(text)) if text.is_empty())
        );
        assert!(state.cancel().is_empty());
        assert_eq!(state.paste("sentinel".into()).len(), 1);
        assert!(
            state
                .input("sentinel".into(), "insertFromPaste", false)
                .is_empty()
        );
        assert_eq!(state.input("sentinel".into(), "insertText", false).len(), 1);
    }
    #[test]
    fn command_selection_uses_event_modifiers_and_paste_keeps_browser_delivery() {
        let modifiers = egui::Modifiers {
            command: true,
            mac_cmd: true,
            shift: true,
            ..Default::default()
        };
        let (events, prevent) = key_event("a", true, false, modifiers).unwrap();
        assert!(prevent);
        assert!(
            matches!(events[0], egui::Event::Key { key: egui::Key::A, modifiers: actual, pressed: true, .. } if actual == modifiers)
        );
        assert!(!key_event("v", true, false, modifiers).unwrap().1);
        assert!(
            key_event("a", true, false, egui::Modifiers::NONE).is_none(),
            "ordinary text belongs to input"
        );
        assert!(key_event(" ", true, false, egui::Modifiers::NONE).is_none());
    }
}
