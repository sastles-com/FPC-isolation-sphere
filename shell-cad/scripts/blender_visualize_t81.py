"""Step 1: Visualize goldberg_t81.obj in Blender with face classification.

Imports the Goldberg T=81 mesh, color-codes the 812 faces, adds a Z=0
reference plane (wireframe), and saves a .blend file for visual inspection.

Color scheme:
  - 12 pentagons              -> blue
  - 800 hexagons (regular)    -> light gray
  - 90 hexagons crossing Z=0  -> red

Usage:
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python shell-cad/scripts/blender_visualize_t81.py

Open the resulting .blend in Blender GUI to inspect.
"""
import bpy
from pathlib import Path

REPO = Path("/Users/katano/work/FPC-isolation-sphere")
OBJ_PATH = REPO / "shell-cad" / "output" / "goldberg_t81.obj"
BLEND_PATH = REPO / "shell-cad" / "output" / "goldberg_t81.blend"

# Clear scene
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Import OBJ (Blender 4.x)
bpy.ops.wm.obj_import(filepath=str(OBJ_PATH))
obj = bpy.context.selected_objects[0]
obj.name = "Goldberg_T81"
mesh = obj.data
print(f"Loaded: {len(mesh.vertices)} verts, {len(mesh.polygons)} faces")


def make_material(name: str, rgba: tuple[float, float, float, float]):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    # Also drive Principled BSDF base color for rendered view
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = rgba
    return mat


mat_pent = make_material("Pentagon", (0.20, 0.40, 0.90, 1.0))
mat_hex = make_material("Hexagon", (0.70, 0.70, 0.70, 1.0))
mat_eq = make_material("EquatorHex", (0.95, 0.20, 0.20, 1.0))

mesh.materials.append(mat_pent)
mesh.materials.append(mat_hex)
mesh.materials.append(mat_eq)

n_pent = n_hex = n_eq = 0
for poly in mesh.polygons:
    nv = len(poly.vertices)
    if nv == 5:
        poly.material_index = 0
        n_pent += 1
    elif nv == 6:
        zs = [mesh.vertices[vi].co.z for vi in poly.vertices]
        if min(zs) < 0.0 < max(zs):
            poly.material_index = 2
            n_eq += 1
        else:
            poly.material_index = 1
            n_hex += 1
    else:
        print(f"  ⚠ unexpected face size {nv}")

print(f"Classified: pent={n_pent}  hex={n_hex}  equator-straddling hex={n_eq}")

# Z=0 reference plane as wireframe (visible but does not occlude)
bpy.ops.mesh.primitive_plane_add(size=120.0, location=(0, 0, 0))
plane = bpy.context.active_object
plane.name = "EquatorPlane"
plane.display_type = "WIRE"

# Lighting + camera (so the saved .blend opens with a sensible view)
bpy.ops.object.light_add(type="SUN", location=(50, -50, 100))
sun = bpy.context.active_object
sun.data.energy = 3.0

bpy.ops.object.camera_add(location=(140, -140, 90), rotation=(1.05, 0.0, 0.785))
cam = bpy.context.active_object
bpy.context.scene.camera = cam

# Save as .blend
BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
print(f"  → wrote {BLEND_PATH}")
