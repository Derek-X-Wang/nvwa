//! Throwaway startup geometry helper; every plugin and UI comes from production.
use bevy::{prelude::*, window::PrimaryWindow};

fn main() -> AppExit {
    // Production consumes the original process arguments, including --work.
    let mut app = nvwa_studio::build_app();
    {
        let world = app.world_mut();
        let mut query = world.query_filtered::<&mut Window, With<PrimaryWindow>>();
        let mut window = query
            .single_mut(world)
            .expect("native viewport harness requires exactly one PrimaryWindow before app.run()");
        window.resolution.set(1024.0, 768.0);
        assert_eq!(window.resolution.width(), 1024.0);
        assert_eq!(window.resolution.height(), 768.0);
    }
    app.run()
}
