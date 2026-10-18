#[cfg(not(target_arch = "wasm32"))]
fn main() -> bevy::app::AppExit {
    b1_accessory_preview::studio_app().run()
}
#[cfg(target_arch = "wasm32")]
fn main() {}
