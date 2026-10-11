"""Original Nvwa M0 fixture. Run with Blender 3.3+: blender -b -t 2 --python this.py.

No imported geometry, textures, motion capture, trained model, or third-party asset.
All coordinates, shape-key displacement functions, and animation poses are authored
here. CC0 applies to this fixture and its generation sources only.
"""
import bpy
import math
import os
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
OUT = os.path.abspath(os.environ.get('NVWA_FIXTURE_OUTPUT', os.path.join(ROOT, 'assets/fixtures')))
os.makedirs(OUT, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)
scene = bpy.context.scene
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 97

def material(name, color, roughness=0.65):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    return mat

skin = material('Skin — warm clay', (0.62, 0.30, 0.16))
shirt = material('Opaque teal tunic', (0.035, 0.28, 0.30))
pants = material('Opaque indigo trousers', (0.07, 0.10, 0.19))
shoe = material('Charcoal shoes', (0.025, 0.032, 0.05))
mouth = material('Facial features', (0.07, 0.018, 0.012))
white = material('Eye whites', (0.92, 0.89, 0.81))
iris = material('Eyes — dark brown', (0.025, 0.012, 0.006), .4)

parts = []
def ellipsoid(name, position, scale):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=position)
    ob = bpy.context.object
    ob.name = name
    ob.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    parts.append(ob)
    return ob

def capsule(name, a, b, radius):
    a, b = Vector(a), Vector(b)
    ob = ellipsoid(name, (a+b)/2, (radius, radius, (b-a).length/2+radius*.6))
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = Vector((0,0,1)).rotation_difference(b-a)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

# The primitives are construction inputs only: voxel remesh unifies them into
# ONE continuous surface before skinning. No sphere/capsule body parts survive.
ellipsoid('pelvis input', (0,0,.85), (.235,.145,.17))
ellipsoid('waist input', (0,0,1.01), (.185,.135,.23))
ellipsoid('chest input', (0,0,1.22), (.275,.16,.25))
capsule('neck input', (0,0,1.37), (0,0,1.49), .09)
ellipsoid('head input', (0,-.015,1.65), (.185,.16,.225))
ellipsoid('jaw input', (0,-.038,1.51), (.132,.12,.11))
ellipsoid('nose input', (0,-.171,1.625), (.035,.064,.055))
for side in (-1,1):
    ellipsoid('ear input', (side*.184,-.007,1.64), (.035,.035,.063))
    capsule('upper arm input', (side*.235,0,1.33), (side*.43,0,1.13), .080)
    capsule('forearm input', (side*.43,0,1.13), (side*.57,-.01,.94), .060)
    ellipsoid('hand input', (side*.605,-.016,.895), (.066,.041,.095))
    capsule('thumb input', (side*.576,-.044,.936), (side*.560,-.061,.875), .027)
    capsule('thigh input', (side*.125,0,.86), (side*.145,0,.50), .103)
    capsule('shin input', (side*.145,0,.50), (side*.155,0,.14), .075)
    ellipsoid('foot input', (side*.155,-.055,.092), (.087,.145,.075))
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:
    ob.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
body = bpy.context.object
body.name = 'Nvwa continuous clothed surface'
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
remesh = body.modifiers.new('Union into continuous topology', 'REMESH')
remesh.mode = 'VOXEL'
remesh.voxel_size = .013
remesh.use_smooth_shade = True
bpy.ops.object.modifier_apply(modifier=remesh.name)
smooth = body.modifiers.new('Round voxel surface', 'SMOOTH')
smooth.factor = .65
smooth.iterations = 5
bpy.ops.object.modifier_apply(modifier=smooth.name)
for mat in (skin, shirt, pants, shoe, mouth):
    body.data.materials.append(mat)
