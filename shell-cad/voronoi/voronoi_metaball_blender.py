"""
Voronoi Sphere — Blender Metaball版
Fibonacci格子による球面Voronoiのエッジ上にネイティブメタボールを配置

Usage:
  /Applications/Blender.app/Contents/MacOS/Blender -b -P voronoi_metaball_blender.py -- \
    --output voronoi_sphere_metaball.blend

オプション:
  --output   出力.blendファイルパス（必須）
  --stl      STLも同時出力する場合のパス（任意）
  --seeds    Voronoiセル数（デフォルト400）
  --radius   球の外半径mm（デフォルト30.0）
  --resolution  メタボール解像度（デフォルト0.15、小さいほど高精度）
"""
from __future__ import annotations

import sys
import math
import argparse

import bpy
import numpy as np
from scipy.spatial import SphericalVoronoi, geometric_slerp
from mathutils import Vector

# ── デフォルトパラメータ ─────────────────────────────────
R_OUTER       = 30.0    # 球の外半径 (mm)
THICKNESS     = 1.5     # 殻の肉厚 (mm)
N_SEEDS       = 400     # Voronoiセル数

# メタボール設定
MB_RESOLUTION       = 0.15   # レンダリング解像度（小さいほど細かい）
MB_RENDER_RES       = 0.15
MB_THRESHOLD        = 0.6

# 頂点メタボール
VERTEX_RADIUS       = 1.8    # mm
VERTEX_STIFFNESS    = 2.0

# エッジメタボール
N_INTERIOR          = 8      # エッジ内部の分割数
MAX_SAG_PCT         = 3.0    # 内側へのたわみ（球心方向へ引く）
CENTER_RADIUS       = 1.4    # エッジ中央付近の半径
MIN_RADIUS          = 1.6    # エッジ端付近の半径
CENTER_STIFFNESS    = 1.2
EDGE_STIFFNESS      = 2.0

MB_NAME = "VoronoiSphere"


# ── ユーティリティ ────────────────────────────────────────
def smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def parse_args(argv):
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    p = argparse.ArgumentParser()
    p.add_argument("--output",     required=True)
    p.add_argument("--stl",        default=None)
    p.add_argument("--seeds",      type=int,   default=N_SEEDS)
    p.add_argument("--radius",     type=float, default=R_OUTER)
    p.add_argument("--resolution", type=float, default=MB_RESOLUTION)
    return p.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for store in (bpy.data.meshes, bpy.data.metaballs,
                  bpy.data.materials, bpy.data.cameras,
                  bpy.data.lights, bpy.data.curves):
        for block in list(store):
            if block.users == 0:
                store.remove(block)


# ── Fibonacci格子による球面Voronoi ────────────────────────
def make_spherical_voronoi(n_seeds: int):
    golden_ratio = (1.0 + math.sqrt(5.0)) / 2.0
    idx   = np.arange(n_seeds)
    theta = 2.0 * math.pi * idx / golden_ratio
    phi   = np.arccos(1.0 - 2.0 * (idx + 0.5) / n_seeds)
    pts   = np.column_stack([
        np.sin(phi) * np.cos(theta),
        np.sin(phi) * np.sin(theta),
        np.cos(phi),
    ])
    sv = SphericalVoronoi(pts, radius=1.0, center=np.zeros(3))
    sv.sort_vertices_of_regions()
    return sv


def collect_edges(sv) -> list[tuple[int, int]]:
    seen = set()
    for region in sv.regions:
        n = len(region)
        for i in range(n):
            a, b = region[i], region[(i + 1) % n]
            key = (min(a, b), max(a, b))
            seen.add(key)
    # 極端に短いエッジを除去（数値誤差）
    edges = [(a, b) for a, b in seen
             if np.linalg.norm(sv.vertices[a] - sv.vertices[b]) > 1e-3]
    return edges


