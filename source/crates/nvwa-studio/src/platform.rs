//! Platform-only file access. A bounded, single-flight mailbox delivers browser
//! callbacks without a global document or business-state bridge.
use bevy::prelude::Resource;
use std::sync::{Mutex, mpsc};

const MAX_BYTES: u64 = 2 * 1024 * 1024;

#[cfg(any(target_arch = "wasm32", test))]
pub(crate) fn validate_static_work_path(path: &str) -> Result<(), String> {
    if path.is_empty()
        || !path
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-' | b'.' | b'/'))
        || path
            .split('/')
            .any(|part| part.is_empty() || part == "." || part == "..")
    {
        return Err(
            "Work must be a relative static path without traversal, scheme, query or fragment"
                .into(),
        );
    }
    Ok(())
}

#[cfg(any(target_arch = "wasm32", test))]
#[derive(Default)]
struct WorkBytes(Vec<u8>);
#[cfg(any(target_arch = "wasm32", test))]
impl WorkBytes {
    fn next_len(&self, extra: usize) -> Result<usize, String> {
        self.0
            .len()
            .checked_add(extra)
            .filter(|length| *length as u64 <= MAX_BYTES)
            .ok_or_else(|| "Document exceeds the 2 MiB limit".into())
    }
    #[cfg(test)]
    fn append(&mut self, chunk: &[u8]) -> Result<(), String> {
        self.next_len(chunk.len())?;
        self.0.extend_from_slice(chunk);
        Ok(())
    }
    #[cfg(target_arch = "wasm32")]
    fn append_js(&mut self, chunk: &js_sys::Uint8Array) -> Result<(), String> {
        let next = self.next_len(chunk.length() as usize)?;
        let previous = self.0.len();
        self.0.resize(next, 0);
        chunk.copy_to(&mut self.0[previous..]);
        Ok(())
    }
    fn finish(self) -> Result<String, String> {
        String::from_utf8(self.0).map_err(|error| format!("Document must be UTF-8: {error}"))
    }
}

#[derive(Debug, PartialEq, Eq)]
pub enum FileCompletion {
    Opened(String),
    Saved(String),
    #[cfg(any(target_arch = "wasm32", test))]
    DownloadStarted(String),
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

    /// Published work loading only; manual browser Open still uses the picker.
    #[cfg(target_arch = "wasm32")]
    pub fn request_open_static(&mut self, path: &str) -> Result<(), String> {
        use wasm_bindgen::{JsCast, closure::Closure};
        if self.pending {
            return Err("A file operation is already pending".into());
        }
        validate_static_work_path(path)?;
        let window = web_sys::window().ok_or("Browser window unavailable")?;
        let base = window.location().href().map_err(js_error)?;
        let url = web_sys::Url::new_with_base(path, &base).map_err(js_error)?;
        let controller = web_sys::AbortController::new().map_err(js_error)?;
        let request = web_sys::RequestInit::new();
        request.set_mode(web_sys::RequestMode::SameOrigin);
        request.set_redirect(web_sys::RequestRedirect::Error);
        request.set_credentials(web_sys::RequestCredentials::Omit);
        request.set_signal(Some(&controller.signal()));
        let timed_out = std::rc::Rc::new(std::cell::Cell::new(false));
        let timeout_flag = timed_out.clone();
        let timeout_controller = controller.clone();
        let timeout = Closure::<dyn FnMut()>::new(move || {
            timeout_flag.set(true);
            timeout_controller.abort();
        });
        let timer = window
            .set_timeout_with_callback_and_timeout_and_arguments_0(
                timeout.as_ref().unchecked_ref(),
                30_000,
            )
            .map_err(js_error)?;
        let promise = window.fetch_with_str_and_init(&url.href(), &request);
        let sender = self.sender.clone();
        self.pending = true;
        wasm_bindgen_futures::spawn_local(async move {
            let result = read_static_work(promise).await;
            window.clear_timeout_with_handle(timer);
            drop(timeout);
            if result.is_err() {
                controller.abort();
            }
            let result = if timed_out.get() {
                Err("Work request exceeded 30 seconds".into())
            } else {
                result.map(FileCompletion::Opened)
            };
            deliver(&sender, result);
        });
        Ok(())
    }