for p in body.data.polygons:
    p.use_smooth = True
    c = p.center
    p.material_index = 0 if c.z > 1.435 or (abs(c.x) > .545 and c.z < 1.03) else (1 if c.z > .825 else 2)
    if c.z < .155:
        p.material_index = 3
    # A small painted mouth and brows live on the continuous head topology.
    if c.y < -.12 and abs(c.x) < .079 and abs(c.z-(1.556+.20*c.x*c.x)) < .009:
        p.material_index = 4
    if c.y < -.124 and .052 < abs(c.x) < .133 and abs(c.z-1.727) < .009:
        p.material_index = 4

def clamp(v):
    return max(0.0, min(1.0, v))
def window(v, center, width):
    return max(0, 1-abs(v-center)/width)**2

body.shape_key_add(name='Basis')
for name in ('jaw_width', 'nose_width', 'smile', 'shoulder_width'):
    key = body.shape_key_add(name=name)
    for point in key.data:
        x,y,z = point.co
        if name == 'jaw_width':
            mask = window(z,1.505,.135) * clamp((.205-abs(x))/.07)
            point.co.x += x * .52 * mask
        elif name == 'nose_width':
            mask = window(z,1.625,.08) * clamp((-y-.125)/.055) * clamp((.065-abs(x))/.025)
            point.co.x += x * 2.0 * mask
            point.co.y -= .035 * mask
        elif name == 'smile':
            mask = window(z,1.562,.09) * clamp((-y-.065)/.07) * window(abs(x),.062,.09)
            point.co.z += .043 * mask * clamp(abs(x)/.055)
            point.co.y -= .020 * mask
        else:
            mask = window(z,1.27,.36) * clamp((abs(x)-.07)/.13)
            point.co.x += math.copysign(.090*mask,x)

# Explicit rig with smooth normalized weights. Body part routing keeps nearby
# arms/legs from accidentally acquiring spine/opposite-limb influences.
bpy.ops.object.armature_add(enter_editmode=True, location=(0,0,0))
rig = bpy.context.object
rig.name = 'Nvwa humanoid rig'
arm = rig.data
arm.name = 'Nvwa original skeleton'
arm.edit_bones.remove(arm.edit_bones[0])
segments = {}
def bone(name, a, b, parent=None):
    eb = arm.edit_bones.new(name)
    eb.head, eb.tail = a,b
    # Make local Z point toward the viewer (-Y). This gives arm lift a clear
    # local-Z rotation axis, and upright torso yaw a local-Y axis.
    eb.align_roll(Vector((0,-1,0)))
    if parent:
        eb.parent = arm.edit_bones[parent]
    segments[name] = (Vector(a),Vector(b))
bone('root',(0,0,.08),(0,0,.28))
bone('pelvis',(0,0,.83),(0,0,1.00),'root')
bone('spine',(0,0,1.00),(0,0,1.19),'pelvis')
bone('chest',(0,0,1.19),(0,0,1.38),'spine')
bone('neck',(0,0,1.38),(0,0,1.48),'chest')
bone('head',(0,0,1.48),(0,0,1.83),'neck')
for side,suffix in ((-1,'L'),(1,'R')):
    bone('upper_arm.'+suffix,(side*.235,0,1.33),(side*.43,0,1.13),'chest')
    bone('forearm.'+suffix,(side*.43,0,1.13),(side*.57,-.01,.94),'upper_arm.'+suffix)
    bone('hand.'+suffix,(side*.57,-.01,.94),(side*.615,-.015,.85),'forearm.'+suffix)
    bone('thigh.'+suffix,(side*.125,0,.86),(side*.145,0,.50),'pelvis')
    bone('shin.'+suffix,(side*.145,0,.50),(side*.155,0,.14),'thigh.'+suffix)
    bone('foot.'+suffix,(side*.155,0,.14),(side*.155,-.15,.075),'shin.'+suffix)
bpy.ops.object.mode_set(mode='OBJECT')

def segment_distance(point,a,b):
    diff = b-a
    return (point-(a+diff*clamp((point-a).dot(diff)/diff.length_squared))).length

