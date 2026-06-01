"""Step 2: Build 10 half-gore cassettes whose boundaries follow Goldberg edges.

Each cassette is the union of Goldberg G(9,0) faces assigned to it by the same
classify() rule as blender_visualize_cassettes.py:
  - faces whose centroid lies within POLAR_R_THRESHOLD mm of the Z axis
    are the 2 polar pentagons (excluded from the 10 cassettes — they become
    the pole cutout where the polar PCB drops in)
  - all other faces: longitudinal slice 0..4 by shifted azimuth, hemisphere
    by sign(centroid_z)

Each cassette mesh is built directly from:
  - outer Goldberg face vertices at r = 50 mm (φ100 outer)
  - inner vertices at r = 45 mm (φ90 inner) by radial scaling (same connectivity)
  - rim quads along the cassette boundary edges connecting outer to inner

No Solidify or Boolean operations — geometry is exact, watertight, and
neighbouring cassettes share boundary vertices exactly so they mate perfectly.

Also produces radial cylinders from origin to each face centroid:
  - 12 pentagon centroids → Φ2.5 mm cylinders (matches M2.5 clamp-screw nominal,
    non-polar pent = clamp-screw axes, polar pent = polar PCB axes)
  - 800 hexagon centroids → Φ3 mm cylinders (radial axes through each LED
    position; can be used as Boolean Diff cutters for straight LED through-holes
    before adding the flared aperture cones)

Cylinders are built directly via from_pydata (no bpy.ops per cylinder), and all
of one type are combined into a single mesh object for fast scene iteration.

Outputs (shell-cad/output/):
  cassette_slice{0..4}_{N,S}.stl   10 cassettes (Goldberg-aligned, zigzag boundary)
  pent_axes.stl                    12 Φ2.5 mm radial cylinders to pent centroids
  hex_axes.stl                     800 Φ3   mm radial cylinders to hex centroids
  hex_pyramids.stl                 800 hex pyramids (tapered aperture wells)
  shell_cassettes.blend            Blender scene for inspection

Usage:
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python shell-cad/scripts/blender_make_cassettes.py
"""
import math
import sys
from collections import defaultdict
from pathlib import Path

import bpy

REPO = Path("/Users/katano/work/FPC-isolation-sphere")
sys.path.insert(0, str(REPO / "shell-cad" / "scripts"))
from goldberg import goldberg  # noqa: E402
from hex_pyramids import build_all_pyramids  # noqa: E402

OUT_DIR = REPO / "shell-cad" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

M = 9                       # Goldberg G(9,0) → T = 81
R_OUTER = 50.0              # mm, φ100 outer
R_INNER = 45.0              # mm, φ90 inner (radial wall = 5 mm)
POLAR_R_THRESHOLD = 1.0     # mm; matches blender_visualize_cassettes.py
N_SLICES = 5
AZ_SHIFT_DEG = 54.0         # matches blender_visualize_cassettes.py:
                            # slice 0 = az ∈ [306°, 18°] (wrap), slice 1 = [18°, 90°], ...
PENT_CYL_DIAMETER = 2.5     # mm, Φ2.5 cylinder along origin→pent-centroid axis
HEX_CYL_DIAMETER = 4.0      # mm, Φ3 cylinder along origin→hex-centroid axis
CYL_SEGMENTS = 16           # cylinder side facets (shared)

# Hexagonal pyramids (六角錐 / tapered aperture wells) — one per hex face.
# Base sits on the outer shell (r = R_OUTER); apex is PYRAMID_L_H mm inward.
# These coexist with the Φ3 hex cylinders (cone = aperture well, cylinder = LED
# bore) and mirror the cutter pair used in aperture_boolean_demo.py.
PYRAMID_L_H = 8.0           # mm, inward depth of apex from base centroid
PYRAMID_BASE_R = None       # None → use R_OUTER (base on outer shell)
PYRAMID_BEVEL = 0.0         # mm, edge bevel (0 = sharp; ~0.5 for chamfer)

