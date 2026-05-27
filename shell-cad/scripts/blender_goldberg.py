"""Generate Goldberg T=81 in Blender via the Geodesic Domes addon, export OBJ.

Usage:
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python shell-cad/scripts/blender_goldberg.py
"""
import bpy

REPO_ROOT = "/Users/katano/work/FPC-isolation-sphere"
OUT_OBJ = f"{REPO_ROOT}/shell-cad/output/goldberg_t81_addon.obj"

FREQUENCY = 9  # m for Goldberg G(m, 0)
RADIUS = 50.0  # Blender units (= mm by convention for this project)

# Clear default scene objects
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Enable addon
bpy.ops.preferences.addon_enable(module="add_mesh_geodesic_domes")

# Generate Goldberg
bpy.ops.mesh.generate_geodesic_dome(
    geodesic_types="Geodesic",        # base form is geodesic ...
    base_type="Icosahedron",
    geodesic_class="Class_1",
    orientation="PointUp",
    spherical_flat="spherical",
    tri_hex_star="tri",
    frequency=FREQUENCY,
    radius=RADIUS,
    dual=True,                        # ... then take the dual → Goldberg
)

# Find the resulting object
obj = bpy.context.active_object
print(f"Active object: {obj.name if obj else None}")
if obj is None:
    # Fallback: pick last mesh in scene
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    print(f"Meshes in scene: {[m.name for m in meshes]}")
    obj = meshes[-1] if meshes else None

assert obj is not None, "Geodesic Dome operator did not create a mesh"

mesh = obj.data
n_verts = len(mesh.vertices)
n_faces = len(mesh.polygons)
n_pent = sum(1 for p in mesh.polygons if len(p.vertices) == 5)
n_hex = sum(1 for p in mesh.polygons if len(p.vertices) == 6)
other = sorted(set(len(p.vertices) for p in mesh.polygons) - {5, 6})

print(f"--- addon-generated mesh stats ---")
print(f"  vertices : {n_verts}")
print(f"  faces    : {n_faces}")
print(f"  pentagons: {n_pent}")
print(f"  hexagons : {n_hex}")
if other:
    print(f"  other face sizes: {other}")

# Sanity: check vertices lie on a sphere of given radius
import math
radii = [math.sqrt(v.co.x**2 + v.co.y**2 + v.co.z**2) for v in mesh.vertices]
print(f"  vertex radius min/max: {min(radii):.4f} / {max(radii):.4f}")

# Export OBJ (Blender 4.x uses wm.obj_export)
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.wm.obj_export(
    filepath=OUT_OBJ,
    export_selected_objects=True,
    apply_modifiers=True,
    export_triangulated_mesh=False,
)
print(f"  → wrote {OUT_OBJ}")
