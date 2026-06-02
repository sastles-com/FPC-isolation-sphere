"""script_ tool: inner_deck の 3 点止め接合 — 受け側(カセット) + provisional inner_deck。

3 点止め (ユーザー確定): **位置決めポスト ×2 + M2.5 セルフタップネジ ×1**。
ポストは hex 穴の間(Goldberg 頂点)に立てる前提で、ポゴ列幅(12.7mm)に合わせ
y=±6.35mm に配置。ネジは 1 列極側 (x=+SCREW_X) に置いて三角形にし安定化。

平面テストペアとして 2 部品を出力(まず機構・寸法・M2.5 食い付き・0603 逃げを検証):
  - 受け側 (cassette-side): 平板 + 位置決めポスト ×2 + M2.5 セルフタップボス ×1
  - provisional inner_deck: 平板 + ポスト穴 ×2 + M2.5 クリアランス穴 + 6 ポゴ穴(2.54)
    + **0603 逃げ recess**(FPC 裏のチップコンデンサ用)

確定後に実カセット赤道中央(r=45 曲面、頂点 v≈lon±8)へ移植する。

Usage:
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python shell-cad/scripts/script_inner_deck_receiver.py
"""
import math
import sys
from pathlib import Path

import bpy

REPO = Path("/Users/katano/work/FPC-isolation-sphere")
OUT_DIR = REPO / "shell-cad" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Parameters (mm) — mother-ring definition (2026-06-02) -------------------
FIX_RADIUS   = 41.25     # Φ82.5: pogo row AND fixing holes share this radius
FIX_ANGLE    = 20.0      # fixing holes ±20° from pogo (zone) centre
FIX_Y        = FIX_RADIUS * math.radians(FIX_ANGLE)   # ≈14.40mm arc offset, flat
FIX_HOLE_D   = 3.0       # inner_deck fixing clearance Ø (Φ3, M2.5 通し)
M25_PILOT_D  = 2.1       # M2.5 self-tap pilot Ø in PETG boss (cassette side)
BOSS_OD      = 4.8       # M2.5 self-tap boss OD
BOSS_H       = 6.0

POGO_N       = 6         # pogo holes (2×GND/2×5V/DIN/DOUT)
POGO_PITCH   = 2.54
POGO_D       = 1.0       # pogo pad hole Ø (test)
POGO_X       = 0.0       # pogo row X (zone centre = same radius as fixings)

DECK_T       = 2.0       # inner_deck plate thickness
CAP0603_RECESS_D = 0.7   # 0603 clearance recess depth (FPC-facing side)

PLATE_X0, PLATE_X1 = -9.0, 9.0     # footprint X (radial extent)
PLATE_Y            = 17.0           # ±Y (tangential, covers ±20° fixings)
SEGS = 32


def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for c in list(bpy.data.collections):
        if len(c.objects) == 0:
            bpy.data.collections.remove(c)


def cyl(d, h, z0, x, y, name):
    bpy.ops.mesh.primitive_cylinder_add(vertices=SEGS, radius=d / 2.0, depth=h,
                                        location=(x, y, z0 + h / 2.0))
    o = bpy.context.active_object; o.name = name
    return o


def tube(od, idia, h, z0, x, y, name):
    ro, ri, z1 = od / 2.0, idia / 2.0, z0 + h
    verts, faces = [], []
    for k in range(SEGS):
        a = 2 * math.pi * k / SEGS
        c, s = math.cos(a), math.sin(a)
        verts += [(x + ro*c, y + ro*s, z0), (x + ri*c, y + ri*s, z0),
                  (x + ro*c, y + ro*s, z1), (x + ri*c, y + ri*s, z1)]
    for k in range(SEGS):
        j = (k + 1) % SEGS
        o0, i0, o1, i1 = 4*k, 4*k+1, 4*k+2, 4*k+3
        o0n, i0n, o1n, i1n = 4*j, 4*j+1, 4*j+2, 4*j+3
        faces += [[o1, o1n, i1n, i1], [o0, i0, i0n, o0n],
                  [o0, o0n, o1n, o1], [i0, i1, i1n, i0n]]
    m = bpy.data.meshes.new(name + "_m"); m.from_pydata(verts, [], faces)
    m.update(); m.validate()
    obj = bpy.data.objects.new(name, m); bpy.context.collection.objects.link(obj)
    return obj


