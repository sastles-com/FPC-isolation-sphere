"""script_ tool: copy the active object (placed at the north pole) onto every
Goldberg T=81 pentagon by rotating it about the world origin.

The active object is treated as a template sitting near the north pole (+Z).
For each of the 12 pentagon centroids, a duplicate is rotated about the origin
by the shortest-arc rotation that maps +Z onto that pentagon's radial direction
— so both the position and orientation follow the pentagon.

  - 10 non-polar pentagons + 2 polar pentagons = 12 placements
  - duplicates are LINKED by default (share the template's mesh; edit once,
    all update). Set LINKED = False for independent copies.
  - duplicates go into a collection "<template>_pents" (cleared on re-run so
    repeated runs don't pile up).

Note: the rotation only aligns the radial axis (+Z → pentagon normal). The roll
about that axis is the shortest-arc default; it does NOT align to pentagon edge
orientation. Ask if you need edge-aligned roll.

Usage:
    # in Blender: select/activate the template object → Scripting tab → Run
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python shell-cad/scripts/script_place_on_pentagons.py
"""
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

REPO = Path("/Users/katano/work/FPC-isolation-sphere")
sys.path.insert(0, str(REPO / "shell-cad" / "scripts"))
from goldberg import goldberg  # noqa: E402

# --- Parameters ---------------------------------------------------------------
M = 9                 # Goldberg G(9,0) → T = 81
R_OUTER = 50.0        # mm, sphere radius the faces live on
NORTH_AXIS = (0.0, 0.0, 1.0)   # template's "up" / pole direction
LINKED = True         # True = linked duplicates (shared mesh); False = full copies
INCLUDE_POLAR = True  # include the 2 polar pentagons (all 12). False = 10 only
COLLECTION_SUFFIX = "_pents"
# ------------------------------------------------------------------------------


def classify_pole(cz):
    return "N" if cz >= 0.0 else "S"


def pentagon_targets():
    """Return list of (label, unit_direction) for every pentagon centroid."""
    V, F = goldberg(M, R_OUTER)
    polar_thresh = 1.0  # mm, axial radius below which a pent is polar
    targets = []
    slice_count = {}
    for f in F:
        if len(f) != 5:
            continue
        c = V[f].mean(axis=0)
        axial_r = float(np.hypot(c[0], c[1]))
        hemi = classify_pole(c[2])
        if axial_r < polar_thresh:
            label = f"pole_{hemi}"
            polar = True
        else:
            # rough longitudinal index just for a stable unique name
            az = (np.degrees(np.arctan2(c[1], c[0])) + 54.0) % 360.0
            s = int(az // 72.0) % 5
            key = (s, hemi)
            slice_count[key] = slice_count.get(key, 0)
            label = f"slice{s}_{hemi}"
            polar = False
        targets.append((label, Vector(c).normalized(), polar))
    return targets


def place_on_pentagons():
    ref = bpy.context.active_object
    if ref is None:
        print("Error: no active object. Select/activate the template first.")
        return []

    targets = pentagon_targets()
    if not INCLUDE_POLAR:
        targets = [t for t in targets if not t[2]]

    # Fresh collection for the instances (clear if it already exists)
    coll_name = f"{ref.name}{COLLECTION_SUFFIX}"
    coll = bpy.data.collections.get(coll_name)
    if coll is None:
        coll = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(coll)
    else:
        for o in list(coll.objects):
            bpy.data.objects.remove(o, do_unlink=True)

    z = Vector(NORTH_AXIS).normalized()
    created = []
    for label, target, _polar in targets:
        dup = ref.copy()
        if not LINKED:
            dup.data = ref.data.copy()
        dup.name = f"{ref.name}_{label}"
        rot = z.rotation_difference(target).to_matrix().to_4x4()  # shortest arc
        dup.matrix_world = rot @ ref.matrix_world                  # rotate about origin
        coll.objects.link(dup)
        created.append(dup)

    print(f"Template: '{ref.name}'  ({'linked' if LINKED else 'full'} copies)")
    print(f"Placed {len(created)} copies into collection '{coll_name}'")
    return created


if __name__ == "__main__":
    place_on_pentagons()