# Mother ring (equator donut PCB, flat gold pads only, mounted on the core).
# Flat annulus centred on z=0; north pogo pins press its top face, south its
# bottom face. Thickness 2.0 mm chosen over standard 1.6 mm for ~1.95x bending
# stiffness (∝ t^3) so distributed pogo load doesn't deflect it (2026-06-01).
MOTHER_RING_ENABLE = True
MOTHER_RING_THICKNESS = 2.0   # mm (standard 1.6; 2.0 for pogo-load stiffness)
MOTHER_RING_OUTER_R = 44.0    # mm, just inside the inner shell (r=45) at equator
MOTHER_RING_INNER_R = 28.0    # mm, placeholder until core size (Q31) is fixed
MOTHER_RING_SEGMENTS = 64

# Scripts embedded into the .blend (visible/runnable in the Scripting tab).
#   - CORE_SCRIPTS   : always embedded so the blend can regenerate itself
#   - script_*.py    : any file in shell-cad/scripts/ with this prefix is
#                      auto-embedded. Name a new tool "script_<name>.py" and
#                      drop it in — no edits here needed.
CORE_SCRIPTS = [
    "blender_make_cassettes.py",   # this generator
    "goldberg.py",                  # dependency
    "hex_pyramids.py",              # dependency
]
SCRIPT_PREFIX = "script_"           # auto-embed glob: shell-cad/scripts/script_*.py


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for col in (bpy.data.meshes, bpy.data.materials):
        for it in list(col):
            if it.users == 0:
                col.remove(it)
    # Remove leftover (now-empty) collections so re-runs start clean
    for coll in list(bpy.data.collections):
        if coll.users == 0 or len(coll.objects) == 0:
            bpy.data.collections.remove(coll)


def get_or_create_collection(name: str):
    """Return a scene-linked collection, creating it on first use."""
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def face_centroid(V, f):
    return tuple(sum(V[i][k] for i in f) / len(f) for k in range(3))


def classify(centroid):
    """Return ('polar', hemi) for the 2 pole pents, else (slice_idx, hemi)."""
    cx, cy, cz = centroid
    r_axial = math.sqrt(cx * cx + cy * cy)
    hemi = 0 if cz >= 0.0 else 1
    if r_axial < POLAR_R_THRESHOLD:
        return ("polar", hemi)
    az_deg = math.degrees(math.atan2(cy, cx))
    if az_deg < 0.0:
        az_deg += 360.0
    shifted = (az_deg + AZ_SHIFT_DEG) % 360.0
    slice_idx = int(shifted // (360.0 / N_SLICES)) % N_SLICES
    return (slice_idx, hemi)


def build_cassette_solid(V_outer, V_inner, F, face_indices, name, collection=None):
    """Closed solid from a set of Goldberg faces.

    Geometry:
      verts[0..n-1]   = outer Goldberg vertices used by these faces (r = R_OUTER)
      verts[n..2n-1]  = inner Goldberg vertices, same connectivity (r = R_INNER)
      outer faces     = original CCW winding (outward normal radially out)
      inner faces     = reversed winding (outward normal radially in = away from material)
      rim quads       = along boundary edges (edges appearing in only one face)
    """
    used = set()
    for fi in face_indices:
        for vi in F[fi]:
            used.add(vi)
    used_list = sorted(used)
    remap = {old: new for new, old in enumerate(used_list)}
    n = len(used_list)

    verts = [tuple(V_outer[i]) for i in used_list]
    verts += [tuple(V_inner[i]) for i in used_list]

    faces = []
    # Outer faces (CCW from outside, original winding)
    for fi in face_indices:
        faces.append([remap[vi] for vi in F[fi]])
    # Inner faces (reverse winding so normal points inward toward sphere center,
    # which is outward from the cassette material)
    for fi in face_indices:
        faces.append([remap[vi] + n for vi in reversed(F[fi])])

    # Collect oriented boundary edges. For each face, traverse its edges as (a→b).
    # An edge appears in only one face iff it's on the cassette boundary.
    edge_dirs = defaultdict(list)  # unordered key → list of (a, b) directed traversals
    for fi in face_indices:
        f = F[fi]
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            edge_dirs[tuple(sorted((a, b)))].append((a, b))
    for key, ab_list in edge_dirs.items():
        if len(ab_list) == 1:
            a, b = ab_list[0]
            # Rim quad: outer_a → outer_b → inner_b → inner_a
            # The outer edge a→b is CCW on the outer face (normal radially outward).
            # The rim's outward normal should point laterally away from the cassette.
            # Going outer_a → outer_b → inner_b → inner_a traces CCW when viewed
            # from outside the rim (lateral outward direction).
            faces.append([remap[a], remap[b], remap[b] + n, remap[a] + n])

    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.validate(verbose=False)
    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.collection).objects.link(obj)
    return obj


