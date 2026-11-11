//! Bounded B1 identity and byte validation. No filesystem or renderer dependency.
use crate::{CharacterProfile, ClipSpec, CoreError, ParameterSpec, Result, parse_json};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub const B1_RUNNING_PROFILE_ID: &str = "nvwa-mpfb-b1-running-v1";
pub const B1_RUN_CLIP_ID: &str = "b1_run_forward_authored_v1";
pub const B1_PROFILE_ID: &str = "nvwa-mpfb-b1-v1";
pub const B1_MOTION_PROFILE_ID: &str = "nvwa-mpfb-b1-motion-v1";
pub const B1_MOTION_CLIPS: [&str; 2] = ["b1_arm_rehearsal_v1", "b1_knee_flex_v1"];
pub const B1_MOTION_DURATION_SECONDS: f32 = 4.0;
pub const B1_ASSET_ID: &str = "mpfb-hm08-game-engine-female-sportsuit01-v1";
pub const B1_ASSET_PATH: &str = "characters/mpfb-b1-v1/manifest.json";
pub const B1_ASSET_MANIFEST_SHA256: &str =
    "abcdbc26e03431c740c5fce98de22902089f985823a3c655db2416d042d62b18";
pub const B1_ASSET_MANIFEST_BYTES: &[u8] =
    include_bytes!("../../../assets/characters/mpfb-b1-v1/manifest.json");
pub const B1_CHARACTER_PROFILE_ID: &str = "nvwa-mpfb-b1-motion-v2";
pub const B1_V2_ASSET_ID: &str = "mpfb-hm08-game-engine-female-sportsuit01-v2";
pub const B1_V2_ASSET_PATH: &str = "characters/mpfb-b1-v2/manifest.json";
pub const B1_V2_ASSET_MANIFEST_SHA256: &str =
    "15834b6bea9bc7daff2d7189e15a66e044130c3b6b4cc75f4b3e508a4e97f3f4";
pub const B1_V2_ASSET_MANIFEST_BYTES: &[u8] =
    include_bytes!("../../../assets/characters/mpfb-b1-v2/manifest.json");

pub const B1_CONTOUR_PROFILE_ID: &str = "nvwa-mpfb-b1-motion-v3";
pub const B1_V3_ASSET_ID: &str = "mpfb-hm08-game-engine-female-sportsuit01-v3";
pub const B1_V3_ASSET_PATH: &str = "characters/mpfb-b1-v3/manifest.json";
pub const B1_V3_ASSET_MANIFEST_SHA256: &str =
    "e4bd47f3f3cf3ef38fd3400bfd5127b7ade52b630cef823f00bba939262796c3";
pub const B1_V3_ASSET_MANIFEST_BYTES: &[u8] =
    include_bytes!("../../../assets/characters/mpfb-b1-v3/manifest.json");

pub const B1_LOWER_CONTOUR_PROFILE_ID: &str = "nvwa-mpfb-b1-motion-v4";
pub const B1_V4_ASSET_ID: &str = "mpfb-hm08-game-engine-female-sportsuit01-v4";
pub const B1_V4_ASSET_PATH: &str = "characters/mpfb-b1-v4/manifest.json";
pub const B1_V4_ASSET_MANIFEST_SHA256: &str =
    "6b11cb9fc53158bf5673d0c5e1636d30d6e2347f4f51ce34f5fea8650baec090";
pub const B1_V4_ASSET_MANIFEST_BYTES: &[u8] =
    include_bytes!("../../../assets/characters/mpfb-b1-v4/manifest.json");

pub const B1_WAIST_PROFILE_ID: &str = "nvwa-mpfb-b1-waist-v1";
pub const B1_V5_ASSET_ID: &str = "mpfb-hm08-game-engine-female-sportsuit01-v5";
pub const B1_V5_ASSET_PATH: &str = "characters/mpfb-b1-v5/manifest.json";
pub const B1_V5_ASSET_MANIFEST_SHA256: &str =
    "9513686fe1a2d24bf64cd067ce1a83d615e7fff30225804ee215991967ff95a2";
pub const B1_V5_ASSET_MANIFEST_BYTES: &[u8] =
    include_bytes!("../../../assets/characters/mpfb-b1-v5/manifest.json");

pub const B1_LEG_PROFILE_ID: &str = "nvwa-mpfb-b1-legs-v1";
pub const B1_V6_ASSET_ID: &str = "mpfb-hm08-game-engine-female-sportsuit01-v6";
pub const B1_V6_ASSET_PATH: &str = "characters/mpfb-b1-v6/manifest.json";
pub const B1_V6_ASSET_MANIFEST_SHA256: &str =
    "240e72755d1f80f738d1979bf5edd1f655918196726bf4797a2689209cf4624c";
pub const B1_V6_ASSET_MANIFEST_BYTES: &[u8] =
    include_bytes!("../../../assets/characters/mpfb-b1-v6/manifest.json");

pub const B1_UPPER_BODY_PROFILE_ID: &str = "nvwa-mpfb-b1-upper-body-v1";
pub const B1_V7_ASSET_ID: &str = "mpfb-hm08-game-engine-female-sportsuit01-v7";
pub const B1_V7_ASSET_PATH: &str = "characters/mpfb-b1-v7/manifest.json";
pub const B1_V7_ASSET_MANIFEST_SHA256: &str =
    "18c8a5a085df11093f2c3218c0c51f3ad882c4653331fb777afb8610a2bae0c3";
pub const B1_V7_ASSET_MANIFEST_BYTES: &[u8] =
    include_bytes!("../../../assets/characters/mpfb-b1-v7/manifest.json");

pub const B1_HIP_CONTOUR_PROFILE_ID: &str = "nvwa-mpfb-b1-hip-contour-v1";
pub const B1_V8_ASSET_ID: &str = "mpfb-hm08-game-engine-female-sportsuit01-v8";
pub const B1_V8_ASSET_PATH: &str = "characters/mpfb-b1-v8/manifest.json";
pub const B1_V8_ASSET_MANIFEST_SHA256: &str =
    "a74911c1e66bd257fbdf149dc30467560c70b6eb6c2cae38e01f9313b53ef4be";
pub const B1_V8_ASSET_MANIFEST_BYTES: &[u8] =
    include_bytes!("../../../assets/characters/mpfb-b1-v8/manifest.json");