def box(sx, sy, sz, x, y, z, name):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z))
    o = bpy.context.active_object; o.name = name; o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    return o


def boolean_diff(target, cutter):
    m = target.modifiers.new("b", "BOOLEAN"); m.operation = "DIFFERENCE"
    m.solver = "EXACT"; m.object = cutter
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def export(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    out = OUT_DIR / f"{name}.stl"
    bpy.ops.wm.stl_export(filepath=str(out), export_selected_objects=True)
    print(f"  → {out.name}")


def build_receiver():
    """Cassette-side: plate + 2 M2.5 self-tap bosses at the ±20° fixing points."""
    parts = []
    plate = box(PLATE_X1 - PLATE_X0, 2 * PLATE_Y, DECK_T,
                (PLATE_X0 + PLATE_X1) / 2.0, 0, -DECK_T / 2.0, "Recv_plate")
    parts.append(plate)
    parts.append(tube(BOSS_OD, M25_PILOT_D, BOSS_H, 0, POGO_X, +FIX_Y, "Recv_M25boss_L"))
    parts.append(tube(BOSS_OD, M25_PILOT_D, BOSS_H, 0, POGO_X, -FIX_Y, "Recv_M25boss_R"))
    return parts


def build_inner_deck():
    """provisional inner_deck: plate − (2 M2.5 clr at ±20° + 6 pogo + 0603 recess)."""
    zc = 24.0  # viewport offset only; exported独立
    deck = box(PLATE_X1 - PLATE_X0, 2 * PLATE_Y, DECK_T,
               (PLATE_X0 + PLATE_X1) / 2.0, 0, zc, "InnerDeck")
    # 2 fixing clearance holes at ±20° (Φ3, M2.5 通し)
    for yy, nm in ((+FIX_Y, "fixL"), (-FIX_Y, "fixR")):
        boolean_diff(deck, cyl(FIX_HOLE_D, DECK_T * 3, zc - DECK_T, POGO_X, yy, nm))
    # 6 pogo holes (row along Y at zone centre)
    y0 = -(POGO_N - 1) * POGO_PITCH / 2.0
    for k in range(POGO_N):
        boolean_diff(deck, cyl(POGO_D, DECK_T * 3, zc - DECK_T, POGO_X,
                               y0 + k * POGO_PITCH, f"pogo{k}"))
    # 0603 clearance recess on the FPC-facing (top) side, over the LED-overlap zone
    boolean_diff(deck, box(12.0, 16.0, CAP0603_RECESS_D * 2,
                           0.0, 0, zc + DECK_T / 2.0, "recess0603"))
    return [deck]


def main():
    clear()
    coll = bpy.data.collections.new("InnerDeckJoint")
    bpy.context.scene.collection.children.link(coll)
    bpy.context.view_layer.active_layer_collection = \
        bpy.context.view_layer.layer_collection.children[coll.name]

    print("=== inner_deck joint test pair (mother-ring def) ===")
    print(f"  fixings ±{FIX_ANGLE}°@R{FIX_RADIUS} → y=±{FIX_Y:.2f}mm (M2.5 boss pilot Ø{M25_PILOT_D}, deck Ø{FIX_HOLE_D})")
    print(f"  pogo {POGO_N}×Ø{POGO_D}@{POGO_PITCH}  0603 recess {CAP0603_RECESS_D}mm")

    recv = build_receiver()
    deck = build_inner_deck()

    export(recv, "inner_deck_receiver_test")
    export(deck, "inner_deck_provisional_test")
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "inner_deck_joint.blend"))
    print(f"  → inner_deck_joint.blend  ({len(recv)} recv + {len(deck)} deck parts)")


if __name__ == "__main__":
    main()
