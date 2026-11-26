# Blender ekransız deneme: düşük poligonlu, şık sekizgen sur kulesi (bpy) → .glb + önizleme
import bpy, math, bmesh, sys

OUT = "/root/is/blender/out"
import os
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def mat(ad, renk, rough=0.85):
    m = bpy.data.materials.new(ad)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*renk, 1.0)
    b.inputs["Roughness"].default_value = rough
    return m


TAS = mat("tas", (0.78, 0.70, 0.56))
TUGLA = mat("tugla", (0.62, 0.30, 0.20))
CATI = mat("cati", (0.55, 0.22, 0.14))
KOYU = mat("koyu", (0.08, 0.07, 0.06))


def silindir(ad, r, h, z, kenar, m, bevel=0.04):
    bpy.ops.mesh.primitive_cylinder_add(vertices=kenar, radius=r, depth=h, location=(0, 0, z + h / 2))
    o = bpy.context.object
    o.name = ad
    o.data.materials.append(m)
    if bevel > 0:
        md = o.modifiers.new("bevel", "BEVEL")
        md.width = bevel
        md.segments = 1
        md.limit_method = "ANGLE"
    return o


parcalar = []
# Gövde: taş ve tuğla hatıl katmanları (sekizgen)
z = 0.0
R = 3.2
for i, (h, m) in enumerate([(2.2, TAS), (0.35, TUGLA), (2.0, TAS), (0.35, TUGLA), (2.0, TAS), (0.35, TUGLA), (1.6, TAS)]):
    parcalar.append(silindir("govde_%d" % i, R + (0.02 if m == TUGLA else 0.0), h, z, 8, m))
    z += h
# Korniş + mazgal dişleri
parcalar.append(silindir("kornis", R + 0.25, 0.3, z, 8, TAS))
z += 0.3
for k in range(8):
    a = (k + 0.5) * math.tau / 8
    bpy.ops.mesh.primitive_cube_add(size=1, location=(math.cos(a) * (R + 0.05), math.sin(a) * (R + 0.05), z + 0.45))
    d = bpy.context.object
    d.scale = (0.55, 1.5, 0.9)
    d.rotation_euler[2] = a
    d.data.materials.append(TAS)
    md = d.modifiers.new("bevel", "BEVEL"); md.width = 0.04; md.segments = 1
    parcalar.append(d)
# Sivri çatı
bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=R - 0.3, radius2=0.0, depth=2.6, location=(0, 0, z + 1.3))
c = bpy.context.object
c.data.materials.append(CATI)
parcalar.append(c)
# Mazgal pencereleri (koyu, hafif içeri)
for k in range(4):
    a = k * math.tau / 4 + math.tau / 16
    for zz in (3.3, 6.0):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(math.cos(a) * (R - 0.05), math.sin(a) * (R - 0.05), zz))
        w = bpy.context.object
        w.scale = (0.2, 0.45, 0.9)
        w.rotation_euler[2] = a
        w.data.materials.append(KOYU)
        parcalar.append(w)

# Birleştir, düz gölgeleme
for o in bpy.context.scene.objects:
    o.select_set(o in parcalar)
bpy.context.view_layer.objects.active = parcalar[0]
for o in parcalar:
    bpy.context.view_layer.objects.active = o
    for md in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=md.name)
bpy.context.view_layer.objects.active = parcalar[0]
bpy.ops.object.join()
kule = bpy.context.object
kule.name = "Kule_Sekizgen"
for p in kule.data.polygons:
    p.use_smooth = False
tri = sum(len(p.vertices) - 2 for p in kule.data.polygons)
print("KULE ucgen=%d" % tri)

bpy.ops.export_scene.gltf(filepath=OUT + "/kule_sekizgen.glb", export_format="GLB", use_selection=True)
print("KULE glb yazildi")

# Önizleme: Cycles CPU, güneş + gökyüzü
cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
sc.collection.objects.link(cam)
cam.location = (17.0, -17.0, 9.5)
hedef = bpy.data.objects.new("hedef", None)
sc.collection.objects.link(hedef)
hedef.location = (0, 0, 6.2)
tc = cam.constraints.new("TRACK_TO")
tc.target = hedef
tc.track_axis = "TRACK_NEGATIVE_Z"
tc.up_axis = "UP_Y"
cam_data.lens = 40
sc.camera = cam
sun_d = bpy.data.lights.new("gunes", "SUN")
sun_d.energy = 4.0
sun = bpy.data.objects.new("gunes", sun_d)
sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(30))
w = bpy.data.worlds.new("dunya")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.72, 0.95, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
sc.world = w
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
yer = bpy.context.object
yer.data.materials.append(mat("yer", (0.45, 0.42, 0.30)))
sc.view_settings.view_transform = "Standard"
sc.render.engine = "CYCLES"
sc.cycles.samples = 24
sc.cycles.device = "CPU"
sc.render.resolution_x = 720
sc.render.resolution_y = 720
sc.render.filepath = OUT + "/kule_onizleme.png"
bpy.ops.render.render(write_still=True)
print("KULE onizleme yazildi")