pub const B1_ARM_PROPORTIONS_PROFILE_ID: &str = "nvwa-mpfb-b1-arm-proportions-v1";
pub const B1_V9_ASSET_ID: &str = "mpfb-hm08-game-engine-female-sportsuit01-v9";
pub const B1_V9_ASSET_PATH: &str = "characters/mpfb-b1-v9/manifest.json";
pub const B1_V9_ASSET_MANIFEST_SHA256: &str =
    "8613722c3924d729ab2f8fbc7f25f3225ee740afaf290bc97b46e03f174d6f48";
pub const B1_V9_ASSET_MANIFEST_BYTES: &[u8] =
    include_bytes!("../../../assets/characters/mpfb-b1-v9/manifest.json");

pub const B1_HAND_SIZE_PROFILE_ID: &str = "nvwa-mpfb-b1-hand-size-v1";
pub const B1_V11_ASSET_ID: &str = "mpfb-hm08-game-engine-female-sportsuit01-v11";
pub const B1_V11_ASSET_PATH: &str = "characters/mpfb-b1-v11/manifest.json";
pub const B1_V11_ASSET_MANIFEST_SHA256: &str =
    "27e4810fed7241ea26e90e28d69da8d1c553ba8ca2e68eee6843301968bb090d";
pub const B1_V11_ASSET_MANIFEST_BYTES: &[u8] =
    include_bytes!("../../../assets/characters/mpfb-b1-v11/manifest.json");

pub const B1_SHOULDER_FORM_PROFILE_ID: &str = "nvwa-mpfb-b1-shoulder-form-v1";
pub const B1_V12_ASSET_ID: &str = "mpfb-hm08-game-engine-female-sportsuit01-v12";
pub const B1_V12_ASSET_PATH: &str = "characters/mpfb-b1-v12/manifest.json";
pub const B1_V12_ASSET_MANIFEST_SHA256: &str =
    "4bd02ea911f3967c862a4760cd7d223dee2f32d0ca59f72ccb252bc69ed8f8b3";
pub const B1_V12_ASSET_MANIFEST_BYTES: &[u8] =
    include_bytes!("../../../assets/characters/mpfb-b1-v12/manifest.json");