def skin_object(ob, head_only=False):
    groups = {name:ob.vertex_groups.new(name=name) for name in segments}
    for v in ob.data.vertices:
        if head_only:
            weights = [('head',1.0)]
        else:
            x,y,z = v.co
            suffix = 'L' if x < 0 else 'R'
            if z < .80:
                names = ['thigh.'+suffix,'shin.'+suffix,'foot.'+suffix,'pelvis']
            elif abs(x) > .285 and z < 1.43:
                names = ['upper_arm.'+suffix,'forearm.'+suffix,'hand.'+suffix,'chest']
            elif z > 1.40:
                names = ['head','neck','chest']
            else:
                names = ['pelvis','spine','chest','neck']
            nearest = sorted([(name,segment_distance(v.co,*segments[name])) for name in names], key=lambda pair:pair[1])[:4]
            # Compact Gaussian with a small tail, normalized to unity.
            weights = [(name,math.exp(-((dist-nearest[0][1])/.070)**2)) for name,dist in nearest]
            total = sum(weight for name,weight in weights)
            weights = [(name,weight/total) for name,weight in weights if weight/total > .0001]
            total = sum(weight for name,weight in weights)
            weights = [(name,weight/total) for name,weight in weights]
        for name,weight in weights:
            groups[name].add([v.index],weight,'REPLACE')
    mod = ob.modifiers.new('Smooth skeleton deformation','ARMATURE')
    mod.object = rig
    ob.parent = rig
skin_object(body)

# Small separate eyeballs are permitted; they are skinned to the head bone.
parts.clear()
for side in (-1,1):
    eye = ellipsoid('Eye white '+str(side),(side*.078,-.148,1.672),(.043,.026,.039))
    eye.data.materials.append(white)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    skin_object(eye,True)
    pupil = ellipsoid('Eye pupil '+str(side),(side*.078,-.172,1.672),(.019,.009,.022))
    pupil.data.materials.append(iris)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    skin_object(pupil,True)
    for ob in (eye,pupil):
        for p in ob.data.polygons:
            p.use_smooth=True

# Human-authored animation presets. One named NLA strip for each glTF clip.
def reset_pose():
    for pb in rig.pose.bones:
        pb.rotation_mode='XYZ'
        pb.rotation_euler=(0,0,0)
        pb.location=(0,0,0)
def make_action(name, frames, pose):
    action=bpy.data.actions.new(name)
    rig.animation_data_create()
    rig.animation_data.action=action
    for frame in frames:
        reset_pose()
        pose((frame-1)/24)
        for pb in rig.pose.bones:
            pb.keyframe_insert(data_path='rotation_euler',frame=frame,group=pb.name)
            pb.keyframe_insert(data_path='location',frame=frame,group=pb.name)
    for curve in action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation='LINEAR'
    rig.animation_data.action=None
    track=rig.animation_data.nla_tracks.new()
    track.name=name
    strip=track.strips.new(name,1,action)
    strip.name=name
    return action

def idle(t):
    phase=math.sin(2*math.pi*t/3)
    rig.pose.bones['chest'].rotation_euler.x=.020*phase
    rig.pose.bones['head'].rotation_euler.z=.026*phase
    rig.pose.bones['upper_arm.L'].rotation_euler.y=.025*phase
    rig.pose.bones['upper_arm.R'].rotation_euler.y=-.025*phase
    rig.pose.bones['pelvis'].location.y=.006*phase

def wave(t):
    amount=min(1,t/.6,(3-t)/.6)
    amount=max(0,amount)
    rig.pose.bones['upper_arm.R'].rotation_euler.z=1.95*amount
    rig.pose.bones['forearm.R'].rotation_euler.z=.28*amount
    rig.pose.bones['hand.R'].rotation_euler.z=.40*amount*math.sin(t*math.pi*4)
    rig.pose.bones['head'].rotation_euler.z=-.075*amount

def turn(t):
    rig.pose.bones['root'].rotation_euler.y=2*math.pi*t/4

