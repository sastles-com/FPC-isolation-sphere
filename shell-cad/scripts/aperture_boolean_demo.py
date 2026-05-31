"""Boolean-diff hex pyramid + cylinder apertures from a sphere shell.

Geometry:
  - Shell   : sphere(R_OUTER) − sphere(R_INNER)  = wall thickness
  - Pyramid : base at R_OUTER, apex L_H mm inward  (tapered aperture well)
  - Cylinder: bore radius CYL_R through full shell  (LED seat / wire path)
  - Result  : shell − union(all pyramids + cylinders)

Backend: manifold3d (same engine as Blender "Exact" Boolean).

Usage:
    uv run python shell-cad/scripts/aperture_boolean_demo.py
    uv run python shell-cad/scripts/aperture_boolean_demo.py --cassette 0
"""
from __future__ import annotations

# ==============================================================================
# TUNABLE PARAMETERS — edit here to change aperture geometry
# ==============================================================================

# --- Shell (球殻) ---
R_OUTER     = 52.0   # 外殻半径 mm          (ピラミッド底面がここに乗る)
R_INNER     = 47.0   # 内殻半径 mm          (R_OUTER − R_INNER = 壁厚 5 mm)

# --- Pyramid / tapered aperture well (テーパー穴) ---
L_H         =  8.0   # 錐の深さ mm          (壁厚より大きくすること: > R_OUTER − R_INNER)
BEVEL       =  0.0   # 錐の辺面取り mm      (0=シャープ, ~0.5=面取り; T=81で上限~1.5)

# --- Cylinder / LED bore (LED 取り付け穴) ---
CYL_R       =  1.2   # ボア半径 mm          (WS2812-2020 本体 2×2mm → 最小 ~1.0)
CYL_ENABLE  = True   # False にすると円筒を無効化 (錐のみ)

# --- Mesh quality (メッシュ解像度) ---
SPHERE_SUBS =  5     # 球の細分割数         (4=高速, 5=良好, 6=高精細)
CYL_SECTS   = 16     # 円筒の多角形分割数   (8=高速, 16=良好, 32=高精細)

# ==============================================================================

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import Manifold, Mesh

sys.path.insert(0, str(Path(__file__).parent))
from goldberg import goldberg
from hex_pyramids import _pyramid_plain, _pyramid_beveled

# ---- helpers -----------------------------------------------------------------