/// Finite shipped base catalogue. This is not a caller-defined asset registry.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum B1AssetVersion {
    V1,
    V2,
    V3,
    V4,
    V5,
    V6,
    V7,
    V8,
    V9,
    V11,
    V12,
}
impl B1AssetVersion {
    pub const fn asset_id(self) -> &'static str {
        match self {
            Self::V1 => B1_ASSET_ID,
            Self::V2 => B1_V2_ASSET_ID,
            Self::V3 => B1_V3_ASSET_ID,
            Self::V4 => B1_V4_ASSET_ID,
            Self::V5 => B1_V5_ASSET_ID,
            Self::V6 => B1_V6_ASSET_ID,
            Self::V7 => B1_V7_ASSET_ID,
            Self::V8 => B1_V8_ASSET_ID,
            Self::V9 => B1_V9_ASSET_ID,
            Self::V11 => B1_V11_ASSET_ID,
            Self::V12 => B1_V12_ASSET_ID,
        }
    }
    pub const fn manifest_path(self) -> &'static str {
        match self {
            Self::V1 => B1_ASSET_PATH,
            Self::V2 => B1_V2_ASSET_PATH,
            Self::V3 => B1_V3_ASSET_PATH,
            Self::V4 => B1_V4_ASSET_PATH,
            Self::V5 => B1_V5_ASSET_PATH,
            Self::V6 => B1_V6_ASSET_PATH,
            Self::V7 => B1_V7_ASSET_PATH,
            Self::V8 => B1_V8_ASSET_PATH,
            Self::V9 => B1_V9_ASSET_PATH,
            Self::V11 => B1_V11_ASSET_PATH,
            Self::V12 => B1_V12_ASSET_PATH,
        }
    }
    pub const fn manifest_sha256(self) -> &'static str {
        match self {
            Self::V1 => B1_ASSET_MANIFEST_SHA256,
            Self::V2 => B1_V2_ASSET_MANIFEST_SHA256,
            Self::V3 => B1_V3_ASSET_MANIFEST_SHA256,
            Self::V4 => B1_V4_ASSET_MANIFEST_SHA256,
            Self::V5 => B1_V5_ASSET_MANIFEST_SHA256,
            Self::V6 => B1_V6_ASSET_MANIFEST_SHA256,
            Self::V7 => B1_V7_ASSET_MANIFEST_SHA256,
            Self::V8 => B1_V8_ASSET_MANIFEST_SHA256,
            Self::V9 => B1_V9_ASSET_MANIFEST_SHA256,
            Self::V11 => B1_V11_ASSET_MANIFEST_SHA256,
            Self::V12 => B1_V12_ASSET_MANIFEST_SHA256,
        }
    }
    pub const fn manifest_bytes(self) -> &'static [u8] {
        match self {
            Self::V1 => B1_ASSET_MANIFEST_BYTES,
            Self::V2 => B1_V2_ASSET_MANIFEST_BYTES,
            Self::V3 => B1_V3_ASSET_MANIFEST_BYTES,
            Self::V4 => B1_V4_ASSET_MANIFEST_BYTES,
            Self::V5 => B1_V5_ASSET_MANIFEST_BYTES,
            Self::V6 => B1_V6_ASSET_MANIFEST_BYTES,
            Self::V7 => B1_V7_ASSET_MANIFEST_BYTES,
            Self::V8 => B1_V8_ASSET_MANIFEST_BYTES,
            Self::V9 => B1_V9_ASSET_MANIFEST_BYTES,
            Self::V11 => B1_V11_ASSET_MANIFEST_BYTES,
            Self::V12 => B1_V12_ASSET_MANIFEST_BYTES,
        }
    }
    pub fn parameters(self) -> &'static [B1ParameterTargets] {
        match self {
            Self::V1 => &B1_PARAMETER_TARGETS[..2],
            Self::V2 => &B1_PARAMETER_TARGETS,
            Self::V3 => &B1_CONTOUR_PARAMETER_TARGETS,
            Self::V4 => &B1_LOWER_CONTOUR_PARAMETER_TARGETS,
            Self::V5 => &B1_WAIST_PARAMETER_TARGETS,
            Self::V6 => &B1_LEG_PARAMETER_TARGETS,
            Self::V7 => &B1_UPPER_BODY_PARAMETER_TARGETS,
            Self::V8 => &B1_HIP_CONTOUR_PARAMETER_TARGETS,
            Self::V9 => &B1_ARM_PROPORTIONS_PARAMETER_TARGETS,
            Self::V11 => &B1_HAND_SIZE_PARAMETER_TARGETS,
            Self::V12 => &B1_SHOULDER_FORM_PARAMETER_TARGETS,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct B1ParameterTargets {
    pub id: &'static str,
    pub decrease: &'static str,
    pub increase: &'static str,
}
pub const B1_PARAMETER_TARGETS: [B1ParameterTargets; 8] = [
    B1ParameterTargets {
        id: "torso_length",
        decrease: "torso-scale-vert-decr",
        increase: "torso-scale-vert-incr",
    },
    B1ParameterTargets {
        id: "jaw_drop",
        decrease: "chin-jaw-drop-decr",
        increase: "chin-jaw-drop-incr",
    },
    B1ParameterTargets {
        id: "head_width",
        decrease: "head-scale-horiz-decr",
        increase: "head-scale-horiz-incr",
    },
    B1ParameterTargets {
        id: "nose_width",
        decrease: "nose-scale-horiz-decr",
        increase: "nose-scale-horiz-incr",
    },
    B1ParameterTargets {
        id: "mouth_width",
        decrease: "mouth-scale-horiz-decr",
        increase: "mouth-scale-horiz-incr",
    },
    B1ParameterTargets {
        id: "chin_width",
        decrease: "chin-width-decr",
        increase: "chin-width-incr",
    },
    B1ParameterTargets {
        id: "neck_width",
        decrease: "neck-scale-horiz-decr",
        increase: "neck-scale-horiz-incr",
    },
    B1ParameterTargets {
        id: "hip_width",
        decrease: "hip-scale-horiz-decr",
        increase: "hip-scale-horiz-incr",
    },
];
pub const B1_CONTOUR_PARAMETER_TARGETS: [B1ParameterTargets; 9] = [
    B1_PARAMETER_TARGETS[0],
    B1_PARAMETER_TARGETS[1],
    B1_PARAMETER_TARGETS[2],
    B1_PARAMETER_TARGETS[3],
    B1_PARAMETER_TARGETS[4],
    B1_PARAMETER_TARGETS[5],
    B1_PARAMETER_TARGETS[6],
    B1_PARAMETER_TARGETS[7],
    B1ParameterTargets {
        id: "cheek_fullness",
        decrease: "cheek-volume-bilateral-decr",
        increase: "cheek-volume-bilateral-incr",
    },
];
pub const B1_LOWER_CONTOUR_PARAMETER_TARGETS: [B1ParameterTargets; 10] = [
    B1_CONTOUR_PARAMETER_TARGETS[0],
    B1_CONTOUR_PARAMETER_TARGETS[1],
    B1_CONTOUR_PARAMETER_TARGETS[2],
    B1_CONTOUR_PARAMETER_TARGETS[3],
    B1_CONTOUR_PARAMETER_TARGETS[4],
    B1_CONTOUR_PARAMETER_TARGETS[5],
    B1_CONTOUR_PARAMETER_TARGETS[6],
    B1_CONTOUR_PARAMETER_TARGETS[7],
    B1_CONTOUR_PARAMETER_TARGETS[8],
    // The exact decrease leaf is retained for the existing loader pair only.
    // Canonical lower_face_squareness is0..1, so its weight is always zero.
    B1ParameterTargets {
        id: "lower_face_squareness",
        decrease: "chin-bones-decr",
        increase: "chin-bones-incr",
    },
];
pub const B1_WAIST_PARAMETER_TARGETS: [B1ParameterTargets; 11] = [
    B1_LOWER_CONTOUR_PARAMETER_TARGETS[0],
    B1_LOWER_CONTOUR_PARAMETER_TARGETS[1],
    B1_LOWER_CONTOUR_PARAMETER_TARGETS[2],
    B1_LOWER_CONTOUR_PARAMETER_TARGETS[3],
    B1_LOWER_CONTOUR_PARAMETER_TARGETS[4],
    B1_LOWER_CONTOUR_PARAMETER_TARGETS[5],
    B1_LOWER_CONTOUR_PARAMETER_TARGETS[6],
    B1_LOWER_CONTOUR_PARAMETER_TARGETS[7],
    B1_LOWER_CONTOUR_PARAMETER_TARGETS[8],
    B1_LOWER_CONTOUR_PARAMETER_TARGETS[9],
    B1ParameterTargets {
        id: "waist_circumference",
        decrease: "measure-waist-circ-decr",
        increase: "measure-waist-circ-incr",
    },
];
pub const B1_LEG_PARAMETER_TARGETS: [B1ParameterTargets; 15] = [
    B1_WAIST_PARAMETER_TARGETS[0],
    B1_WAIST_PARAMETER_TARGETS[1],
    B1_WAIST_PARAMETER_TARGETS[2],
    B1_WAIST_PARAMETER_TARGETS[3],
    B1_WAIST_PARAMETER_TARGETS[4],
    B1_WAIST_PARAMETER_TARGETS[5],
    B1_WAIST_PARAMETER_TARGETS[6],
    B1_WAIST_PARAMETER_TARGETS[7],
    B1_WAIST_PARAMETER_TARGETS[8],
    B1_WAIST_PARAMETER_TARGETS[9],
    B1_WAIST_PARAMETER_TARGETS[10],
    B1ParameterTargets {
        id: "thigh_length",
        decrease: "measure-upperleg-height-decr",
        increase: "measure-upperleg-height-incr",
    },
    B1ParameterTargets {
        id: "lower_leg_length",
        decrease: "measure-lowerleg-height-decr",
        increase: "measure-lowerleg-height-incr",
    },
    B1ParameterTargets {
        id: "thigh_girth",
        decrease: "measure-thigh-circ-decr",
        increase: "measure-thigh-circ-incr",
    },
    B1ParameterTargets {
        id: "calf_girth",
        decrease: "measure-calf-circ-decr",
        increase: "measure-calf-circ-incr",
    },
];
pub const B1_UPPER_BODY_PARAMETER_TARGETS: [B1ParameterTargets; 18] = [
    B1_LEG_PARAMETER_TARGETS[0],
    B1_LEG_PARAMETER_TARGETS[1],
    B1_LEG_PARAMETER_TARGETS[2],
    B1_LEG_PARAMETER_TARGETS[3],
    B1_LEG_PARAMETER_TARGETS[4],
    B1_LEG_PARAMETER_TARGETS[5],
    B1_LEG_PARAMETER_TARGETS[6],
    B1_LEG_PARAMETER_TARGETS[7],
    B1_LEG_PARAMETER_TARGETS[8],
    B1_LEG_PARAMETER_TARGETS[9],
    B1_LEG_PARAMETER_TARGETS[10],
    B1_LEG_PARAMETER_TARGETS[11],
    B1_LEG_PARAMETER_TARGETS[12],
    B1_LEG_PARAMETER_TARGETS[13],
    B1_LEG_PARAMETER_TARGETS[14],
    B1ParameterTargets {
        id: "bust_circumference",
        decrease: "measure-bust-circ-decr",
        increase: "measure-bust-circ-incr",
    },
    B1ParameterTargets {
        id: "shoulder_span",
        decrease: "measure-shoulder-dist-decr",
        increase: "measure-shoulder-dist-incr",
    },
    B1ParameterTargets {
        id: "upper_arm_girth",
        decrease: "measure-upperarm-circ-decr",
        increase: "measure-upperarm-circ-incr",
    },
];
pub const B1_HIP_CONTOUR_PARAMETER_TARGETS: [B1ParameterTargets; 20] = [
    B1_UPPER_BODY_PARAMETER_TARGETS[0],
    B1_UPPER_BODY_PARAMETER_TARGETS[1],
    B1_UPPER_BODY_PARAMETER_TARGETS[2],
    B1_UPPER_BODY_PARAMETER_TARGETS[3],
    B1_UPPER_BODY_PARAMETER_TARGETS[4],
    B1_UPPER_BODY_PARAMETER_TARGETS[5],
    B1_UPPER_BODY_PARAMETER_TARGETS[6],
    B1_UPPER_BODY_PARAMETER_TARGETS[7],
    B1_UPPER_BODY_PARAMETER_TARGETS[8],
    B1_UPPER_BODY_PARAMETER_TARGETS[9],
    B1_UPPER_BODY_PARAMETER_TARGETS[10],
    B1_UPPER_BODY_PARAMETER_TARGETS[11],
    B1_UPPER_BODY_PARAMETER_TARGETS[12],
    B1_UPPER_BODY_PARAMETER_TARGETS[13],
    B1_UPPER_BODY_PARAMETER_TARGETS[14],
    B1_UPPER_BODY_PARAMETER_TARGETS[15],
    B1_UPPER_BODY_PARAMETER_TARGETS[16],
    B1_UPPER_BODY_PARAMETER_TARGETS[17],
    B1ParameterTargets {
        id: "hip_depth",
        decrease: "hip-scale-depth-decr",
        increase: "hip-scale-depth-incr",
    },
    B1ParameterTargets {
        id: "buttocks_volume",
        decrease: "buttocks-volume-decr",
        increase: "buttocks-volume-incr",
    },
];
pub const B1_ARM_PROPORTIONS_PARAMETER_TARGETS: [B1ParameterTargets; 23] = [
    B1_HIP_CONTOUR_PARAMETER_TARGETS[0],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[1],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[2],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[3],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[4],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[5],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[6],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[7],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[8],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[9],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[10],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[11],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[12],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[13],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[14],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[15],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[16],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[17],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[18],
    B1_HIP_CONTOUR_PARAMETER_TARGETS[19],
    B1ParameterTargets {
        id: "upper_arm_length",
        decrease: "measure-upperarm-length-decr",
        increase: "measure-upperarm-length-incr",
    },
    B1ParameterTargets {
        id: "forearm_length",
        decrease: "measure-lowerarm-length-decr",
        increase: "measure-lowerarm-length-incr",
    },
    B1ParameterTargets {
        id: "wrist_circumference",
        decrease: "measure-wrist-circ-decr",
        increase: "measure-wrist-circ-incr",
    },
];
/// Independent authored left/right hand-size target weights. These are not
/// centimetres and do not certify finger articulation or prop grip.
pub const B1_HAND_SIZE_PARAMETER_TARGETS: [B1ParameterTargets; 25] = [
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[0],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[1],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[2],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[3],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[4],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[5],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[6],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[7],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[8],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[9],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[10],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[11],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[12],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[13],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[14],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[15],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[16],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[17],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[18],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[19],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[20],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[21],
    B1_ARM_PROPORTIONS_PARAMETER_TARGETS[22],
    B1ParameterTargets {
        id: "left_hand_size",
        decrease: "l-hand-scale-decr",
        increase: "l-hand-scale-incr",
    },
    B1ParameterTargets {
        id: "right_hand_size",
        decrease: "r-hand-scale-decr",
        increase: "r-hand-scale-incr",
    },
];
/// Bilateral shoulder muscle shape, separate from shoulder span. A signed
/// source-target weight is not a mass, circumference or posture measurement.
pub const B1_SHOULDER_FORM_PARAMETER_TARGETS: [B1ParameterTargets; 26] = [
    B1_HAND_SIZE_PARAMETER_TARGETS[0],
    B1_HAND_SIZE_PARAMETER_TARGETS[1],
    B1_HAND_SIZE_PARAMETER_TARGETS[2],
    B1_HAND_SIZE_PARAMETER_TARGETS[3],
    B1_HAND_SIZE_PARAMETER_TARGETS[4],
    B1_HAND_SIZE_PARAMETER_TARGETS[5],
    B1_HAND_SIZE_PARAMETER_TARGETS[6],
    B1_HAND_SIZE_PARAMETER_TARGETS[7],
    B1_HAND_SIZE_PARAMETER_TARGETS[8],
    B1_HAND_SIZE_PARAMETER_TARGETS[9],
    B1_HAND_SIZE_PARAMETER_TARGETS[10],
    B1_HAND_SIZE_PARAMETER_TARGETS[11],
    B1_HAND_SIZE_PARAMETER_TARGETS[12],
    B1_HAND_SIZE_PARAMETER_TARGETS[13],
    B1_HAND_SIZE_PARAMETER_TARGETS[14],
    B1_HAND_SIZE_PARAMETER_TARGETS[15],
    B1_HAND_SIZE_PARAMETER_TARGETS[16],
    B1_HAND_SIZE_PARAMETER_TARGETS[17],
    B1_HAND_SIZE_PARAMETER_TARGETS[18],
    B1_HAND_SIZE_PARAMETER_TARGETS[19],
    B1_HAND_SIZE_PARAMETER_TARGETS[20],
    B1_HAND_SIZE_PARAMETER_TARGETS[21],
    B1_HAND_SIZE_PARAMETER_TARGETS[22],
    B1_HAND_SIZE_PARAMETER_TARGETS[23],
    B1_HAND_SIZE_PARAMETER_TARGETS[24],
    B1ParameterTargets {
        id: "shoulder_muscle_fullness",
        decrease: "shoulder-muscle-decr",
        increase: "shoulder-muscle-incr",
    },
];
pub const B1_DIAGNOSTIC_POSES: [&str; 5] = ["neutral", "shoulder", "elbow", "knee", "combined"];
pub const B1_MAX_MANIFEST_BYTES: usize = 32 * 1024;
pub const B1_MAX_ASSET_BYTES: usize = 4 * 1024 * 1024;
pub const B1_MAX_TOTAL_ASSET_BYTES: usize = 8 * 1024 * 1024;

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum CharacterBackend {
    Glb {
        schema_version: u32,
    },
    B1Cpu {
        schema_version: u32,
        asset_id: String,
    },
}

impl<'de> Deserialize<'de> for CharacterBackend {
    fn deserialize<D: serde::Deserializer<'de>>(
        deserializer: D,
    ) -> std::result::Result<Self, D::Error> {
        // String's decoder rejects explicit null; presence rejects glb asset_id,
        // including null. Derive retains duplicate/unknown-field rejection.
        #[derive(Default)]
        struct AssetId(Option<String>);
        impl<'de> Deserialize<'de> for AssetId {
            fn deserialize<D: serde::Deserializer<'de>>(
                deserializer: D,
            ) -> std::result::Result<Self, D::Error> {
                String::deserialize(deserializer).map(|id| Self(Some(id)))
            }
        }
        #[derive(Deserialize)]
        #[serde(deny_unknown_fields)]
        struct Wire {
            #[serde(rename = "type")]
            kind: String,
            schema_version: u32,
            #[serde(default)]
            asset_id: AssetId,
        }
        let wire = Wire::deserialize(deserializer)?;
        match (wire.kind.as_str(), wire.asset_id.0) {
            ("glb", None) => Ok(Self::Glb {
                schema_version: wire.schema_version,
            }),
            ("glb", Some(_)) => Err(serde::de::Error::custom(
                "glb backend does not allow asset_id",
            )),
            ("b1_cpu", Some(asset_id)) => Ok(Self::B1Cpu {
                schema_version: wire.schema_version,
                asset_id,
            }),
            ("b1_cpu", None) => Err(serde::de::Error::missing_field("asset_id")),
            (kind, _) => Err(serde::de::Error::custom(format!(
                "unsupported_character_backend: unknown character backend {kind}"
            ))),
        }
    }
}

