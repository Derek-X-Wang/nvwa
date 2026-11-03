#[cfg(not(target_arch = "wasm32"))]
fn main() -> bevy::app::AppExit {
    nvwa_studio::run()
}

#[cfg(target_arch = "wasm32")]
fn main() {}