    #[cfg(not(target_arch = "wasm32"))]
    fn save_impl(&mut self, json: String, path: &str) -> Result<(), String> {
        native_atomic_save(&json, std::path::Path::new(path))?;
        let destination = std::path::absolute(path).unwrap_or_else(|_| path.into());
        self.sender
            .send(Ok(FileCompletion::Saved(destination.display().to_string())))
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
        let file_name = path
            .rsplit('/')
            .next()
            .filter(|s| !s.is_empty())
            .unwrap_or("scene.nvwa.json");
        anchor.set_download(file_name);
        anchor.click();
        web_sys::Url::revoke_object_url(&url).map_err(js_error)?;
        self.sender
            .send(Ok(FileCompletion::DownloadStarted(file_name.into())))
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
async fn read_static_work(promise: js_sys::Promise) -> Result<String, String> {
    use wasm_bindgen::JsCast;
    use wasm_bindgen_futures::JsFuture;
    let response = JsFuture::from(promise)
        .await
        .map_err(js_error)?
        .dyn_into::<web_sys::Response>()
        .map_err(js_error)?;
    if !response.ok() {
        return Err(format!(
            "Work request failed: HTTP {} {}",
            response.status(),
            response.status_text()
        ));
    }
    let stream = response
        .body()
        .ok_or("Work response has no readable body")?;
    let reader = web_sys::ReadableStreamDefaultReader::new(&stream).map_err(js_error)?;
    let result = async {
        let mut bytes = WorkBytes::default();
        loop {
            let value = JsFuture::from(reader.read()).await.map_err(js_error)?;
            // Browser read() returns a dictionary, which has no JS constructor
            // for instanceof checks. Validate the dictionary's fields below.
            let chunk: web_sys::ReadableStreamReadResult = value.unchecked_into();
            match chunk.get_done() {
                Some(true) => break,
                Some(false) => {
                    let value = chunk
                        .get_value()
                        .dyn_into::<js_sys::Uint8Array>()
                        .map_err(js_error)?;
                    bytes.append_js(&value)?;
                }
                None => return Err("Work response stream returned an invalid result".into()),
            }
        }
        bytes.finish()
    }
    .await;
    reader.release_lock();
    result
}

#[cfg(target_arch = "wasm32")]
fn js_error(error: wasm_bindgen::JsValue) -> String {
    // Preserve the complete diagnostic in the console. Player's recovery
    // controls must remain visible when a browser error includes a long stack.
    web_sys::console::error_1(&error);
    let message = js_sys::Reflect::get(&error, &wasm_bindgen::JsValue::from_str("message"))
        .ok()
        .and_then(|value| value.as_string())
        .or_else(|| error.as_string());
    browser_error_message(message.as_deref())
}

#[cfg(any(target_arch = "wasm32", test))]
fn browser_error_message(message: Option<&str>) -> String {
    let message = message
        .and_then(|message| message.lines().find(|line| !line.trim().is_empty()))
        .map(str::trim)
        .unwrap_or("Unexpected browser error");
    let mut characters = message.chars();
    let mut concise: String = characters.by_ref().take(240).collect();
    if characters.next().is_some() {
        concise.push('…');
    }
    format!("Browser file operation failed: {concise}")
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

    #[test]
    fn browser_failure_keeps_message_bounded_without_showing_stack() {
        assert_eq!(
            browser_error_message(Some(
                "Failed to fetch\n    at wasm-function[1234]\n    at player.js:99"
            )),
            "Browser file operation failed: Failed to fetch"
        );
        assert_eq!(
            browser_error_message(None),
            "Browser file operation failed: Unexpected browser error"
        );
        assert_eq!(
            browser_error_message(Some(" \n ")),
            "Browser file operation failed: Unexpected browser error"
        );
        let long = "失".repeat(300);
        let formatted = browser_error_message(Some(&long));
        assert!(formatted.ends_with('…'));
        assert_eq!(
            formatted.chars().count(),
            "Browser file operation failed: ".chars().count() + 241
        );
    }

    #[test]
    fn static_paths_reject_external_traversal_and_encoded_escapes() {
        for path in [
            "works/m1-sequence.nvwa.json",
            "nested-directory/work_1.json",
        ] {
            validate_static_work_path(path).unwrap();
        }
        for path in [
            "",
            "/work.json",
            "//host/work.json",
            "https://host/work.json",
            "../work.json",
            "works/../work.json",
            "./work.json",
            "works//work.json",
            "works/",
            "works/%2e%2e/work.json",
            "works/file.json?x=1",
            "works/file.json#fragment",
            "works\\file.json",
            "works/\nfile.json",
        ] {
            assert!(
                validate_static_work_path(path).is_err(),
                "accepted {path:?}"
            );
        }
    }

    #[test]
    fn streamed_work_enforces_cumulative_limit_before_copy_and_strict_utf8() {
        let mut bytes = WorkBytes::default();
        let chunk = vec![b' '; MAX_BYTES as usize / 2];
        bytes.append(&chunk).unwrap();
        bytes.append(&chunk).unwrap();
        assert_eq!(bytes.0.len(), MAX_BYTES as usize);
        assert!(bytes.append(b"x").is_err());
        assert_eq!(bytes.0.len(), MAX_BYTES as usize);
        assert_eq!(bytes.finish().unwrap().len(), MAX_BYTES as usize);
        let mut invalid = WorkBytes::default();
        invalid.append(&[0xff]).unwrap();
        assert!(invalid.finish().unwrap_err().contains("UTF-8"));
        assert!(WorkBytes::default().next_len(usize::MAX).is_err());
    }

    #[test]
    fn failed_async_completion_releases_mailbox_for_recovery() {
        let path = directory("async-recovery").join("valid.json");
        std::fs::write(&path, "{}").unwrap();
        let mut io = PlatformIo {
            pending: true,
            ..Default::default()
        };
        io.sender
            .send(Err("Work request exceeded 30 seconds".into()))
            .unwrap();
        assert!(io.request_open(path.to_str().unwrap()).is_err());
        assert!(io.poll().unwrap().is_err());
        assert!(!io.busy());
        io.request_open(path.to_str().unwrap()).unwrap();
        assert_eq!(io.poll(), Some(Ok(FileCompletion::Opened("{}".into()))));
    }

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
        assert_eq!(
            io.poll(),
            Some(Ok(FileCompletion::Saved(path.display().to_string())))
        );
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