impl CharacterBackend {
    pub fn is_b1(&self) -> bool {
        matches!(self, Self::B1Cpu { .. })
    }
    pub fn is_b1_motion(&self) -> bool {
        matches!(
            self,
            Self::B1Cpu {
                schema_version: 2..=5,
                ..
            }
        ) || self.is_b1_running()
    }
    pub fn is_b1_running(&self) -> bool {
        matches!(self, Self::B1Cpu { schema_version: 6, asset_id } if asset_id == B1_V4_ASSET_ID)
    }
    pub fn b1_asset_version(&self) -> Option<B1AssetVersion> {
        match self {
            Self::B1Cpu {
                schema_version: 1 | 2,
                asset_id,
            } if asset_id == B1_ASSET_ID => Some(B1AssetVersion::V1),
            Self::B1Cpu {
                schema_version: 3,
                asset_id,
            } if asset_id == B1_V2_ASSET_ID => Some(B1AssetVersion::V2),
            Self::B1Cpu {
                schema_version: 4,
                asset_id,
            } if asset_id == B1_V3_ASSET_ID => Some(B1AssetVersion::V3),
            Self::B1Cpu {
                schema_version: 5 | 6,
                asset_id,
            } if asset_id == B1_V4_ASSET_ID => Some(B1AssetVersion::V4),
            Self::B1Cpu {
                schema_version: 7,
                asset_id,
            } if asset_id == B1_V5_ASSET_ID => Some(B1AssetVersion::V5),
            Self::B1Cpu {
                schema_version: 8,
                asset_id,
            } if asset_id == B1_V6_ASSET_ID => Some(B1AssetVersion::V6),
            Self::B1Cpu {
                schema_version: 9,
                asset_id,
            } if asset_id == B1_V7_ASSET_ID => Some(B1AssetVersion::V7),
            Self::B1Cpu {
                schema_version: 10,
                asset_id,
            } if asset_id == B1_V8_ASSET_ID => Some(B1AssetVersion::V8),
            CharacterBackend::B1Cpu {
                schema_version: 11,
                asset_id,
            } if asset_id == B1_V9_ASSET_ID => Some(B1AssetVersion::V9),
            CharacterBackend::B1Cpu {
                asset_id,
                schema_version: 13,
            } if asset_id == B1_V11_ASSET_ID => Some(B1AssetVersion::V11),
            CharacterBackend::B1Cpu {
                asset_id,
                schema_version: 14,
            } if asset_id == B1_V12_ASSET_ID => Some(B1AssetVersion::V12),
            _ => None,
        }
    }
    pub fn supports_timeline(&self) -> bool {
        self.is_glb() || self.is_b1_motion()
    }
    pub fn is_glb(&self) -> bool {
        matches!(self, Self::Glb { .. })
    }
    pub fn validate(&self) -> Result<()> {
        let version = match self {
            Self::Glb { schema_version } | Self::B1Cpu { schema_version, .. } => *schema_version,
        };
        if version != 1 && !(matches!(version, 2..=14) && self.is_b1()) {
            return Err(CoreError::new(
                "unsupported_character_version",
                format!("character backend version {version} is unsupported"),
            ));
        }
        if let Self::B1Cpu { asset_id, .. } = self
            && self.b1_asset_version().is_none()
        {
            return Err(CoreError::new(
                "unsupported_character_asset",
                format!("unsupported B1 asset {asset_id}; expected {B1_ASSET_ID}"),
            ));
        }
        Ok(())
    }
}