def _normalize(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


def _align_z_to(target: np.ndarray) -> np.ndarray:
    """4×4 rotation matrix aligning +Z to *target* direction."""
    z = np.array([0., 0., 1.])
    t = _normalize(np.array(target, dtype=float))
    axis = np.cross(z, t)
    sin_a = np.linalg.norm(axis)
    cos_a = float(np.dot(z, t))
    if sin_a < 1e-8:
        return np.eye(4) if cos_a > 0 else \
               trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
    return trimesh.transformations.rotation_matrix(
        np.arctan2(sin_a, cos_a), axis / sin_a
    )


def tm_to_manifold(mesh: trimesh.Trimesh) -> Manifold:
    return Manifold(Mesh(
        vert_properties=np.array(mesh.vertices, dtype=np.float32),
        tri_verts=np.array(mesh.faces, dtype=np.int32),
    ))


def manifold_to_tm(m: Manifold) -> trimesh.Trimesh:
    out = m.to_mesh()
    return trimesh.Trimesh(vertices=out.vert_properties, faces=out.tri_verts,
                           process=False)


# ---- cutter builders ---------------------------------------------------------

def pyramid_manifold(verts6: np.ndarray, apex: np.ndarray) -> Manifold:
    if BEVEL > 0.0:
        verts, tris = _pyramid_beveled(verts6, apex, BEVEL)
    else:
        verts, tris = _pyramid_plain(verts6, apex)
    return Manifold(Mesh(
        vert_properties=verts.astype(np.float32),
        tri_verts=np.array(tris, dtype=np.int32),
    ))


def cylinder_manifold(centroid: np.ndarray) -> Manifold:
    cyl = trimesh.creation.cylinder(radius=CYL_R, height=R_OUTER * 2,
                                    sections=CYL_SECTS)
    T = _align_z_to(centroid)
    T[:3, 3] = centroid
    cyl.apply_transform(T)
    return tm_to_manifold(cyl)


# ---- cassette filter ---------------------------------------------------------

def cassette_filter(centroid: np.ndarray, cassette: int | None) -> bool:
    if cassette is None:
        return True
    az = np.degrees(np.arctan2(centroid[1], centroid[0])) % 360
    shifted   = (az + 54.0) % 360
    slice_idx = int(shifted // 72) % 5
    hemi      = 0 if centroid[2] >= 0 else 1
    return slice_idx == (cassette % 5) and hemi == (cassette // 5)


# ---- main --------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cassette", type=int, default=None,
                        help="カセット番号 0–9 に限定 (0–4=N, 5–9=S). デフォルト: 全球")
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    t0 = time.time()
    def elapsed(): return f"({time.time() - t0:.1f}s)"

    wall = R_OUTER - R_INNER
    print(f"Parameters: R_OUTER={R_OUTER} R_INNER={R_INNER} wall={wall:.1f}mm "
          f"L_H={L_H} BEVEL={BEVEL} CYL_R={CYL_R} CYL_ENABLE={CYL_ENABLE}")

    V, F_list = goldberg(9, R_OUTER)
    hex_faces = [(fi, f) for fi, f in enumerate(F_list) if len(f) == 6]
    print(f"Goldberg T=81: {len(hex_faces)} hex faces  {elapsed()}")

    # ---- Build cutters ----
    cutters: list[Manifold] = []
    for fi, face in hex_faces:
        verts6   = V[face]
        centroid = verts6.mean(axis=0)
        if not cassette_filter(centroid, args.cassette):
            continue
        apex = centroid - _normalize(centroid) * L_H
        try:
            cutters.append(pyramid_manifold(verts6, apex))
            if CYL_ENABLE:
                cutters.append(cylinder_manifold(centroid))
        except Exception as e:
            print(f"  ⚠ face {fi}: {e}")

    n_ap = len(cutters) // (2 if CYL_ENABLE else 1)
    print(f"Built {n_ap} aperture cutters  {elapsed()}")

    # ---- Union all cutters ----
    print("Composing cutter union...")
    try:
        cutter_union = Manifold.compose(cutters)
    except Exception:
        from functools import reduce
        print("  compose failed, falling back to reduce union...")
        cutter_union = reduce(lambda a, b: a + b, cutters)
    print(f"Cutter manifold: genus={cutter_union.genus()}  {elapsed()}")

    # ---- Shell ----
    print("Building sphere shell...")
    outer_tm = trimesh.creation.icosphere(subdivisions=SPHERE_SUBS, radius=R_OUTER)
    inner_tm = trimesh.creation.icosphere(subdivisions=SPHERE_SUBS, radius=R_INNER)
    shell_m  = tm_to_manifold(outer_tm) - tm_to_manifold(inner_tm)
    print(f"Shell  {elapsed()}")

    # ---- Boolean diff ----
    print("Shell − cutters ...")
    result_m = shell_m - cutter_union
    print(f"Done  {elapsed()}")

    result = manifold_to_tm(result_m)
    print(f"Result: {len(result.vertices)} verts, {len(result.faces)} tris  {elapsed()}")

    # ---- Export + view + upload ----
    label   = f"cassette{args.cassette}" if args.cassette is not None else "fullsphere"
    out_stl = Path(args.output or f"shell-cad/output/aperture_demo_{label}.stl")
    out_stl.parent.mkdir(parents=True, exist_ok=True)
    result.export(str(out_stl))
    print(f"→ STL: {out_stl}")

    import subprocess
    title = (f"Aperture — cassette {args.cassette}"
             if args.cassette is not None
             else f"Aperture — full sphere  R={R_OUTER}/{R_INNER} L_H={L_H} "
                  f"bevel={BEVEL} cyl={CYL_R if CYL_ENABLE else 'off'}")
    subprocess.run(["uv", "run", "python",
                    "shell-cad/scripts/generate_stl_viewer.py",
                    str(out_stl), "--title", title], check=True)
    subprocess.run(["bash", "shell-cad/scripts/upload_to_lolipop.sh"], check=True)
    print(f"\n✅  Total: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
