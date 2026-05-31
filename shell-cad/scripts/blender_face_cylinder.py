"""Build a single radial cylinder pointing from the world origin toward one
Goldberg T=81 face (a chosen pentagon or hexagon).

Pick one face by (kind, index):
  kind  = "pent" | "hex"
  index = position within that kind's list (pent: 0..11, hex: 0..799)

The cylinder axis is the radial direction origin → face centroid. You control:
  distance : where the cylinder base starts, measured from the origin along
             the radial axis (mm). 0 = starts at the very center.
  height   : cylinder length along the axis (mm).
  diameter : cylinder diameter (mm).
  segments : number of side facets (mesh resolution).

The resulting object's ORIGIN stays at the world origin (0, 0, 0): the geometry
is authored in world coordinates and the object location is left at (0, 0, 0),
so the pivot sits at the sphere center, not at the cylinder body.

Usage:
    # edit the PARAMETERS block below, then:
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python shell-cad/scripts/blender_face_cylinder.py

    # or override on the command line (args after `--`):
    /Applications/Blender.app/Contents/MacOS/Blender -b \
        --python shell-cad/scripts/blender_face_cylinder.py -- \
        --kind hex --index 100 --distance 0 --height 50 --diameter 4 --segments 32

    # from Blender's Scripting tab, after running once you can also call:
    #   build_face_cylinder(V, F, "pent", 3, distance=40, height=12, diameter=2.5)
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np

REPO = Path("/Users/katano/work/FPC-isolation-sphere")
sys.path.insert(0, str(REPO / "shell-cad" / "scripts"))
from goldberg import goldberg  # noqa: E402

OUT_DIR = REPO / "shell-cad" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# PARAMETERS — edit here (or override via `-- --kind ... --index ...`)
# ==============================================================================
M = 9                # Goldberg G(9,0) → T = 81
R_OUTER = 50.0       # mm, sphere radius the faces live on (φ100 outer)

FACE_KIND = "hex"    # "pent" or "hex"
FACE_INDEX = 0       # index within that kind's list (pent 0..11, hex 0..799)

CYL_DISTANCE = 0.0   # mm, base start distance from origin along the radial axis
CYL_HEIGHT = 50.0    # mm, cylinder length along the axis
CYL_DIAMETER = 4.0   # mm, cylinder diameter
CYL_SEGMENTS = 16    # side facets

SAVE_BLEND = True    # write OUT_DIR/face_cylinder.blend
SAVE_STL = True      # write OUT_DIR/face_cylinder_<kind><index>.stl
# ==============================================================================


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for col in (bpy.data.meshes, bpy.data.materials):
        for it in list(col):
            if it.users == 0:
                col.remove(it)


def embed_text(name, path):
    """Embed a source file as a Text datablock so it shows up in Blender's
    Scripting workspace (Text → Run Script to re-run it)."""
    path = Path(path)
    if not path.exists():
        print(f"  ⚠ skip (not found): {name}")
        return None
    if name in bpy.data.texts:
        bpy.data.texts.remove(bpy.data.texts[name])
    txt = bpy.data.texts.new(name)
    txt.from_string(path.read_text())
    return txt


def _normalize(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def face_centroid(V, face):
    return V[face].mean(axis=0)


def faces_of_kind(F, kind):
    """Return the list of face-vertex-index lists for the requested kind."""
    n = 5 if kind == "pent" else 6
    return [f for f in F if len(f) == n]


def cylinder_mesh_data(p0, p1, radius, n_segs):
    """(verts, faces) for a closed, capped cylinder from p0 to p1 (world coords)."""
    a = np.asarray(p0, dtype=float)
    b = np.asarray(p1, dtype=float)
    axis = b - a
    length = float(np.linalg.norm(axis))
    if length < 1e-9:
        raise ValueError("Cylinder height is zero (check distance/height).")
    axis_hat = axis / length

    ref = np.array([0.0, 0.0, 1.0]) if abs(axis_hat[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = _normalize(np.cross(axis_hat, ref))
    v = np.cross(axis_hat, u)

    verts = []
    for i in range(n_segs):                       # ring 0 at p0 (0..n-1)
        ang = 2.0 * math.pi * i / n_segs
        verts.append(tuple(a + radius * (math.cos(ang) * u + math.sin(ang) * v)))
    for i in range(n_segs):                       # ring 1 at p1 (n..2n-1)
        ang = 2.0 * math.pi * i / n_segs
        verts.append(tuple(b + radius * (math.cos(ang) * u + math.sin(ang) * v)))
    verts.append(tuple(a))                        # bottom cap center = 2n
    verts.append(tuple(b))                        # top cap center    = 2n+1

    n = n_segs
    faces = []
    for i in range(n):                            # side quads (outward normal)
        i1 = (i + 1) % n
        faces.append([i, i1, n + i1, n + i])
    bc = 2 * n
    for i in range(n):                            # bottom cap
        i1 = (i + 1) % n
        faces.append([bc, i1, i])
    tc = 2 * n + 1
    for i in range(n):                            # top cap
        i1 = (i + 1) % n
        faces.append([tc, n + i, n + i1])
    return verts, faces


def build_face_cylinder(V, F, kind, index,
                        distance=CYL_DISTANCE, height=CYL_HEIGHT,
                        diameter=CYL_DIAMETER, segments=CYL_SEGMENTS,
                        name=None):
    """Create one radial cylinder object aimed at face (kind, index).

    The object's origin is left at the world origin (0, 0, 0).
    Returns the created bpy object.
    """
    kind = kind.lower()
    if kind not in ("pent", "hex"):
        raise ValueError(f"kind must be 'pent' or 'hex', got {kind!r}")
    faces = faces_of_kind(F, kind)
    if not (0 <= index < len(faces)):
        raise IndexError(f"{kind} index {index} out of range 0..{len(faces) - 1}")

    centroid = face_centroid(V, faces[index])
    direction = _normalize(centroid)
    p0 = direction * distance
    p1 = direction * (distance + height)

    verts, mesh_faces = cylinder_mesh_data(p0, p1, diameter / 2.0, segments)

    name = name or f"Cyl_{kind}_{index:04d}"
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], mesh_faces)
    mesh.update()
    mesh.validate(verbose=False)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = (0.0, 0.0, 0.0)   # keep object origin at the world origin

    print(f"  {name}: centroid r={np.linalg.norm(centroid):.3f} mm  "
          f"dir=({direction[0]:.3f}, {direction[1]:.3f}, {direction[2]:.3f})")
    print(f"    base@{distance:.2f}mm  top@{distance + height:.2f}mm  "
          f"Ø{diameter}  segs={segments}  origin=(0,0,0)")
    return obj


def parse_argv():
    """Read overrides from argv after the `--` separator (if present)."""
    import argparse
    argv = sys.argv
    if "--" not in argv:
        return None
    extra = argv[argv.index("--") + 1:]
    p = argparse.ArgumentParser(prog="blender_face_cylinder.py")
    p.add_argument("--kind", choices=("pent", "hex"), default=FACE_KIND)
    p.add_argument("--index", type=int, default=FACE_INDEX)
    p.add_argument("--distance", type=float, default=CYL_DISTANCE)
    p.add_argument("--height", type=float, default=CYL_HEIGHT)
    p.add_argument("--diameter", type=float, default=CYL_DIAMETER)
    p.add_argument("--segments", type=int, default=CYL_SEGMENTS)
    return p.parse_args(extra)


# -----------------------------------------------------------------------------
clear_scene()

print(f"=== Generating Goldberg G({M}, 0), r={R_OUTER} ===")
V_np, F = goldberg(M, R_OUTER)
n_pent = sum(1 for f in F if len(f) == 5)
n_hex = sum(1 for f in F if len(f) == 6)
print(f"  {len(V_np)} verts, {len(F)} faces ({n_pent} pent, {n_hex} hex)")

args = parse_argv()
kind = args.kind if args else FACE_KIND
index = args.index if args else FACE_INDEX
distance = args.distance if args else CYL_DISTANCE
height = args.height if args else CYL_HEIGHT
diameter = args.diameter if args else CYL_DIAMETER
segments = args.segments if args else CYL_SEGMENTS

print(f"\n=== Building cylinder for {kind}[{index}] ===")
obj = build_face_cylinder(V_np, F, kind, index,
                          distance=distance, height=height,
                          diameter=diameter, segments=segments)

if SAVE_STL:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    stl_path = OUT_DIR / f"face_cylinder_{kind}{index:04d}.stl"
    bpy.ops.wm.stl_export(filepath=str(stl_path), export_selected_objects=True)
    print(f"  → wrote {stl_path.name}")

if SAVE_BLEND:
    SCRIPTS_DIR = REPO / "shell-cad" / "scripts"
    # CORE (always) + any script_*.py auto-detected in shell-cad/scripts/
    core = ["blender_face_cylinder.py", "goldberg.py"]
    auto = sorted(p.name for p in SCRIPTS_DIR.glob("script_*.py"))
    for fname in core + [n for n in auto if n not in core]:
        if embed_text(fname, SCRIPTS_DIR / fname):
            print(f"  embedded {fname}")
    blend_path = OUT_DIR / "face_cylinder.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"  → wrote {blend_path.name}")

print("\n✓ Done.")