# ── メタボール要素の追加（generate_metaball_10.pyのadd_edge_ballsを踏襲）────
def add_edge_balls(mb, p1: Vector, p2: Vector, r_sphere: float):
    """
    2頂点間（球面上、スケール済み）にメタボールを配置。
    p1, p2: 球面上の3D座標 (mm)
    r_sphere: 球半径 (mm) — たわみ計算の参照用
    """
    # 端点（頂点）ボール — 重複するが threshold が吸収する
    for pos in (p1, p2):
        e = mb.elements.new()
        e.type = 'BALL'
        e.co = pos
        e.radius = MIN_RADIUS
        e.stiffness = EDGE_STIFFNESS

    # 内部補間点
    for i in range(1, N_INTERIOR + 1):
        t = i / (N_INTERIOR + 1)

        # 球面上の大円弧補間（slerp）
        u1 = p1.normalized()
        u2 = p2.normalized()
        # mathutils にはslerpがないのでnumpyで計算
        dot = max(-1.0, min(1.0, u1.dot(u2)))
        omega = math.acos(dot)
        if omega < 1e-6:
            slerp_pos = p1.lerp(p2, t)
        else:
            s = math.sin(omega)
            slerp_pos = (math.sin((1 - t) * omega) / s) * p1 + \
                        (math.sin(t * omega) / s) * p2
        slerp_pos = slerp_pos.normalized() * r_sphere

        # 球心方向へのたわみ（スカルのリブが内側に丸まる効果）
        curve_t = 1.0 - abs(2.0 * t - 1.0)   # 0→1→0
        sag_factor = (MAX_SAG_PCT / 100.0) * smoothstep(curve_t)
        to_center = -slerp_pos  # 球心 = 原点
        dist_c = to_center.length
        if dist_c > 1e-4:
            sagged_pos = slerp_pos + to_center.normalized() * (dist_c * sag_factor)
        else:
            sagged_pos = slerp_pos

        # 中央ほど半径・stiffnessを変える
        smooth_r = smoothstep(curve_t)
        radius    = MIN_RADIUS    + (CENTER_RADIUS    - MIN_RADIUS)    * smooth_r
        stiffness = EDGE_STIFFNESS + (CENTER_STIFFNESS - EDGE_STIFFNESS) * smooth_r

        e = mb.elements.new()
        e.type = 'BALL'
        e.co = sagged_pos
        e.radius = radius
        e.stiffness = stiffness


def create_voronoi_metaball(sv, r_outer: float, resolution: float):
    """Voronoiエッジ全本にメタボールを配置してオブジェクト生成"""
    edges = collect_edges(sv)
    print(f"Voronoi頂点数: {len(sv.vertices)}")
    print(f"有効エッジ数:   {len(edges)}")

    mb = bpy.data.metaballs.new(MB_NAME)
    mb.resolution        = resolution
    mb.render_resolution = resolution
    mb.threshold         = MB_THRESHOLD

    obj = bpy.data.objects.new(MB_NAME, mb)
    bpy.context.collection.objects.link(obj)

    # 頂点ボール（Voronoi頂点 = リブの交差点）
    for v_unit in sv.vertices:
        pos = Vector(v_unit.tolist()) * r_outer
        e = mb.elements.new()
        e.type = 'BALL'
        e.co = pos
        e.radius = VERTEX_RADIUS
        e.stiffness = VERTEX_STIFFNESS

    # エッジボール
    for idx, (a, b) in enumerate(edges):
        p1 = Vector(sv.vertices[a].tolist()) * r_outer
        p2 = Vector(sv.vertices[b].tolist()) * r_outer
        add_edge_balls(mb, p1, p2, r_outer)
        if idx % 200 == 0:
            print(f"  エッジ {idx}/{len(edges)} 処理中...")

    total_elements = len(mb.elements)
    print(f"メタボール要素数: {total_elements}")
    print(f"  （頂点: {len(sv.vertices)}, エッジ×(N_INTERIOR+2): {len(edges)}×{N_INTERIOR+2}）")
    return obj


def main():
    args = parse_args(sys.argv)

    global N_SEEDS, R_OUTER, MB_RESOLUTION, MB_RENDER_RES
    N_SEEDS        = args.seeds
    R_OUTER        = args.radius
    MB_RESOLUTION  = args.resolution
    MB_RENDER_RES  = args.resolution

    clear_scene()

    print(f"=== Voronoi Sphere Metaball ===")
    print(f"  seeds={N_SEEDS}, R={R_OUTER}mm, resolution={MB_RESOLUTION}")

    sv = make_spherical_voronoi(N_SEEDS)
    obj = create_voronoi_metaball(sv, R_OUTER, MB_RESOLUTION)

    # STL出力（オプション）
    if args.stl:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.export_mesh.stl(
            filepath=args.stl,
            use_selection=True,
            global_scale=1.0,
        )
        print(f"✅ STL: {args.stl}")

    bpy.ops.wm.save_as_mainfile(filepath=args.output)
    print(f"✅ Blend: {args.output}")


if __name__ == "__main__":
    main()
