"""script_ tool: place one short cylinder at each Goldberg T=81 pentagon.

Run from Blender's Scripting tab (or --python). It ADDS 12 cylinders to the
current scene — it does NOT clear the scene and does NOT group them: each
pentagon gets its own separate object.

Per request:
  - height   = 1 mm   (CYL_HEIGHT)
  - segments = 16      (CYL_SEGMENTS)
  - one cylinder per pentagon position (12 total)
  - individual objects (not combined / not collected)

Geometry per cylinder:
  - axis    = radial direction (origin → pentagon centroid)
  - centred on the pentagon centroid (sphere surface r ≈ 49.9 mm),
    extending ±CYL_HEIGHT/2 along the radial axis
  - object ORIGIN is set to its own pentagon centroid (so each object's pivot
    sits at its placement, matching "individual placement")

Usage:
    # inside Blender → Scripting tab → Run Script, or:
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python shell-cad/scripts/script_pent_cylinders.py
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np

REPO = Path("/Users/katano/work/FPC-isolation-sphere")
sys.path.insert(0, str(REPO / "shell-cad" / "scripts"))
from goldberg import goldberg  # noqa: E402

# --- Parameters ---------------------------------------------------------------
M = 9                 # Goldberg G(9,0) → T = 81
R_OUTER = 50.0        # mm, sphere radius the faces live on
CYL_HEIGHT = 1.0      # mm, cylinder length along the radial axis
CYL_SEGMENTS = 16     # side facets
CYL_DIAMETER = 2.5    # mm, cylinder diameter (M2.5 clamp-screw nominal)
NAME_PREFIX = "PentCyl"
# ------------------------------------------------------------------------------


def _normalize(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def cylinder_local(direction, height, radius, n_segs):
    """(verts, faces) for a capped cylinder CENTRED at the local origin, with
    its axis along *direction*. Used so the object origin lands on the centroid.
    """
    axis_hat = _normalize(np.asarray(direction, dtype=float))
    ref = np.array([0.0, 0.0, 1.0]) if abs(axis_hat[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = _normalize(np.cross(axis_hat, ref))
    v = np.cross(axis_hat, u)

    a = -axis_hat * (height / 2.0)   # base ring centre (local)
    b = +axis_hat * (height / 2.0)   # top ring centre (local)

    verts = []
    for i in range(n_segs):                       # ring 0 (0..n-1)
        ang = 2.0 * math.pi * i / n_segs
        verts.append(tuple(a + radius * (math.cos(ang) * u + math.sin(ang) * v)))
    for i in range(n_segs):                       # ring 1 (n..2n-1)
        ang = 2.0 * math.pi * i / n_segs
        verts.append(tuple(b + radius * (math.cos(ang) * u + math.sin(ang) * v)))
    verts.append(tuple(a))                        # bottom cap centre = 2n
    verts.append(tuple(b))                        # top cap centre    = 2n+1

    n = n_segs
    faces = []
    for i in range(n):                            # side quads
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


def make_pent_cylinders():
    V, F = goldberg(M, R_OUTER)
    pent_faces = [f for f in F if len(f) == 5]
    print(f"Goldberg G({M},0): {len(pent_faces)} pentagons")

    created = []
    for idx, face in enumerate(pent_faces):
        centroid = V[face].mean(axis=0)
        direction = _normalize(centroid)
        verts, faces = cylinder_local(direction, CYL_HEIGHT,
                                      CYL_DIAMETER / 2.0, CYL_SEGMENTS)

        name = f"{NAME_PREFIX}_{idx:02d}"
        mesh = bpy.data.meshes.new(name + "_mesh")
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        mesh.validate(verbose=False)
        obj = bpy.data.objects.new(name, mesh)
        obj.location = tuple(centroid)            # origin at the centroid
        bpy.context.collection.objects.link(obj)  # current collection, not grouped
        created.append(obj)

    print(f"Created {len(created)} individual cylinders "
          f"(h={CYL_HEIGHT}mm, Ø{CYL_DIAMETER}mm, segs={CYL_SEGMENTS})")
    return created


if __name__ == "__main__":
    make_pent_cylinders()
