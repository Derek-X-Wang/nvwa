//! Portable presentation settings. Colors are sRGB; angles are degrees.
use crate::{CoreError, Result, finite};
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StageQuality {
    Low,
    Balanced,
    High,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StageLight {
    pub illuminance_lux: f32,
    pub color_srgb: [f32; 3],
    /// Position of the light around the subject. Zero faces the subject from +Z.
    pub azimuth_degrees: f32,
    /// Height of the light above the horizon.
    pub elevation_degrees: f32,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StageAmbient {
    /// Bevy ambient brightness, in cd/m² before color multiplication.
    pub brightness: f32,
    pub color_srgb: [f32; 3],
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StageFloor {
    pub visible: bool,
    pub color_srgb: [f32; 3],
    /// Enables key-light shadow maps.
    /// Low quality overrides this request. Fill-light shadows stay off.
    pub shadows: bool,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StageCamera {
    pub azimuth_degrees: f32,
    pub elevation_degrees: f32,
    /// Distance in character-relative units, multiplied by character scale at render time.
    pub distance: f32,
    /// Target height in character-relative units. The floor remains at world y=0.
    pub target_height: f32,
    /// Vertical field of view.
    pub fov_degrees: f32,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StageSettings {
    pub key_light: StageLight,
    pub fill_light: StageLight,
    pub ambient: StageAmbient,
    pub background_color_srgb: [f32; 3],
    pub floor: StageFloor,
    pub camera: StageCamera,
    pub quality: StageQuality,
}

pub(crate) fn bounded(value: f32, min: f32, max: f32, name: &str) -> Result<()> {
    finite(value, name)?;
    if !(min..=max).contains(&value) {
        return Err(CoreError::new(
            "out_of_range",
            format!("{name} must be between {min} and {max}"),
        ));
    }
    Ok(())
}
fn color(value: [f32; 3], name: &str) -> Result<()> {
    for channel in value {
        bounded(channel, 0.0, 1.0, name)?;
    }
    Ok(())
}
impl StageLight {
    fn validate(&self) -> Result<()> {
        bounded(
            self.illuminance_lux,
            0.0,
            100_000.0,
            "light illuminance_lux",
        )?;
        color(self.color_srgb, "light color_srgb")?;
        bounded(self.azimuth_degrees, -180.0, 180.0, "light azimuth_degrees")?;
        bounded(self.elevation_degrees, 5.0, 89.0, "light elevation_degrees")
    }
}
impl StageCamera {
    pub fn full_body() -> Self {
        Self {
            azimuth_degrees: 16.0,
            elevation_degrees: 8.0,
            distance: 3.8,
            target_height: 0.95,
            fov_degrees: 36.0,
        }
    }
    pub fn detail() -> Self {
        Self {
            azimuth_degrees: 8.0,
            elevation_degrees: 3.0,
            distance: 1.25,
            target_height: 1.65,
            fov_degrees: 30.0,
        }
    }
    pub fn validate(&self) -> Result<()> {
        bounded(
            self.azimuth_degrees,
            -180.0,
            180.0,
            "camera azimuth_degrees",
        )?;
        bounded(
            self.elevation_degrees,
            -20.0,
            80.0,
            "camera elevation_degrees",
        )?;
        bounded(self.distance, 0.35, 20.0, "camera distance")?;
        bounded(self.target_height, 0.0, 4.0, "camera target_height")?;
        bounded(self.fov_degrees, 15.0, 75.0, "camera fov_degrees")
    }
}
impl Default for StageSettings {
    fn default() -> Self {
        Self::white_studio()
    }
}
impl StageSettings {
    pub fn white_studio() -> Self {
        Self {
            key_light: StageLight {
                illuminance_lux: 10_000.0,
                color_srgb: [1.0, 0.94, 0.86],
                azimuth_degrees: -35.0,
                elevation_degrees: 42.0,
            },
            fill_light: StageLight {
                illuminance_lux: 3_000.0,
                color_srgb: [0.80, 0.89, 1.0],
                azimuth_degrees: 55.0,
                elevation_degrees: 28.0,
            },
            ambient: StageAmbient {
                brightness: 180.0,
                color_srgb: [1.0; 3],
            },
            background_color_srgb: [0.88, 0.90, 0.93],
            floor: StageFloor {
                visible: true,
                color_srgb: [0.72, 0.75, 0.80],
                shadows: true,
            },
            camera: StageCamera::full_body(),
            quality: StageQuality::Balanced,
        }
    }
    pub fn black_space() -> Self {
        Self {
            key_light: StageLight {
                illuminance_lux: 12_000.0,
                color_srgb: [1.0, 0.92, 0.80],
                azimuth_degrees: -42.0,
                elevation_degrees: 38.0,
            },
            fill_light: StageLight {
                illuminance_lux: 4_500.0,
                color_srgb: [0.65, 0.80, 1.0],
                azimuth_degrees: 115.0,
                elevation_degrees: 35.0,
            },
            ambient: StageAmbient {
                brightness: 95.0,
                color_srgb: [0.80, 0.88, 1.0],
            },
            background_color_srgb: [0.008, 0.011, 0.018],
            floor: StageFloor {
                visible: true,
                color_srgb: [0.035, 0.045, 0.065],
                shadows: true,
            },
            ..Self::white_studio()
        }
    }
    pub fn validate(&self) -> Result<()> {
        self.key_light.validate()?;
        self.fill_light.validate()?;
        bounded(self.ambient.brightness, 0.0, 2000.0, "ambient brightness")?;
        color(self.ambient.color_srgb, "ambient color_srgb")?;
        color(self.background_color_srgb, "background_color_srgb")?;
        color(self.floor.color_srgb, "floor color_srgb")?;
        self.camera.validate()
    }
}
