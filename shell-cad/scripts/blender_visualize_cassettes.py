"""Step 1b: Color faces of Goldberg T=81 by half-gore cassette.

10 half-gore cassettes = 5 longitudinal slices × N/S hemispheres.

Longitudinal slice boundaries are at θ = 18°, 90°, 162°, 234°, 306°
(midway between upper-ring pentagons at 0°,72°,... and lower-ring at 36°,108°,...).
Each slice contains 1 upper-ring + 1 lower-ring pentagon.

Color scheme:
  - hue   ~ longitudinal slice (5 hues)
  - light ~ hemisphere (N = saturated, S = light/pastel)

Usage:
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python shell-cad/scripts/blender_visualize_cassettes.py
"""
import math
from pathlib import Path

import bpy

REPO = Path("/Users/katano/work/FPC-isolation-sphere")
OBJ_PATH = REPO / "shell-cad" / "output" / "goldberg_t81.obj"
BLEND_PATH = REPO / "shell-cad" / "output" / "goldberg_t81_cassettes.blend"

# 5 base hues for longitudinal slices (N hemisphere uses these directly)
SLICE_COLORS_N = [
    (0.95, 0.25, 0.25, 1.0),  # red
    (1.00, 0.65, 0.10, 1.0),  # orange
    (0.30, 0.80, 0.30, 1.0),  # green
    (0.20, 0.55, 0.95, 1.0),  # blue
    (0.75, 0.30, 0.95, 1.0),  # purple
]


def lighten(rgba, t=0.55):
    r, g, b, a = rgba
    return (r * (1 - t) + t, g * (1 - t) + t, b * (1 - t) + t, a)


def make_material(name, rgba):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = rgba
    return mat


# Clear scene
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Import OBJ
bpy.ops.wm.obj_import(filepath=str(OBJ_PATH))
obj = bpy.context.selected_objects[0]
obj.name = "Goldberg_T81_Cassettes"
mesh = obj.data
print(f"Loaded: {len(mesh.vertices)} verts, {len(mesh.polygons)} faces")

# Create 10 cassette materials: Slice{i}_N then Slice{i}_S
mat_index = {}
for i, base in enumerate(SLICE_COLORS_N):
    mat_n = make_material(f"Slice{i}_N", base)
    mat_s = make_material(f"Slice{i}_S", lighten(base, 0.55))
    mesh.materials.append(mat_n)
    mesh.materials.append(mat_s)
    mat_index[(i, 0)] = len(mesh.materials) - 2
    mat_index[(i, 1)] = len(mesh.materials) - 1

# Polar pentagon (north / south pole) — special category, white
mat_polar = make_material("PolarPent", (1.0, 1.0, 1.0, 1.0))
mesh.materials.append(mat_polar)
MAT_POLAR_IDX = len(mesh.materials) - 1

# Polar detection threshold (radial distance from Z axis, in mm)
POLAR_R_THRESHOLD = 1.0


def classify(centroid) -> tuple[int, int]:
    """Return (slice_idx, hemi). slice_idx=-1 means polar (special)."""
    cx, cy, cz = centroid[0], centroid[1], centroid[2]
    r_axial = math.sqrt(cx * cx + cy * cy)
    hemi = 0 if cz >= 0.0 else 1
    if r_axial < POLAR_R_THRESHOLD:
        return -1, hemi
    az_deg = math.degrees(math.atan2(cy, cx))
    if az_deg < 0:
        az_deg += 360.0
    shifted = (az_deg + 54.0) % 360.0  # boundaries at 18° + k*72°
    return int(shifted // 72.0) % 5, hemi


counts: dict[tuple[int, int], dict[str, int]] = {
    (s, h): {"pent": 0, "hex": 0, "eq_hex": 0}
    for s in range(5) for h in range(2)
}
polar_count = [0, 0]  # [N, S]

for poly in mesh.polygons:
    s, h = classify(poly.center)
    if s < 0:
        poly.material_index = MAT_POLAR_IDX
        polar_count[h] += 1
        continue
    poly.material_index = mat_index[(s, h)]
    nv = len(poly.vertices)
    if nv == 5:
        counts[(s, h)]["pent"] += 1
    else:
        zs = [mesh.vertices[vi].co.z for vi in poly.vertices]
        if min(zs) < 0.0 < max(zs):
            counts[(s, h)]["eq_hex"] += 1
        else:
            counts[(s, h)]["hex"] += 1

print("\nCassette face distribution (10 half-gores + 2 polar):")
print(f"  {'cassette':>10}  {'pent':>4}  {'hex':>4}  {'eq_hex':>6}  {'total':>5}")
grand = 0
for s in range(5):
    for h in (0, 1):
        c = counts[(s, h)]
        total = c["pent"] + c["hex"] + c["eq_hex"]
        grand += total
        label = f"Slice{s}_{'N' if h == 0 else 'S'}"
        print(f"  {label:>10}  {c['pent']:>4}  {c['hex']:>4}  {c['eq_hex']:>6}  {total:>5}")
print(f"  {'Polar_N':>10}  {polar_count[0]:>4}  {0:>4}  {0:>6}  {polar_count[0]:>5}")
print(f"  {'Polar_S':>10}  {polar_count[1]:>4}  {0:>4}  {0:>6}  {polar_count[1]:>5}")
grand += polar_count[0] + polar_count[1]
print(f"  {'TOTAL':>10}  {'':>4}  {'':>4}  {'':>6}  {grand:>5}")

# Z=0 reference plane (wireframe)
bpy.ops.mesh.primitive_plane_add(size=120.0, location=(0, 0, 0))
plane = bpy.context.active_object
plane.name = "EquatorPlane"
plane.display_type = "WIRE"

# Camera + light
bpy.ops.object.light_add(type="SUN", location=(50, -50, 100))
bpy.context.active_object.data.energy = 3.0
bpy.ops.object.camera_add(location=(140, -140, 90), rotation=(1.05, 0.0, 0.785))
bpy.context.scene.camera = bpy.context.active_object

BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
print(f"\n  → wrote {BLEND_PATH}")