impl CharacterProfile {
    /// The only admitted B1 sample. Indices 0/1 are inert legacy metadata on
    /// this backend, never GLB morph indices. Source target pairs are fixed.
    pub fn b1() -> Self {
        Self {
            backend: CharacterBackend::B1Cpu {
                schema_version: 1,
                asset_id: B1_ASSET_ID.into(),
            },
            id: B1_PROFILE_ID.into(),
            asset_path: B1_ASSET_PATH.into(),
            asset_sha256: B1_ASSET_MANIFEST_SHA256.into(),
            license: "CC0-1.0".into(),
            parameters: ["torso_length", "jaw_drop"]
                .into_iter()
                .enumerate()
                .map(|(morph_index, id)| ParameterSpec {
                    id: id.into(),
                    morph_index,
                    min: -1.0,
                    max: 1.0,
                    default: 0.0,
                })
                .collect(),
            clips: Vec::new(),
        }
    }
    /// Authored continuous rehearsal on the same admitted body and sportsuit.
    pub fn b1_motion() -> Self {
        let mut profile = Self::b1();
        profile.backend = CharacterBackend::B1Cpu {
            schema_version: 2,
            asset_id: B1_ASSET_ID.into(),
        };
        profile.id = B1_MOTION_PROFILE_ID.into();
        profile.clips = B1_MOTION_CLIPS
            .into_iter()
            .enumerate()
            .map(|(animation_index, id)| ClipSpec {
                id: id.into(),
                animation_index,
                duration_seconds: B1_MOTION_DURATION_SECONDS,
            })
            .collect();
        profile
    }
    /// Eight exact source parameters on the second immutable motion asset set.
    pub fn b1_character() -> Self {
        let mut profile = Self::b1_motion();
        profile.backend = CharacterBackend::B1Cpu {
            schema_version: 3,
            asset_id: B1_V2_ASSET_ID.into(),
        };
        profile.id = B1_CHARACTER_PROFILE_ID.into();
        profile.asset_path = B1_V2_ASSET_PATH.into();
        profile.asset_sha256 = B1_V2_ASSET_MANIFEST_SHA256.into();
        profile.parameters = B1_PARAMETER_TARGETS
            .iter()
            .enumerate()
            .map(|(morph_index, targets)| ParameterSpec {
                id: targets.id.into(),
                morph_index,
                min: -1.0,
                max: 1.0,
                default: 0.0,
            })
            .collect();
        profile
    }
    /// Explicit nine-parameter profile. Existing Works are never migrated.
    pub fn b1_character_contour() -> Self {
        let mut profile = Self::b1_character();
        profile.backend = CharacterBackend::B1Cpu {
            schema_version: 4,
            asset_id: B1_V3_ASSET_ID.into(),
        };
        profile.id = B1_CONTOUR_PROFILE_ID.into();
        profile.asset_path = B1_V3_ASSET_PATH.into();
        profile.asset_sha256 = B1_V3_ASSET_MANIFEST_SHA256.into();
        profile.parameters.push(ParameterSpec {
            id: "cheek_fullness".into(),
            morph_index: 8,
            min: -1.0,
            max: 1.0,
            default: 0.0,
        });
        profile
    }
    /// Explicit E-only contour extension. Old profiles and Works stay fixed.
    pub fn b1_character_lower_contour() -> Self {
        let mut profile = Self::b1_character_contour();
        profile.backend = CharacterBackend::B1Cpu {
            schema_version: 5,
            asset_id: B1_V4_ASSET_ID.into(),
        };
        profile.id = B1_LOWER_CONTOUR_PROFILE_ID.into();
        profile.asset_path = B1_V4_ASSET_PATH.into();
        profile.asset_sha256 = B1_V4_ASSET_MANIFEST_SHA256.into();
        profile.parameters.push(ParameterSpec {
            id: "lower_face_squareness".into(),
            morph_index: 9,
            min: 0.0,
            max: 1.0,
            default: 0.0,
        });
        profile
    }
    /// Static waist extension. No motion or appearance acceptance is inherited.
    /// Existing Works retain their original profile and asset version.
    pub fn b1_character_waist() -> Self {
        let mut profile = Self::b1_character_lower_contour();
        profile.backend = CharacterBackend::B1Cpu {
            schema_version: 7,
            asset_id: B1_V5_ASSET_ID.into(),
        };
        profile.id = B1_WAIST_PROFILE_ID.into();
        profile.asset_path = B1_V5_ASSET_PATH.into();
        profile.asset_sha256 = B1_V5_ASSET_MANIFEST_SHA256.into();
        profile.clips.clear();
        profile.parameters.push(ParameterSpec {
            id: "waist_circumference".into(),
            morph_index: 10,
            min: -1.0,
            max: 1.0,
            default: 0.0,
        });
        profile
    }
    /// Static bilateral leg extension. Values are authored target weights, not centimetres.
    /// Old Works keep their exact prior profile and asset set.
    pub fn b1_character_legs() -> Self {
        let mut profile = Self::b1_character_waist();
        profile.backend = CharacterBackend::B1Cpu {
            schema_version: 8,
            asset_id: B1_V6_ASSET_ID.into(),
        };
        profile.id = B1_LEG_PROFILE_ID.into();
        profile.asset_path = B1_V6_ASSET_PATH.into();
        profile.asset_sha256 = B1_V6_ASSET_MANIFEST_SHA256.into();
        profile
            .parameters
            .extend(
                B1_LEG_PARAMETER_TARGETS[11..]
                    .iter()
                    .enumerate()
                    .map(|(offset, target)| ParameterSpec {
                        id: target.id.into(),
                        morph_index: 11 + offset,
                        min: -1.0,
                        max: 1.0,
                        default: 0.0,
                    }),
            );
        profile
    }
    /// Static upper-body shape extension. Signed values are authored target weights.
    /// Earlier Works retain their exact profile and asset bytes.
    pub fn b1_character_upper_body() -> Self {
        let mut profile = Self::b1_character_legs();
        profile.backend = CharacterBackend::B1Cpu {
            schema_version: 9,
            asset_id: B1_V7_ASSET_ID.into(),
        };
        profile.id = B1_UPPER_BODY_PROFILE_ID.into();
        profile.asset_path = B1_V7_ASSET_PATH.into();
        profile.asset_sha256 = B1_V7_ASSET_MANIFEST_SHA256.into();
        profile.parameters.extend(
            B1_UPPER_BODY_PARAMETER_TARGETS[15..]
                .iter()
                .enumerate()
                .map(|(offset, target)| ParameterSpec {
                    id: target.id.into(),
                    morph_index: 15 + offset,
                    min: -1.0,
                    max: 1.0,
                    default: 0.0,
                }),
        );
        profile
    }
    /// Static hip depth and buttocks volume extension; values are source-target
    /// weights, not centimetres. Older Works keep their exact profile identity.
    pub fn b1_character_hip_contour() -> Self {
        let mut profile = Self::b1_character_upper_body();
        profile.backend = CharacterBackend::B1Cpu {
            schema_version: 10,
            asset_id: B1_V8_ASSET_ID.into(),
        };
        profile.id = B1_HIP_CONTOUR_PROFILE_ID.into();
        profile.asset_path = B1_V8_ASSET_PATH.into();
        profile.asset_sha256 = B1_V8_ASSET_MANIFEST_SHA256.into();
        profile.parameters.extend(
            B1_HIP_CONTOUR_PARAMETER_TARGETS[18..]
                .iter()
                .enumerate()
                .map(|(offset, target)| ParameterSpec {
                    id: target.id.into(),
                    morph_index: 18 + offset,
                    min: -1.0,
                    max: 1.0,
                    default: 0.0,
                }),
        );
        profile
    }
    /// Static bilateral arm-length and wrist-circumference extension. These are
    /// authored source-target weights, not centimetres or measured lengths.
    pub fn b1_character_arm_proportions() -> Self {
        let mut profile = Self::b1_character_hip_contour();
        profile.backend = CharacterBackend::B1Cpu {
            schema_version: 11,
            asset_id: B1_V9_ASSET_ID.into(),
        };
        profile.id = B1_ARM_PROPORTIONS_PROFILE_ID.into();
        profile.asset_path = B1_V9_ASSET_PATH.into();
        profile.asset_sha256 = B1_V9_ASSET_MANIFEST_SHA256.into();
        profile.parameters.extend(
            B1_ARM_PROPORTIONS_PARAMETER_TARGETS[20..]
                .iter()
                .enumerate()
                .map(|(offset, target)| ParameterSpec {
                    id: target.id.into(),
                    morph_index: 20 + offset,
                    min: -1.0,
                    max: 1.0,
                    default: 0.0,
                }),
        );
        profile
    }
    /// Static independent hand-size extension. Zero retains v9 geometry;
    /// older Works remain pinned to their original assets and profile.
    pub fn b1_character_hand_size() -> Self {
        let mut profile = Self::b1_character_arm_proportions();
        profile.backend = CharacterBackend::B1Cpu {
            schema_version: 13,
            asset_id: B1_V11_ASSET_ID.into(),
        };
        profile.id = B1_HAND_SIZE_PROFILE_ID.into();
        profile.asset_path = B1_V11_ASSET_PATH.into();
        profile.asset_sha256 = B1_V11_ASSET_MANIFEST_SHA256.into();
        profile
            .parameters
            .extend(B1_HAND_SIZE_PARAMETER_TARGETS[23..].iter().enumerate().map(
                |(offset, target)| ParameterSpec {
                    id: target.id.into(),
                    morph_index: 23 + offset,
                    min: -1.0,
                    max: 1.0,
                    default: 0.0,
                },
            ));
        profile
    }
    /// Static bilateral shoulder-muscle extension. Zero preserves v11 geometry.
    pub fn b1_character_shoulder_form() -> Self {
        let mut profile = Self::b1_character_hand_size();
        profile.backend = CharacterBackend::B1Cpu {
            schema_version: 14,
            asset_id: B1_V12_ASSET_ID.into(),
        };
        profile.id = B1_SHOULDER_FORM_PROFILE_ID.into();
        profile.asset_path = B1_V12_ASSET_PATH.into();
        profile.asset_sha256 = B1_V12_ASSET_MANIFEST_SHA256.into();
        profile.parameters.push(ParameterSpec {
            id: "shoulder_muscle_fullness".into(),
            morph_index: 25,
            min: -1.0,
            max: 1.0,
            default: 0.0,
        });
        profile
    }
    /// New immutable finite running profile on the exact existing V4 asset set.
    pub fn b1_running() -> Self {
        let mut profile = Self::b1_character_lower_contour();
        profile.backend = CharacterBackend::B1Cpu {
            schema_version: 6,
            asset_id: B1_V4_ASSET_ID.into(),
        };
        profile.id = B1_RUNNING_PROFILE_ID.into();
        // Retain the exact old ClipSpec records, including inert indices.
        profile.clips.insert(
            0,
            ClipSpec {
                id: B1_RUN_CLIP_ID.into(),
                animation_index: 2,
                duration_seconds: crate::running::SOURCE_SECONDS as f32,
            },
        );
        profile
    }
    pub(crate) fn validate_b1(&self) -> Result<()> {
        if (self.id == B1_PROFILE_ID && self.backend.is_b1_motion())
            || (self.id == B1_MOTION_PROFILE_ID && !self.backend.is_b1_motion())
        {
            return Err(CoreError::new(
                "unsupported_character_version",
                "B1 backend version does not match its canonical profile identity",
            ));
        }
        let canonical = if self.backend.b1_asset_version() == Some(B1AssetVersion::V12) {
            Self::b1_character_shoulder_form()
        } else if self.backend.b1_asset_version() == Some(B1AssetVersion::V11) {
            Self::b1_character_hand_size()
        } else if self.backend.b1_asset_version() == Some(B1AssetVersion::V9) {
            Self::b1_character_arm_proportions()
        } else if self.backend.b1_asset_version() == Some(B1AssetVersion::V8) {
            Self::b1_character_hip_contour()
        } else if self.backend.b1_asset_version() == Some(B1AssetVersion::V7) {
            Self::b1_character_upper_body()
        } else if self.backend.b1_asset_version() == Some(B1AssetVersion::V6) {
            Self::b1_character_legs()
        } else if self.backend.b1_asset_version() == Some(B1AssetVersion::V5) {
            Self::b1_character_waist()
        } else if self.backend.is_b1_running() {
            Self::b1_running()
        } else if self.backend.b1_asset_version() == Some(B1AssetVersion::V4) {
            Self::b1_character_lower_contour()
        } else if self.backend.b1_asset_version() == Some(B1AssetVersion::V3) {
            Self::b1_character_contour()
        } else if self.backend.b1_asset_version() == Some(B1AssetVersion::V2) {
            Self::b1_character()
        } else if self.backend.is_b1_motion() {
            Self::b1_motion()
        } else {
            Self::b1()
        };
        if self != &canonical {
            return Err(CoreError::new(
                "unsupported_character_asset",
                "B1 requires its exact versioned shipped profile, asset identity, parameters and clip catalogue",
            ));
        }
        Ok(())
    }
}

