//! Platform-only file access. A bounded, single-flight mailbox delivers browser
//! callbacks without a global document or business-state bridge.
use bevy::prelude::Resource;
use std::sync::{Mutex, mpsc};

const MAX_BYTES: u64 = 2 * 1024 * 1024;

#[derive(Debug, PartialEq, Eq)]
pub enum FileCompletion {
    Opened(String),
    Saved,
}

#[derive(Resource)]
pub struct PlatformIo {
    sender: mpsc::Sender<Result<FileCompletion, String>>,
    receiver: Mutex<mpsc::Receiver<Result<FileCompletion, String>>>,
    pending: bool,
}

impl Default for PlatformIo {
    fn default() -> Self {
        let (sender, receiver) = mpsc::channel();
        Self {
            sender,
            receiver: Mutex::new(receiver),
            pending: false,
        }
    }
}

impl PlatformIo {
    pub fn busy(&self) -> bool {
        self.pending
    }

    pub fn poll(&mut self) -> Option<Result<FileCompletion, String>> {
        let result = match self.receiver.lock() {
            Ok(receiver) => match receiver.try_recv() {
                Ok(value) => Some(value),
                Err(mpsc::TryRecvError::Empty) => None,
                Err(mpsc::TryRecvError::Disconnected) => {
                    Some(Err("File completion channel disconnected".into()))
                }
            },
            Err(_) => Some(Err("File completion mailbox is poisoned".into())),
        };
        if result.is_some() {
            self.pending = false;
        }
        result
    }

    pub fn request_save(&mut self, json: String, path: &str) -> Result<(), String> {
        if self.pending {
            return Err("A file operation is already pending".into());
        }
        if json.len() as u64 > MAX_BYTES {
            return Err("Document exceeds the 2 MiB limit".into());
        }
        self.save_impl(json, path)
    }

    pub fn request_open(&mut self, path: &str) -> Result<(), String> {
        if self.pending {
            return Err("A file operation is already pending".into());
        }
        self.open_impl(path)
    }

    #[cfg(not(target_arch = "wasm32"))]
    fn save_impl(&mut self, json: String, path: &str) -> Result<(), String> {
        native_atomic_save(&json, std::path::Path::new(path))?;
        self.sender
            .send(Ok(FileCompletion::Saved))
            .map_err(|e| e.to_string())?;
        self.pending = true;
        Ok(())
    }

    #[cfg(not(target_arch = "wasm32"))]
    fn open_impl(&mut self, path: &str) -> Result<(), String> {
        use std::io::Read;
        let mut options = std::fs::OpenOptions::new();
        options.read(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.custom_flags(libc::O_NONBLOCK);
        }
        let file = options
            .open(path)
            .map_err(|e| format!("Open {path}: {e}"))?;
        if !file.metadata().map_err(|e| e.to_string())?.is_file() {
            return Err("Only regular document files are supported".into());
        }
        let mut bytes = Vec::new();
        file.take(MAX_BYTES + 1)
            .read_to_end(&mut bytes)
            .map_err(|e| format!("Read {path}: {e}"))?;
        if bytes.len() as u64 > MAX_BYTES {
            return Err("Document exceeds the 2 MiB limit".into());
        }
        let json = String::from_utf8(bytes).map_err(|e| format!("Document must be UTF-8: {e}"))?;
        self.sender
            .send(Ok(FileCompletion::Opened(json)))
            .map_err(|e| e.to_string())?;
        self.pending = true;
        Ok(())
    }

