//! Read-only observation of current production entity/asset bindings.
use bevy::{mesh::VertexAttributeValues, prelude::*};
use nvwa_core::appearance_sha256;
use serde_json::{Value, json};

fn find(world: &World, label: &Value) -> Result<Entity, String> {
    let matches = world
        .iter_entities()
        .filter(|e| json!(format!("{:?}", e.id())) == *label)
        .map(|e| e.id())
        .collect::<Vec<_>>();
    if matches.len() != 1 {
        return Err("current observed entity absent/ambiguous".into());
    }
    Ok(matches[0])
}
fn mesh_values(mesh: &Mesh, attribute: bevy::mesh::MeshVertexAttribute) -> Result<Value, String> {
    match mesh.attribute(attribute) {
        Some(VertexAttributeValues::Float32x2(v)) => Ok(json!(v)),
        Some(VertexAttributeValues::Float32x3(v)) => Ok(json!(v)),
        Some(VertexAttributeValues::Float32x4(v)) => Ok(json!(v)),
        None => Ok(Value::Null),
        _ => Err("unsupported actual mesh attribute type".into()),
    }
}
pub fn bindings(world: &World, base: &Value, appearance: &Value) -> Result<Value, String> {
    let mut labels = Vec::new();
    for part in base["parts"].as_array().ok_or("full base parts absent")? {
        labels.push((
            part["name"].clone(),
            part["display_entity"].clone(),
            part["mesh_handle"].clone(),
            if part["name"] == "body" {
                appearance["body_material"].clone()
            } else {
                Value::Null
            },
            Some(part),
        ));
    }
    for item in appearance["accessories"]
        .as_array()
        .ok_or("production accessories absent")?
    {
        labels.push((
            item["name"].clone(),
            item["entity"].clone(),
            item["mesh_handle"].clone(),
            item["material_handle"].clone(),
            None,
        ));
    }
    let mut records = Vec::new();
    for (role, label, mesh_label, material_label, part) in labels {
        let entity = find(world, &label)?;
        let mesh_handle = &world.get::<Mesh3d>(entity).ok_or("actual Mesh3d absent")?.0;
        let material_handle = &world
            .get::<MeshMaterial3d<StandardMaterial>>(entity)
            .ok_or("actual material binding absent")?
            .0;
        if json!(format!("{:?}", mesh_handle.id())) != mesh_label
            || (!material_label.is_null()
                && json!(format!("{:?}", material_handle.id())) != material_label)
        {
            return Err("actual mesh/material differs from production snapshot identity".into());
        }
        let mesh = world
            .resource::<Assets<Mesh>>()
            .get(mesh_handle)
            .ok_or("actual mesh absent")?;
        let positions = mesh_values(mesh, Mesh::ATTRIBUTE_POSITION)?;
        let normals = mesh_values(mesh, Mesh::ATTRIBUTE_NORMAL)?;
        let tangents = mesh_values(mesh, Mesh::ATTRIBUTE_TANGENT)?;
        let uv = mesh_values(mesh, Mesh::ATTRIBUTE_UV_0)?;
        let indices = mesh
            .indices()
            .ok_or("actual indices absent")?
            .iter()
            .collect::<Vec<_>>();
        let global = world
            .get::<GlobalTransform>(entity)
            .ok_or("actual global absent")?
            .to_matrix()
            .to_cols_array();
        if positions.is_null() || normals.is_null() {
            return Err("actual positions/normals absent".into());
        }
        if let Some(part) = part {
            if positions != part["positions"]
                || normals != part["normals"]
                || tangents != part["tangents"]
                || json!(indices) != part["indices"]
                || json!(global) != part["display_transform"]
            {
                return Err("actual bound base mesh differs from full production snapshot".into());
            }
        }
        let material = world
            .resource::<Assets<StandardMaterial>>()
            .get(material_handle)
            .ok_or("actual material absent")?;
        let image=material.base_color_texture.as_ref().map(|handle| {
            let image=world.resource::<Assets<Image>>().get(handle).ok_or("actual bound image absent")?;
            let pixels=image.data.as_ref().ok_or("actual bound CPU image bytes absent")?;
            Ok::<_,String>(json!({"image_handle":format!("{:?}",handle.id()),"width":image.width(),"height":image.height(),"format":format!("{:?}",image.texture_descriptor.format),"sampler":format!("{:?}",image.sampler),"decoded_bytes":pixels.len(),"decoded_rgba_sha256":appearance_sha256(pixels),"scope":"hash of actual CPU image bytes through current material handle; RGBA byte array omitted to avoid repeating immutable multi-MiB images in69frames; not GPU texel readback"}))
        }).transpose()?;
        records.push(json!({"role":role,"entity":label,"mesh_handle":mesh_label,"material_handle":format!("{:?}",material_handle.id()),"positions_sha256":appearance_sha256(positions.to_string().as_bytes()),"normals_sha256":appearance_sha256(normals.to_string().as_bytes()),"uv_sha256":appearance_sha256(uv.to_string().as_bytes()),"indices_sha256":appearance_sha256(serde_json::to_string(&indices).map_err(|e|e.to_string())?.as_bytes()),"positions":positions,"normals":normals,"tangents":tangents,"uv_0":uv,"indices":indices,"display_transform":global,"material":{"full_standard_material_debug":format!("{material:?}"),"base_color":format!("{:?}",material.base_color),"unlit":material.unlit,"alpha_mode":format!("{:?}",material.alpha_mode),"cull_mode":format!("{:?}",material.cull_mode),"double_sided":material.double_sided,"roughness":material.perceptual_roughness,"metallic":material.metallic,"image":image},"visibility":format!("{:?}",world.get::<Visibility>(entity)),"inherited_visibility":world.get::<InheritedVisibility>(entity).map(|v|v.get()),"view_visibility":world.get::<ViewVisibility>(entity).map(|v|v.get()),"scope":"actual entity->Mesh3d/StandardMaterial/Image CPU assets; already posed metres; global applied once only by renderer; no overrides/GPU ownership claim"}));
    }
    Ok(json!(records))
}
pub fn base_summary(base: &Value) -> Value {
    let parts=base["parts"].as_array().map(|parts|parts.iter().map(|p|json!({"name":p["name"],"display_entity":p["display_entity"],"mesh_handle":p["mesh_handle"],"vertices":p["positions"].as_array().map(Vec::len),"indices":p["indices"].as_array().map(Vec::len)})).collect::<Vec<_>>());
    json!({"backend":base["backend"],"asset_id":base["asset_id"],"profile_id":base["profile_id"],"generation":base["generation"],"revision":base["revision"],"parameters":base["parameters"],"sample":base["sample"],"bone_count":base["bones"].as_array().map(Vec::len),"parts":parts,"full_snapshot":"frame.full_base retains exact unmodified production Value"})
}
pub fn camera(world: &World) -> Value {
    let cameras = world
        .iter_entities()
        .filter(|e| e.contains::<nvwa_runtime::SceneCamera>())
        .collect::<Vec<_>>();
    if cameras.len() != 1 {
        return json!({"error":"exactly one SceneCamera required"});
    }
    let entity = &cameras[0];
    json!({"entity":format!("{:?}",entity.id()),"global_transform":entity.get::<GlobalTransform>().map(|t|t.to_matrix().to_cols_array()),"projection":entity.get::<Projection>().map(|p|format!("{p:?}")),"msaa":entity.get::<Msaa>().map(|m|format!("{m:?}")),"viewport":entity.get::<Camera>().and_then(|c|c.physical_viewport_size()).map(|v|v.to_array()),"sub_camera_view":entity.get::<Camera>().map(|c|format!("{:?}",c.sub_camera_view)),"active":entity.get::<Camera>().map(|c|c.is_active)})
}
pub fn environment(world: &World) -> Value {
    let lights=world.iter_entities().filter_map(|e|e.get::<DirectionalLight>().map(|l|json!({"entity":format!("{:?}",e.id()),"light":format!("{l:?}"),"global_transform":e.get::<GlobalTransform>().map(|t|t.to_matrix().to_cols_array())}))).collect::<Vec<_>>();
    json!({"directional_lights":lights,"ambient":world.get_resource::<GlobalAmbientLight>().map(|a|format!("{a:?}")),"clear_color":world.get_resource::<ClearColor>().map(|c|format!("{c:?}"))})
}
