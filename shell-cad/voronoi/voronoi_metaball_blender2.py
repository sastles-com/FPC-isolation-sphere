"""
Voronoi Sphere — Blender Metaball版 (scipy不要)
JSONからVoronoiデータを読み込んでネイティブメタボールを配置

Usage:
  # Step 1: Voronoiデータ生成（scipy環境で）
  python3 gen_voronoi_json.py voronoi_data.json

  # Step 2: Blenderでメタボール生成
  /Applications/Blender.app/Contents/MacOS/Blender -b -P voronoi_metaball_blender.py -- \
    --input voronoi_data.json \
    --output voronoi_sphere_metaball.blend
"""
from __future__ import annotations

import sys
import math
import json
import argparse

import bpy
from mathutils import Vector

# ── メタボールパラメータ ──────────────────────────────────
MB_RESOLUTION    = 0.15   # 小さいほど高精細（重い）
MB_THRESHOLD     = 0.6

VERTEX_RADIUS    = 1.8    # Voronoi頂点の玉サイズ
VERTEX_STIFFNESS = 2.0

N_INTERIOR       = 8      # エッジ内部の補間点数
MAX_SAG_PCT      = 3.0    # 球心方向へのたわみ %
CENTER_RADIUS    = 1.4    # エッジ中央の玉サイズ
MIN_RADIUS       = 1.6    # エッジ端の玉サイズ
CENTER_STIFFNESS = 1.2
EDGE_STIFFNESS   = 2.0

MB_NAME = "VoronoiSphere"


def smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def slerp(v1: Vector, v2: Vector, t: float) -> Vector:
    """球面線形補間（mathutils版）"""
    dot = max(-1.0, min(1.0, v1.normalized().dot(v2.normalized())))
    omega = math.acos(dot)
    if omega < 1e-6:
        return v1.lerp(v2, t)
    s = math.sin(omega)
    return (math.sin((1.0 - t) * omega) / s) * v1 + \
           (math.sin(t * omega) / s) * v2


def parse_args(argv):
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    p = argparse.ArgumentParser()
    p.add_argument("--input",      required=True,  help="voronoi_data.json のパス")
    p.add_argument("--output",     required=True,  help="出力 .blend ファイルパス")
    p.add_argument("--resolution", type=float, default=MB_RESOLUTION)
    p.add_argument("--threshold",  type=float, default=MB_THRESHOLD)
    p.add_argument("--vertex_r",   type=float, default=VERTEX_RADIUS)
    p.add_argument("--center_r",   type=float, default=CENTER_RADIUS)
    p.add_argument("--min_r",      type=float, default=MIN_RADIUS)
    p.add_argument("--n_interior", type=int,   default=N_INTERIOR)
    p.add_argument("--sag",        type=float, default=MAX_SAG_PCT)
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


def add_edge_balls(mb, p1: Vector, p2: Vector, r_sphere: float,
                   n_interior: int, max_sag_pct: float,
                   center_r: float, min_r: float,
                   center_stiff: float, edge_stiff: float):
    """
    2頂点間（球面スケール済み）にエッジメタボールを配置
    generate_metaball_10.py の add_edge_balls と同構造
    """
    # 端点ボール
    for pos in (p1, p2):
        e = mb.elements.new()
        e.type = 'BALL'
        e.co = pos
        e.radius = min_r
        e.stiffness = edge_stiff

    # 内部補間点
    u1 = p1.normalized()
    u2 = p2.normalized()

    for i in range(1, n_interior + 1):
        t = i / (n_interior + 1)

        # 大円弧補間（slerp）
        slerp_dir = slerp(u1, u2, t)
        slerp_pos = slerp_dir * r_sphere

        # 球心方向へのたわみ
        curve_t    = 1.0 - abs(2.0 * t - 1.0)
        sag_factor = (max_sag_pct / 100.0) * smoothstep(curve_t)
        to_center  = -slerp_pos  # 原点が球心
        dist_c     = to_center.length
        if dist_c > 1e-4:
            sagged_pos = slerp_pos + to_center.normalized() * (dist_c * sag_factor)
        else:
            sagged_pos = slerp_pos

        smooth_r  = smoothstep(curve_t)
        radius    = min_r    + (center_r    - min_r)    * smooth_r
        stiffness = edge_stiff + (center_stiff - edge_stiff) * smooth_r

        e = mb.elements.new()
        e.type = 'BALL'
        e.co = sagged_pos
        e.radius = radius
        e.stiffness = stiffness


def create_voronoi_metaball(data: dict, args) -> bpy.types.Object:
    r_outer  = data["r_outer"]
    verts_raw = data["vertices"]   # 単位球面上
    edges    = data["edges"]

    # mathutils.Vector に変換してスケール
    verts = [Vector(v) * r_outer for v in verts_raw]

    print(f"Voronoi頂点数: {len(verts)}")
    print(f"有効エッジ数:   {len(edges)}")

    mb = bpy.data.metaballs.new(MB_NAME)
    mb.resolution        = args.resolution
    mb.render_resolution = args.resolution
    mb.threshold         = args.threshold

    obj = bpy.data.objects.new(MB_NAME, mb)
    bpy.context.collection.objects.link(obj)

    # 頂点ボール（交差点）
    for v in verts:
        e = mb.elements.new()
        e.type = 'BALL'
        e.co = v
        e.radius = args.vertex_r
        e.stiffness = VERTEX_STIFFNESS

    # エッジボール
    for idx, (a, b) in enumerate(edges):
        add_edge_balls(
            mb, verts[a], verts[b], r_outer,
            args.n_interior, args.sag,
            args.center_r, args.min_r,
            CENTER_STIFFNESS, EDGE_STIFFNESS,
        )
        if idx % 200 == 0:
            print(f"  エッジ {idx}/{len(edges)} 処理中...")

    print(f"メタボール要素数: {len(mb.elements)}")
    return obj


def main():
    args = parse_args(sys.argv)

    # JSON読み込み
    with open(args.input) as f:
        data = json.load(f)
    print(f"=== Voronoi Sphere Metaball ===")
    print(f"  R={data['r_outer']}mm  seeds={data['n_seeds']}")
    print(f"  resolution={args.resolution}  threshold={args.threshold}")

    clear_scene()
    create_voronoi_metaball(data, args)

    bpy.ops.wm.save_as_mainfile(filepath=args.output)
    print(f"✅ Saved: {args.output}")


if __name__ == "__main__":
    main()