    #[cfg(target_arch = "wasm32")]
    fn save_impl(&mut self, json: String, path: &str) -> Result<(), String> {
        use wasm_bindgen::{JsCast, JsValue};
        let window = web_sys::window().ok_or("Browser window unavailable")?;
        let document = window.document().ok_or("Browser document unavailable")?;
        let parts = js_sys::Array::new();
        parts.push(&JsValue::from_str(&json));
        let options = web_sys::BlobPropertyBag::new();
        options.set_type("application/json");
        let blob =
            web_sys::Blob::new_with_str_sequence_and_options(&parts, &options).map_err(js_error)?;
        let url = web_sys::Url::create_object_url_with_blob(&blob).map_err(js_error)?;
        let anchor: web_sys::HtmlAnchorElement = document
            .create_element("a")
            .map_err(js_error)?
            .dyn_into()
            .map_err(|element: web_sys::Element| js_error(element.into()))?;
        anchor.set_href(&url);
        anchor.set_download(
            path.rsplit('/')
                .next()
                .filter(|s| !s.is_empty())
                .unwrap_or("scene.nvwa.json"),
        );
        anchor.click();
        web_sys::Url::revoke_object_url(&url).map_err(js_error)?;
        self.sender
            .send(Ok(FileCompletion::Saved))
            .map_err(|e| e.to_string())?;
        self.pending = true;
        Ok(())
    }

    #[cfg(target_arch = "wasm32")]
    fn open_impl(&mut self, _path: &str) -> Result<(), String> {
        use wasm_bindgen::{JsCast, closure::Closure};
        let document = web_sys::window()
            .and_then(|w| w.document())
            .ok_or("Browser document unavailable")?;
        let input: web_sys::HtmlInputElement = document
            .create_element("input")
            .map_err(js_error)?
            .dyn_into()
            .map_err(|element: web_sys::Element| js_error(element.into()))?;
        input.set_type("file");
        input.set_accept(".json,application/json");
        input.set_attribute("hidden", "").map_err(js_error)?;
        document
            .body()
            .ok_or("Browser body unavailable")?
            .append_child(&input)
            .map_err(js_error)?;
        let selected = input.clone();
        let sender = self.sender.clone();
        let callback = Closure::once_into_js(move |_event: web_sys::Event| {
            selected.set_onchange(None);
            if let Err(error) = js_sys::Reflect::set(
                selected.as_ref(),
                &"oncancel".into(),
                &wasm_bindgen::JsValue::NULL,
            ) {
                web_sys::console::error_1(&error);
            }
            selected.remove();
            let file = selected.files().and_then(|files| files.get(0));
            let Some(file) = file else {
                deliver(&sender, Err("File selection cancelled".into()));
                return;
            };
            if file.size() > MAX_BYTES as f64 {
                deliver(&sender, Err("Document exceeds the 2 MiB limit".into()));
                return;
            }
            wasm_bindgen_futures::spawn_local(async move {
                let result = wasm_bindgen_futures::JsFuture::from(file.text())
                    .await
                    .map_err(js_error)
                    .and_then(|value| {
                        value
                            .as_string()
                            .ok_or("Selected file is not UTF-8 text".into())
                    });
                let result = result.and_then(|json| {
                    if json.len() as u64 > MAX_BYTES {
                        Err("Document exceeds the 2 MiB limit".into())
                    } else {
                        Ok(FileCompletion::Opened(json))
                    }
                });
                deliver(&sender, result);
            });
        });
        input.set_onchange(Some(callback.unchecked_ref()));
        js_sys::Reflect::set(input.as_ref(), &"oncancel".into(), &callback).map_err(js_error)?;
        self.pending = true;
        input.click();
        Ok(())
    }
}

#[cfg(target_arch = "wasm32")]
fn js_error(error: wasm_bindgen::JsValue) -> String {
    format!("Browser file operation failed: {error:?}")
}

#[cfg(target_arch = "wasm32")]
fn deliver(
    sender: &mpsc::Sender<Result<FileCompletion, String>>,
    value: Result<FileCompletion, String>,
) {
    if let Err(error) = sender.send(value) {
        web_sys::console::error_1(&error.to_string().into());
    }
}

