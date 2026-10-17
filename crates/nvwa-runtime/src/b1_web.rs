//! Bounded browser raw reads. Bevy's default Wasm reader buffers array_buffer()
//! before returning, so use a response stream before authenticating the snapshot.
use wasm_bindgen::JsCast;
use wasm_bindgen_futures::JsFuture;

struct AbortOnDrop(web_sys::AbortController);
impl Drop for AbortOnDrop {
    fn drop(&mut self) {
        self.0.abort();
    }
}
fn error(value: wasm_bindgen::JsValue) -> String {
    format!(
        "invalid_asset: Browser B1 read failed: {}",
        value
            .as_string()
            .unwrap_or_else(|| "browser request or stream error".into())
    )
}
pub(super) async fn read(path: &str, max: usize) -> Result<Vec<u8>, String> {
    let window = web_sys::window().ok_or("invalid_asset: Browser window unavailable")?;
    let base = window.location().href().map_err(error)?;
    let url = web_sys::Url::new_with_base(&format!("assets/{path}"), &base).map_err(error)?;
    let guard = AbortOnDrop(web_sys::AbortController::new().map_err(error)?);
    let request = web_sys::RequestInit::new();
    request.set_mode(web_sys::RequestMode::SameOrigin);
    request.set_redirect(web_sys::RequestRedirect::Error);
    request.set_credentials(web_sys::RequestCredentials::Omit);
    request.set_signal(Some(&guard.0.signal()));
    let response = JsFuture::from(window.fetch_with_str_and_init(&url.href(), &request))
        .await
        .map_err(error)?
        .dyn_into::<web_sys::Response>()
        .map_err(error)?;
    if !response.ok() {
        return Err(format!(
            "{}: {path}: HTTP {}",
            if response.status() == 404 {
                "asset_missing"
            } else {
                "invalid_asset"
            },
            response.status()
        ));
    }
    if response
        .headers()
        .get("content-length")
        .map_err(error)?
        .and_then(|value| value.parse::<u64>().ok())
        .is_some_and(|bytes| bytes > max as u64)
    {
        return Err(format!("invalid_asset: {path} exceeds byte limit"));
    }
    let stream = response
        .body()
        .ok_or("invalid_asset: B1 response body absent")?;
    let reader = web_sys::ReadableStreamDefaultReader::new(&stream).map_err(error)?;
    let result = async {
        let mut bytes = Vec::new();
        loop {
            let value = JsFuture::from(reader.read()).await.map_err(error)?;
            // read() returns a dictionary, not a JavaScript class instance.
            let chunk: web_sys::ReadableStreamReadResult = value.unchecked_into();
            match chunk.get_done() {
                Some(true) => break,
                Some(false) => {
                    let chunk = chunk
                        .get_value()
                        .dyn_into::<js_sys::Uint8Array>()
                        .map_err(error)?;
                    let length = chunk.length() as usize;
                    if bytes
                        .len()
                        .checked_add(length)
                        .is_none_or(|total| total > max)
                    {
                        return Err(format!("invalid_asset: {path} exceeds byte limit"));
                    }
                    // Check the JS chunk length before allocating a Rust copy.
                    bytes.extend(chunk.to_vec());
                }
                None => return Err("invalid_asset: B1 stream returned an invalid result".into()),
            }
        }
        Ok(bytes)
    }
    .await;
    reader.release_lock();
    result
}