make_action('idle',range(1,74,6),idle)
make_action('wave',range(1,74,3),wave)
make_action('turn',range(1,98,6),turn)
reset_pose()
scene.frame_set(1)
for track in rig.animation_data.nla_tracks:
    track.mute=True

# Measure source continuity and deformation before glTF material splits.
adj=[[] for _ in body.data.vertices]
for edge in body.data.edges:
    a,b=edge.vertices
    adj[a].append(b); adj[b].append(a)
unseen=set(range(len(adj)))
components=[]
while unseen:
    stack=[unseen.pop()]; count=0
    while stack:
        node=stack.pop(); count+=1
        for other in adj[node]:
            if other in unseen:
                unseen.remove(other); stack.append(other)
    components.append(count)
import json
proof={'source_vertices':len(body.data.vertices),'source_polygons':len(body.data.polygons),
       'continuous_surface_components':components,'bones':list(segments),
       'morph_order':['jaw_width','nose_width','smile','shoulder_width'],
       'morph_nonzero_vertices':{key.name:sum((a.co-b.co).length>1e-7 for a,b in zip(key.data,body.data.shape_keys.key_blocks[0].data)) for key in list(body.data.shape_keys.key_blocks)[1:]},
       'animation_authorship':'Original manually authored preset poses; not AI generated motion',
       'blender_version':bpy.app.version_string}
with open(os.path.join(OUT,'source-structure.json'),'w') as handle:
    json.dump(proof,handle,indent=2)

# Export only original fixture surfaces and rig, excluding render setup.
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True); body.select_set(True)
for ob in parts:
    ob.select_set(True)
bpy.context.view_layer.objects.active=rig
for track in rig.animation_data.nla_tracks:
    track.mute=False
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'nvwa-humanoid.blend'))
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,'nvwa-humanoid.glb'),export_format='GLB',
    use_selection=True,export_animations=True,export_nla_strips=True,
    export_force_sampling=True,export_frame_range=False,export_skins=True,
    export_morph=True,export_morph_normal=True,export_morph_tangent=False,
    export_yup=True,export_materials='EXPORT',export_extras=True)
print('NVWA_SOURCE_PROOF '+json.dumps(proof))

# Optional CPU stills for authoring inspection, never runtime/GPU measurements.
if os.environ.get('NVWA_RENDER_PREVIEWS') == '1':
    for track in rig.animation_data.nla_tracks:
        track.mute=True
    reset_pose(); scene.frame_set(1)
    scene.render.engine='CYCLES'
    scene.cycles.device='CPU'
    scene.cycles.samples=16
    scene.render.resolution_x=600; scene.render.resolution_y=650
    scene.render.resolution_percentage=100
    scene.world.color=(.14,.14,.14)
    bpy.ops.object.camera_add(location=(2.8,-5.5,2.5))
    camera=bpy.context.object
    camera.rotation_euler=(Vector((0,0,.97))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO'; camera.data.ortho_scale=2.18
    scene.camera=camera
    for location,power,size in [((2,-3,4),450,4),((-3,-2,2),260,3),((0,3,3),350,3)]:
        bpy.ops.object.light_add(type='AREA',location=location)
        light=bpy.context.object
        light.data.energy=power; light.data.size=size
        light.rotation_euler=(Vector((0,0,1))-light.location).to_track_quat('-Z','Y').to_euler()
    for label,key in [('base',None)]+[(name,name) for name in proof['morph_order']]:
        for kb in list(body.data.shape_keys.key_blocks)[1:]:
            kb.value=1 if kb.name==key else 0
        scene.render.filepath=os.path.join(OUT,'preview-'+label+'.png')
        bpy.ops.render.render(write_still=True)
    for kb in list(body.data.shape_keys.key_blocks)[1:]:
        kb.value=0
    rig.animation_data.action=bpy.data.actions['wave']
    scene.frame_set(25)
    scene.render.filepath=os.path.join(OUT,'preview-wave.png')
    bpy.ops.render.render(write_still=True)