#[cfg(not(target_arch = "wasm32"))]
fn native_atomic_save(json: &str, path: &std::path::Path) -> Result<(), String> {
    use std::io::Write;
    let nonce = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|e| e.to_string())?
        .as_nanos();
    let parent = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(std::path::Path::new("."));
    let temp = parent.join(format!(".nvwa-save-{}-{nonce}.tmp", std::process::id()));
    let mut file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temp)
        .map_err(|e| format!("Create temporary save: {e}"))?;
    let result = file
        .write_all(json.as_bytes())
        .and_then(|()| file.sync_all())
        .and_then(|()| std::fs::rename(&temp, path));
    if let Err(error) = result {
        let cleanup = std::fs::remove_file(&temp);
        return Err(match cleanup {
            Ok(()) => format!("Save {}: {error}", path.display()),
            Err(cleanup_error) => format!(
                "Save {}: {error}; temporary cleanup failed: {cleanup_error}",
                path.display()
            ),
        });
    }
    Ok(())
}

#[cfg(all(test, not(target_arch = "wasm32")))]
mod tests {
    use super::*;

    fn directory(name: &str) -> std::path::PathBuf {
        let dir = std::env::temp_dir().join(format!("nvwa-platform-{}-{name}", std::process::id()));
        std::fs::create_dir_all(&dir).expect("test-owned directory");
        dir
    }

    #[test]
    fn save_does_not_truncate_unrelated_predictable_sibling() {
        let dir = directory("safe-save");
        let path = dir.join("scene.json");
        let sibling = dir.join("scene.nvwa.json.tmp");
        std::fs::write(&sibling, "unrelated content").expect("sibling fixture");
        let mut io = PlatformIo::default();
        io.request_save("{}".into(), path.to_str().expect("path"))
            .expect("save");
        assert_eq!(io.poll(), Some(Ok(FileCompletion::Saved)));
        assert_eq!(std::fs::read_to_string(path).expect("save bytes"), "{}");
        assert_eq!(
            std::fs::read_to_string(sibling).expect("sibling bytes"),
            "unrelated content"
        );
    }

    #[test]
    fn empty_open_is_an_opened_payload_and_operations_are_single_flight() {
        let path = directory("empty-open").join("empty.json");
        std::fs::write(&path, "").expect("empty fixture");
        let mut io = PlatformIo::default();
        io.request_open(path.to_str().expect("path")).expect("open");
        assert!(
            io.request_save("{}".into(), path.to_str().expect("path"))
                .is_err()
        );
        assert_eq!(io.poll(), Some(Ok(FileCompletion::Opened(String::new()))));
        assert!(!io.busy());
        assert_eq!(std::fs::read_to_string(path).expect("empty bytes"), "");
    }

    #[test]
    fn oversized_and_nonregular_inputs_are_rejected_before_unbounded_read() {
        let dir = directory("bounded-open");
        let path = dir.join("oversized.json");
        std::fs::File::create(&path)
            .expect("fixture")
            .set_len(MAX_BYTES + 1)
            .expect("sparse size");
        let mut io = PlatformIo::default();
        assert!(
            io.request_open(path.to_str().expect("path"))
                .expect_err("size rejection")
                .contains("2 MiB")
        );
        assert!(io.request_open(dir.to_str().expect("path")).is_err());
        if std::path::Path::new("/dev/zero").exists() {
            assert!(
                io.request_open("/dev/zero")
                    .expect_err("device rejection")
                    .contains("regular")
            );
        }
    }

    #[cfg(unix)]
    #[test]
    fn fifo_without_writer_is_rejected_without_blocking_ui() {
        let path = directory("fifo-open").join("pipe.json");
        let result = std::process::Command::new("mkfifo")
            .arg(&path)
            .status()
            .expect("create FIFO");
        assert!(result.success());
        let (sender, receiver) = std::sync::mpsc::channel();
        let worker = std::thread::spawn(move || {
            let mut io = PlatformIo::default();
            sender
                .send(io.request_open(path.to_str().expect("path")))
                .expect("result");
        });
        let error = receiver
            .recv_timeout(std::time::Duration::from_secs(2))
            .expect("FIFO import must return without a writer")
            .expect_err("FIFO rejected");
        assert!(error.contains("regular"));
        worker.join().expect("worker exits");
    }
}
