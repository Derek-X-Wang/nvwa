//! Session-only protection for the first native Save after accepted creation.
//! Work bytes and the platform's atomic save contract remain unchanged.
use super::{EditorState, PlatformIo, egui};
use nvwa_core::SceneDocument;

#[derive(Clone)]
struct SaveBinding {
    identity: (u64, u64),
    work_json: String,
    path: String,
    destination: String,
    preview: Option<SceneDocument>,
}
impl SaveBinding {
    fn current(editor: &EditorState, path: &str) -> Result<Self, String> {
        Ok(Self {
            identity: editor.file_context_identity(),
            work_json: editor
                .document()
                .ok_or("No document is open")?
                .to_json()
                .map_err(|error| error.to_string())?,
            path: path.into(),
            destination: native_destination(path),
            preview: editor.preview.clone(),
        })
    }

    fn matches(&self, editor: &EditorState, path: &str) -> bool {
        self.preview == editor.preview
            && self.identity == editor.file_context_identity()
            && self.path == path
            && self.destination == native_destination(path)
            && editor
                .document()
                .and_then(|doc| doc.to_json().ok())
                .as_ref()
                == Some(&self.work_json)
    }
}

fn native_destination(path: &str) -> String {
    std::path::absolute(path)
        .unwrap_or_else(|_| path.into())
        .display()
        .to_string()
}

struct PendingNew {
    generation: u64,
    candidate: SceneDocument,
}

#[derive(Default)]
pub(super) struct FirstSave {
    observed_generation: Option<u64>,
    pending_new: Option<PendingNew>,
    required_generation: Option<u64>,
    confirmation: Option<SaveBinding>,
    saving: Option<SaveBinding>,
}

#[derive(Clone, Copy, Default)]
pub(super) enum ConfirmationIntent {
    #[default]
    None,
    Cancel,
    Save,
}

impl FirstSave {
    pub(super) fn sync(&mut self, editor: &EditorState, path: &str) {
        let generation = editor.file_context_identity().0;
        if self
            .observed_generation
            .is_some_and(|previous| previous != generation)
        {
            // A pending New may have published and then been edited before the
            // next UI pass. Protect that new generation even if bytes changed.
            self.required_generation = self.pending_new.take().map(|_| generation);
            self.confirmation = None;
        }
        self.observed_generation = Some(generation);
        if self.pending_new.as_ref().is_some_and(|pending| {
            pending.generation != generation
                || editor.pending_open.as_ref() != Some(&pending.candidate)
        }) {
            // Rejection/cancellation retains the current Work's file context.
            self.pending_new = None;
        }
        if self
            .confirmation
            .as_ref()
            .is_some_and(|binding| !binding.matches(editor, path))
        {
            self.confirmation = None;
        }
    }

    pub(super) fn request_new(
        &mut self,
        editor: &mut EditorState,
        path: &str,
        candidate: SceneDocument,
    ) -> Result<(), String> {
        self.sync(editor, path);
        self.confirmation = None;
        let generation = editor.file_context_identity().0;
        editor.request_open(candidate.clone())?;
        self.pending_new = Some(PendingNew {
            generation,
            candidate,
        });
        self.sync(editor, path);
        Ok(())
    }

    pub(super) fn confirmation_open(&self) -> bool {
        self.confirmation.is_some()
    }

    pub(super) fn dismiss(&mut self) {
        self.confirmation = None;
    }

    pub(super) fn request_save(
        &mut self,
        editor: &EditorState,
        path: &str,
        io: &mut PlatformIo,
    ) -> Result<(), String> {
        self.sync(editor, path);
        if io.busy() {
            return Err("A file operation is already pending".into());
        }
        let binding = SaveBinding::current(editor, path)?;
        if cfg!(not(target_arch = "wasm32")) && self.required_generation == Some(binding.identity.0)
        {
            self.confirmation = Some(binding);
            Ok(())
        } else {
            self.save(binding, io)
        }
    }

    pub(super) fn confirm(
        &mut self,
        editor: &EditorState,
        path: &str,
        io: &mut PlatformIo,
    ) -> Result<(), String> {
        self.sync(editor, path);
        let binding = self
            .confirmation
            .take()
            .ok_or("Work or destination changed; click Save again")?;
        self.save(binding, io)
    }

    fn save(&mut self, binding: SaveBinding, io: &mut PlatformIo) -> Result<(), String> {
        io.request_save(binding.work_json.clone(), &binding.path)?;
        self.saving = Some(binding);
        Ok(())
    }

    /// Only this exact Work/path's own native completion consumes protection.
    /// A stale completion must not announce success for a different Work.
    pub(super) fn saved(&mut self, editor: &EditorState, path: &str, destination: &str) -> bool {
        self.sync(editor, path);
        let Some(binding) = self.saving.take() else {
            return true; // Existing platform callers can also emit save notices.
        };
        if !binding.matches(editor, path) || binding.destination != destination {
            return false;
        }
        if self.required_generation == Some(binding.identity.0) {
            self.required_generation = None;
        }
        true
    }

    pub(super) fn finish_other_io(&mut self) {
        self.saving = None;
    }

    pub(super) fn draw(&self, ctx: &egui::Context) -> ConfirmationIntent {
        let Some(binding) = &self.confirmation else {
            return ConfirmationIntent::None;
        };
        let mut intent = ConfirmationIntent::None;
        let response =
            egui::Modal::new(egui::Id::new("new_character_first_save")).show(ctx, |ui| {
                if ui.is_sizing_pass() {
                    ctx.request_discard("measure first Save confirmation before input");
                }
                ui.set_width(420.0_f32.min((ctx.viewport_rect().width() - 64.0).max(0.0)));
                ui.heading("新人物首次保存 / First save for new character");
                ui.label("在此保存会替换该路径的现有文件。 / Saving here replaces any existing file:");
                egui::ScrollArea::vertical()
                    .max_height(120.0)
                    .show(ui, |ui| {
                        ui.add(
                            egui::Label::new(&binding.destination)
                                .selectable(true)
                                .wrap(),
                        );
                    });
                ui.label("保留旧作品：取消并修改顶部 Work 路径。 / To keep the previous Work, cancel and change the Work path above.");
                ui.horizontal_wrapped(|ui| {
                    if ui.button("取消 / Cancel").clicked() {
                        intent = ConfirmationIntent::Cancel;
                    }
                    if ui
                        .button("确认保存并替换 / Save here and replace")
                        .clicked()
                    {
                        intent = ConfirmationIntent::Save;
                    }
                });
            });
        if response.should_close() {
            ConfirmationIntent::Cancel
        } else {
            intent
        }
    }
}