pub(crate) fn validate_b1_pose(pose: &str) -> Result<()> {
    if !B1_DIAGNOSTIC_POSES.contains(&pose) {
        return Err(CoreError::new(
            "unsupported_pose",
            format!(
                "unsupported B1 diagnostic pose {pose}; expected neutral, shoulder, elbow, knee or combined"
            ),
        ));
    }
    Ok(())
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct B1AssetFile {
    pub path: String,
    pub bytes: usize,
    pub sha256: String,
    pub license: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct B1AssetManifest {
    pub format: String,
    pub schema_version: u32,
    pub asset_id: String,
    pub common_manifest_sha256: String,
    pub adapter_receipt_sha256: String,
    pub files: Vec<B1AssetFile>,
}

impl B1AssetManifest {
    /// Authenticate the exact shipped descriptor before interpreting its paths.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self> {
        Self::from_bytes_for(B1AssetVersion::V1, bytes)
    }

    pub fn from_bytes_for(version: B1AssetVersion, bytes: &[u8]) -> Result<Self> {
        if bytes.is_empty() {
            return Err(CoreError::new(
                "asset_missing",
                "B1 manifest is empty or missing",
            ));
        }
        if bytes.len() > B1_MAX_MANIFEST_BYTES {
            return Err(CoreError::new(
                "invalid_asset",
                "B1 manifest exceeds 32 KiB",
            ));
        }
        if format!("{:x}", Sha256::digest(bytes)) != version.manifest_sha256() {
            return Err(CoreError::new(
                "asset_hash_mismatch",
                "B1 manifest differs from the shipped descriptor",
            ));
        }
        let manifest = Self::decode(bytes)?;
        manifest.validate()?;
        Ok(manifest)
    }

    fn decode(bytes: &[u8]) -> Result<Self> {
        let text = std::str::from_utf8(bytes)
            .map_err(|e| CoreError::new("invalid_asset", e.to_string()))?;
        parse_json(text).map_err(|e| CoreError::new("invalid_asset", e.message))
    }

    /// Public fields do not grant callers authority to change the authenticated
    /// file set, hashes, paths or bounds used by validate_file_bytes.
    pub fn validate(&self) -> Result<()> {
        let version = match self.asset_id.as_str() {
            B1_ASSET_ID => B1AssetVersion::V1,
            B1_V2_ASSET_ID => B1AssetVersion::V2,
            B1_V3_ASSET_ID => B1AssetVersion::V3,
            B1_V4_ASSET_ID => B1AssetVersion::V4,
            B1_V5_ASSET_ID => B1AssetVersion::V5,
            B1_V6_ASSET_ID => B1AssetVersion::V6,
            B1_V7_ASSET_ID => B1AssetVersion::V7,
            B1_V8_ASSET_ID => B1AssetVersion::V8,
            B1_V9_ASSET_ID => B1AssetVersion::V9,
            B1_V11_ASSET_ID => B1AssetVersion::V11,
            B1_V12_ASSET_ID => B1AssetVersion::V12,
            _ => return Err(CoreError::new("invalid_asset", "unknown B1 asset identity")),
        };
        let canonical = Self::decode(version.manifest_bytes())?;
        if self != &canonical
            || self.format != "nvwa-b1-assets"
            || self.schema_version != 1
            || self.asset_id != version.asset_id()
            || self.files.len()
                != match version {
                    B1AssetVersion::V1 => 13,
                    B1AssetVersion::V2 => 25,
                    B1AssetVersion::V3 => 27,
                    B1AssetVersion::V4 => 29,
                    B1AssetVersion::V5 => 31,
                    B1AssetVersion::V6 => 39,
                    B1AssetVersion::V7 => 45,
                    B1AssetVersion::V8 => 49,
                    B1AssetVersion::V9 => 55,
                    B1AssetVersion::V11 => 59,
                    B1AssetVersion::V12 => 61,
                }
        {
            return Err(CoreError::new(
                "invalid_asset",
                "B1 descriptor must contain the exact versioned shipped file set and identities",
            ));
        }
        let mut total = 0usize;
        let mut previous: Option<&str> = None;
        for file in &self.files {
            if file.bytes == 0
                || file.bytes > B1_MAX_ASSET_BYTES
                || file.license != "CC0-1.0"
                || previous.is_some_and(|p| p >= file.path.as_str())
                || file
                    .path
                    .split('/')
                    .any(|p| p.is_empty() || p == "." || p == "..")
                || file
                    .path
                    .chars()
                    .any(|c| c.is_control() || matches!(c, '\\' | ':' | '?' | '#' | '%'))
            {
                return Err(CoreError::new(
                    "invalid_asset",
                    format!("invalid B1 asset descriptor entry {}", file.path),
                ));
            }
            previous = Some(&file.path);
            total = total
                .checked_add(file.bytes)
                .ok_or_else(|| CoreError::new("invalid_asset", "B1 asset total overflow"))?;
        }
        if total > B1_MAX_TOTAL_ASSET_BYTES {
            return Err(CoreError::new(
                "invalid_asset",
                "B1 asset total exceeds 8 MiB",
            ));
        }
        Ok(())
    }

    /// Validate caller-owned bytes, which a loader can then consume directly.
    /// This never reopens a path and never trusts a changed public descriptor.
    pub fn validate_file_bytes(&self, path: &str, bytes: &[u8]) -> Result<()> {
        self.validate()?;
        let file = self
            .files
            .iter()
            .find(|file| file.path == path)
            .ok_or_else(|| {
                CoreError::new(
                    "invalid_asset",
                    format!("unrecognized B1 asset path {path}"),
                )
            })?;
        if bytes.is_empty() {
            return Err(CoreError::new(
                "asset_missing",
                format!("B1 asset {path} is empty or missing"),
            ));
        }
        if bytes.len() > B1_MAX_ASSET_BYTES || bytes.len() != file.bytes {
            return Err(CoreError::new(
                "invalid_asset",
                format!(
                    "B1 asset {path} size mismatch; expected {} bytes, received {}",
                    file.bytes,
                    bytes.len()
                ),
            ));
        }
        if format!("{:x}", Sha256::digest(bytes)) != file.sha256 {
            return Err(CoreError::new(
                "asset_hash_mismatch",
                format!("B1 asset {path} SHA-256 mismatch"),
            ));
        }
        Ok(())
    }
}
