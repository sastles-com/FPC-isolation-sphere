"""Build the FULL Goldberg T=81 shell as ONE object (no cassette split).

カセット分割しない丸ごとの Goldberg 多面体を 1 メッシュで生成する。
  - HOLLOW=True (既定): 外殻(r=R_OUTER)+ 内殻(r=R_INNER, 逆 winding)= 中空シェル。
    全エッジが 2 面共有なので rim は不要 → 2 つの閉曲面 = 中空ボール(watertight)
  - HOLLOW=False: 外側 Goldberg 面のみの閉じたソリッド(中実の多面体)

`blender_make_cassettes.py` と同じ面集合・同じ向きだが、分類・分割をしない版。

Outputs (shell-cad/output/):
  goldberg_shell.stl   全シェル(分割なし)
  goldberg_shell.blend Blender シーン

Usage:
    /Applications/Blender.app/Contents/MacOS/Blender --background \
        --python shell-cad/scripts/blender_goldberg_shell.py
    # 外径/内径を指定(-- 以降):
    /Applications/Blender.app/Contents/MacOS/Blender -b \
        --python shell-cad/scripts/blender_goldberg_shell.py -- \
        --outer 60 --inner 54 -m 9
    # 中実ソリッド:
    ...  -- --outer 50 --solid
"""
import sys
from pathlib import Path

import bpy

REPO = Path("/Users/katano/work/FPC-isolation-sphere")
sys.path.insert(0, str(REPO / "shell-cad" / "scripts"))
from goldberg import goldberg  # noqa: E402

OUT_DIR = REPO / "shell-cad" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Defaults (overridable via `-- --outer ... --inner ...`) -----------------
M       = 9        # Goldberg G(M,0) → T = M²
R_OUTER = 44.0     # mm, φ100 outer
R_INNER = 10.0     # mm, φ90 inner (radial wall 5mm)
HOLLOW  = True     # True = 中空シェル(外+内) / False = 中実ソリッド(外のみ)
NAME    = "GoldbergShell"


def parse_argv():
    """`--` 以降の引数で外径/内径/m/solid を上書き(無ければデフォルト)。"""
    import argparse
    if "--" not in sys.argv:
        return M, R_OUTER, R_INNER, HOLLOW
    extra = sys.argv[sys.argv.index("--") + 1:]
    p = argparse.ArgumentParser(prog="blender_goldberg_shell.py")
    p.add_argument("--outer", type=float, default=R_OUTER, help="外径 mm")
    p.add_argument("--inner", type=float, default=R_INNER, help="内径 mm")
    p.add_argument("-m", type=int, default=M, help="Goldberg m (T=m²)")
    p.add_argument("--solid", action="store_true", help="中実ソリッド(外のみ)")
    a = p.parse_args(extra)
    return a.m, a.outer, a.inner, (not a.solid)
# ------------------------------------------------------------------------------


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for col in (bpy.data.meshes, bpy.data.materials):
        for it in list(col):
            if it.users == 0:
                col.remove(it)


def build_shell(V_outer, V_inner, F, hollow):
    n = len(V_outer)
    verts = [tuple(v) for v in V_outer]
    faces = [list(f) for f in F]                       # outer (CCW, 外向き法線)
    if hollow:
        verts += [tuple(v) for v in V_inner]
        faces += [[vi + n for vi in reversed(f)] for f in F]   # inner (逆 winding)
    mesh = bpy.data.meshes.new(NAME + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.validate(verbose=False)
    obj = bpy.data.objects.new(NAME, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def main():
    m, r_outer, r_inner, hollow = parse_argv()
    clear_scene()
    print(f"=== Goldberg G({m},0) full shell  outer={r_outer} inner={r_inner} "
          f"HOLLOW={hollow} ===")
    V_outer_np, F = goldberg(m, r_outer)
    V_outer = V_outer_np.tolist()
    V_inner = (V_outer_np * (r_inner / r_outer)).tolist()
    n_pent = sum(1 for f in F if len(f) == 5)
    n_hex = sum(1 for f in F if len(f) == 6)
    print(f"  {len(V_outer)} verts, {len(F)} faces ({n_pent} pent, {n_hex} hex)")

    obj = build_shell(V_outer, V_inner, F, hollow)
    print(f"  → {NAME}: {len(obj.data.vertices)} verts, {len(obj.data.polygons)} faces "
          f"({'hollow shell' if hollow else 'solid'})")

    tag = f"o{r_outer:g}" + (f"_i{r_inner:g}" if hollow else "_solid")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    stl = OUT_DIR / f"goldberg_shell_{tag}.stl"
    bpy.ops.wm.stl_export(filepath=str(stl), export_selected_objects=True)
    print(f"  → wrote {stl.name}")

    blend = OUT_DIR / f"goldberg_shell_{tag}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print(f"  → wrote {blend.name}\n✓ Done.")


if __name__ == "__main__":
    main()