def cylinder_mesh_data(p0, p1, radius: float, n_segs: int = CYL_SEGMENTS):
    """Return (verts, faces) for a closed, capped cylinder from p0 to p1.

    p0, p1: 3-tuples (start/end of the cylinder axis in world coords)
    Faces are indexed from 0; caller offsets when combining.
    """
    import numpy as np
    a = np.asarray(p0, dtype=float)
    b = np.asarray(p1, dtype=float)
    axis = b - a
    length = float(np.linalg.norm(axis))
    axis_hat = axis / length

    # Orthonormal basis (u, v) in the plane perpendicular to axis_hat
    ref = np.array([0.0, 0.0, 1.0]) if abs(axis_hat[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(axis_hat, ref)
    u /= np.linalg.norm(u)
    v = np.cross(axis_hat, u)

    verts = []
    # Ring 0 at p0 (indices 0 .. n-1)
    for i in range(n_segs):
        ang = 2.0 * math.pi * i / n_segs
        verts.append(tuple(a + radius * (math.cos(ang) * u + math.sin(ang) * v)))
    # Ring 1 at p1 (indices n .. 2n-1)
    for i in range(n_segs):
        ang = 2.0 * math.pi * i / n_segs
        verts.append(tuple(b + radius * (math.cos(ang) * u + math.sin(ang) * v)))
    # Cap centers: 2n = bottom (at p0), 2n+1 = top (at p1)
    verts.append(tuple(a))
    verts.append(tuple(b))

    n = n_segs
    faces = []
    # Side quads, outward normal radial
    for i in range(n):
        i1 = (i + 1) % n
        faces.append([i, i1, n + i1, n + i])
    # Bottom cap (outward normal = -axis_hat), reversed winding
    bc = 2 * n
    for i in range(n):
        i1 = (i + 1) % n
        faces.append([bc, i1, i])
    # Top cap (outward normal = +axis_hat)
    tc = 2 * n + 1
    for i in range(n):
        i1 = (i + 1) % n
        faces.append([tc, n + i, n + i1])

    return verts, faces


def make_combined_cylinders(name: str, axis_endpoints, radius: float,
                            n_segs: int = CYL_SEGMENTS):
    """Build a single mesh object that contains multiple cylinders.

    axis_endpoints: iterable of (p0, p1) tuples.
    """
    all_verts = []
    all_faces = []
    for p0, p1 in axis_endpoints:
        verts, faces = cylinder_mesh_data(p0, p1, radius, n_segs=n_segs)
        offset = len(all_verts)
        all_verts.extend(verts)
        all_faces.extend([[i + offset for i in f] for f in faces])

    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(all_verts, [], all_faces)
    mesh.update()
    mesh.validate(verbose=False)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def embed_text(name: str, path: Path):
    """Embed a source file as a Text datablock so it appears in Blender's
    Scripting workspace (and can be re-run there via Text → Run Script).

    Re-imports an existing datablock of the same name to keep the blend in sync
    with the on-disk source on every regeneration.
    """
    if not path.exists():
        print(f"  ⚠ skip (not found): {name}")
        return None
    if name in bpy.data.texts:
        bpy.data.texts.remove(bpy.data.texts[name])
    txt = bpy.data.texts.new(name)
    txt.from_string(path.read_text())
    return txt


def make_combined_pyramids(name: str, pyramids):
    """Build a single mesh object from hex_pyramids.build_all_pyramids output.

    pyramids: list of (face_idx, verts (np.ndarray), tris (list[list[int]])).
    All pyramids are merged into one mesh (offset indices) for fast iteration.
    """
    all_verts = []
    all_faces = []
    for _fi, verts, tris in pyramids:
        offset = len(all_verts)
        all_verts.extend(tuple(v) for v in verts)
        all_faces.extend([[i + offset for i in t] for t in tris])

    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(all_verts, [], all_faces)
    mesh.update()
    mesh.validate(verbose=False)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def make_mother_ring(name, outer_r, inner_r, thickness, n_segs, collection=None):
    """Flat donut PCB centred on z=0 (z = -t/2 .. +t/2), watertight.

    Vertex layout per segment i (base 4*i): outer_bot, inner_bot, outer_top,
    inner_top. Faces: top + bottom annulus quads, outer + inner side walls.
    """
    z0, z1 = -thickness / 2.0, +thickness / 2.0
    verts = []
    for i in range(n_segs):
        ang = 2.0 * math.pi * i / n_segs
        c, s = math.cos(ang), math.sin(ang)
        verts.append((outer_r * c, outer_r * s, z0))  # outer_bot 4i
        verts.append((inner_r * c, inner_r * s, z0))  # inner_bot 4i+1
        verts.append((outer_r * c, outer_r * s, z1))  # outer_top 4i+2
        verts.append((inner_r * c, inner_r * s, z1))  # inner_top 4i+3

    faces = []
    for i in range(n_segs):
        j = (i + 1) % n_segs
        ob_i, ib_i, ot_i, it_i = 4 * i, 4 * i + 1, 4 * i + 2, 4 * i + 3
        ob_j, ib_j, ot_j, it_j = 4 * j, 4 * j + 1, 4 * j + 2, 4 * j + 3
        faces.append([ot_i, ot_j, it_j, it_i])   # top annulus (+Z)
        faces.append([ob_i, ib_i, ib_j, ob_j])   # bottom annulus (-Z)
        faces.append([ob_i, ob_j, ot_j, ot_i])   # outer wall
        faces.append([ib_i, it_i, it_j, ib_j])   # inner wall

    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.validate(verbose=False)
    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.collection).objects.link(obj)
    return obj


# -----------------------------------------------------------------------------
# Generate outer/inner Goldberg + classify faces
# -----------------------------------------------------------------------------
clear_scene()

print(f"=== Generating Goldberg G({M}, 0) ===")
V_outer_np, F = goldberg(M, R_OUTER)
V_outer = V_outer_np.tolist()
V_inner = (V_outer_np * (R_INNER / R_OUTER)).tolist()
print(f"  {len(V_outer)} vertices, {len(F)} faces")

groups = defaultdict(list)
for fi, f in enumerate(F):
    c = face_centroid(V_outer, f)
    key = classify(c)
    groups[key].append(fi)

print("\n=== Face assignment ===")
print(f"  {'cassette':>14}  {'faces':>5}")
total_assigned = 0
for s in range(N_SLICES):
    for h in (0, 1):
        n_faces = len(groups.get((s, h), []))
        total_assigned += n_faces
        print(f"  slice{s}_{'N' if h == 0 else 'S':>6}  {n_faces:>5}")
n_polar_n = len(groups.get(("polar", 0), []))
n_polar_s = len(groups.get(("polar", 1), []))
print(f"  {'polar_N (skip)':>14}  {n_polar_n:>5}")
print(f"  {'polar_S (skip)':>14}  {n_polar_s:>5}")
print(f"  {'TOTAL':>14}  {total_assigned + n_polar_n + n_polar_s:>5}  "
      f"(expected {len(F)})")

# -----------------------------------------------------------------------------
# Build + export each cassette
# -----------------------------------------------------------------------------
hemi_label = ("N", "S")
cassette_coll = get_or_create_collection("Cassettes")
stats = []
for s in range(N_SLICES):
    for h in (0, 1):
        face_idx = groups[(s, h)]
        label = f"slice{s}_{hemi_label[h]}"
        obj = build_cassette_solid(
            V_outer, V_inner, F, face_idx, f"Cassette_{label}",
            collection=cassette_coll)
        nv = len(obj.data.vertices)
        nf = len(obj.data.polygons)
        stats.append((label, nv, nf, len(face_idx)))

        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        out_path = OUT_DIR / f"cassette_{label}.stl"
        bpy.ops.wm.stl_export(filepath=str(out_path), export_selected_objects=True)
        print(f"  → wrote {out_path.name}")

print("\n=== Summary ===")
print(f"  {'cassette':>14}  {'verts':>5}  {'faces':>5}  {'src_faces':>9}")
for label, nv, nf, src in stats:
    print(f"  {label:>14}  {nv:>5}  {nf:>5}  {src:>9}")

# -----------------------------------------------------------------------------
# Pentagon panels as separate objects (overlapping the cassettes)
#   10 non-polar pents (1 per cassette) + 2 polar pents (pole cutout positions).
#   Each is a watertight plug: outer pent (r=R_OUTER) + inner pent (r=R_INNER)
#   + 5 rim quads — built with the same solid builder, single-face set.
#   Cassettes are left UNCHANGED (the pent material still exists in them too).
# -----------------------------------------------------------------------------
print("\n=== Pentagon panels (separate objects) ===")
pent_coll = get_or_create_collection("Pentagons")
pent_panel_stats = []
for fi, f in enumerate(F):
    if len(f) != 5:
        continue
    key = classify(face_centroid(V_outer, f))
    if key[0] == "polar":
        label = f"pole_{hemi_label[key[1]]}"
    else:
        s, h = key
        label = f"slice{s}_{hemi_label[h]}"
    name = f"Pent_{label}"
    pobj = build_cassette_solid(V_outer, V_inner, F, [fi], name,
                                collection=pent_coll)
    pent_panel_stats.append((name, len(pobj.data.vertices), len(pobj.data.polygons)))

    bpy.ops.object.select_all(action="DESELECT")
    pobj.select_set(True)
    bpy.context.view_layer.objects.active = pobj
    pout = OUT_DIR / f"pent_panel_{label}.stl"
    bpy.ops.wm.stl_export(filepath=str(pout), export_selected_objects=True)

n_pole = sum(1 for n, *_ in pent_panel_stats if "pole_" in n)
print(f"  {len(pent_panel_stats)} pentagon panels "
      f"({len(pent_panel_stats) - n_pole} non-polar + {n_pole} polar) → Pentagons collection")
print(f"  each: {pent_panel_stats[0][1]} verts, {pent_panel_stats[0][2]} faces "
      f"(outer pent + inner pent + 5 rim quads)")

# -----------------------------------------------------------------------------
# Pentagon (Φ2.5) and Hexagon (Φ3) radial axis cylinders
# -----------------------------------------------------------------------------
print("\n=== Face axis cylinders ===")

pent_endpoints = []
hex_endpoints = []
for fi, f in enumerate(F):
    c = face_centroid(V_outer, f)
    if len(f) == 5:
        pent_endpoints.append(((0.0, 0.0, 0.0), c))
    elif len(f) == 6:
        hex_endpoints.append(((0.0, 0.0, 0.0), c))

print(f"  pentagons: {len(pent_endpoints):>4} → Φ{PENT_CYL_DIAMETER} mm")
print(f"  hexagons : {len(hex_endpoints):>4} → Φ{HEX_CYL_DIAMETER} mm")

pent_obj = make_combined_cylinders(
    "PentCylinders", pent_endpoints, PENT_CYL_DIAMETER / 2.0)
hex_obj = make_combined_cylinders(
    "HexCylinders", hex_endpoints, HEX_CYL_DIAMETER / 2.0)

print(f"  PentCylinders mesh: {len(pent_obj.data.vertices)} verts, "
      f"{len(pent_obj.data.polygons)} faces")
print(f"  HexCylinders mesh : {len(hex_obj.data.vertices)} verts, "
      f"{len(hex_obj.data.polygons)} faces")

# Export STLs
for obj, fname in ((pent_obj, "pent_axes.stl"), (hex_obj, "hex_axes.stl")):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    out = OUT_DIR / fname
    bpy.ops.wm.stl_export(filepath=str(out), export_selected_objects=True)
    print(f"  → wrote {fname}")

# -----------------------------------------------------------------------------
# Hexagonal pyramids (六角錐 / tapered aperture wells) — one per hex face
# -----------------------------------------------------------------------------
print("\n=== Hex pyramids (aperture wells) ===")
pyramids = build_all_pyramids(
    V_outer_np, F, PYRAMID_L_H, base_r=PYRAMID_BASE_R, bevel=PYRAMID_BEVEL)
pyr_obj = make_combined_pyramids("HexPyramids", pyramids)
print(f"  l_h={PYRAMID_L_H} base_r={PYRAMID_BASE_R or R_OUTER} bevel={PYRAMID_BEVEL}")
print(f"  {len(pyramids)} pyramids → HexPyramids mesh: "
      f"{len(pyr_obj.data.vertices)} verts, {len(pyr_obj.data.polygons)} faces")

bpy.ops.object.select_all(action="DESELECT")
pyr_obj.select_set(True)
bpy.context.view_layer.objects.active = pyr_obj
pyr_out = OUT_DIR / "hex_pyramids.stl"
bpy.ops.wm.stl_export(filepath=str(pyr_out), export_selected_objects=True)
print(f"  → wrote {pyr_out.name}")

# -----------------------------------------------------------------------------
# Mother ring (equator donut PCB)
# -----------------------------------------------------------------------------
if MOTHER_RING_ENABLE:
    print("\n=== Mother ring (equator donut PCB) ===")
    ring_coll = get_or_create_collection("MotherRing")
    ring_obj = make_mother_ring("MotherRing", MOTHER_RING_OUTER_R,
                                MOTHER_RING_INNER_R, MOTHER_RING_THICKNESS,
                                MOTHER_RING_SEGMENTS, collection=ring_coll)
    print(f"  donut z=0 ±{MOTHER_RING_THICKNESS/2:.1f}mm  "
          f"R {MOTHER_RING_INNER_R}–{MOTHER_RING_OUTER_R}mm  "
          f"t={MOTHER_RING_THICKNESS}mm  segs={MOTHER_RING_SEGMENTS}")
    print(f"  MotherRing mesh: {len(ring_obj.data.vertices)} verts, "
          f"{len(ring_obj.data.polygons)} faces")
    bpy.ops.object.select_all(action="DESELECT")
    ring_obj.select_set(True)
    bpy.context.view_layer.objects.active = ring_obj
    ring_out = OUT_DIR / "mother_ring.stl"
    bpy.ops.wm.stl_export(filepath=str(ring_out), export_selected_objects=True)
    print(f"  → wrote {ring_out.name}")

# -----------------------------------------------------------------------------
# Embed the generating scripts into the .blend (visible in Scripting workspace)
# -----------------------------------------------------------------------------
print("\n=== Embedding scripts (Scripting tab) ===")
SCRIPTS_DIR = REPO / "shell-cad" / "scripts"
auto = sorted(p.name for p in SCRIPTS_DIR.glob(f"{SCRIPT_PREFIX}*.py"))
embed_names = CORE_SCRIPTS + [n for n in auto if n not in CORE_SCRIPTS]
for fname in embed_names:
    if embed_text(fname, SCRIPTS_DIR / fname):
        print(f"  → embedded {fname}")

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "shell_cassettes.blend"))
print(f"\n✓ Done. Outputs in {OUT_DIR}")
print("  Open shell_cassettes.blend → Scripting tab to view/re-run the scripts.")
