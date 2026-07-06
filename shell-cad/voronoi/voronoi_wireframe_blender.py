"""
Voronoi Sphere — Wireframe + Subdivision版
球面Voronoiのポリゴンメッシュを構築し、
WireframeモディファイアとSubdivision Surfaceで有機的な穴を生成

【アプローチ】
  1. JSON（gen_voronoi_json.py出力）からVoronoi頂点・セルを読み込み
  2. bmeshで球面上に各セルの多角形面を構築（頂点は球面に投影）
  3. Wireframe modifier  → エッジをチューブ化（穴が開く）
  4. Subdivision Surface → 全体を滑らかに丸める
  5. .blend保存 / STL出力

【Usage】
  # Step 1: Voronoiデータ生成（scipy環境）
  python3 gen_voronoi_json.py voronoi_data.json

  # Step 2: Blender実行
  /Applications/Blender.app/Contents/MacOS/Blender -b \\
    -P voronoi_wireframe_blender.py -- \\
    --input  voronoi_data.json \\
    --output voronoi_wireframe.blend

【主要パラメータ（--オプションで上書き可）】
  --thickness   リブの太さ mm （デフォルト 1.2）
  --subdivisions  Subdivision levels （デフォルト 3）
  --project_r   球面投影半径 mm （デフォルトはJSONのr_outer）
  --stl         STL出力パス（省略可）
  --apply       モディファイアを適用してSTL/blendに焼き込む（フラグ）
"""
from __future__ import annotations

import sys
import math
import json
import argparse

import bpy
import bmesh
from mathutils import Vector


# ── デフォルトパラメータ ──────────────────────────────────
WIREFRAME_THICKNESS  = 1.2   # mm  リブの太さ（大きいほど穴が小さい）
WIREFRAME_OFFSET     = 0.0   # -1〜1  オフセット方向（0=中心）
WIREFRAME_USE_EVEN   = True  # 均等な厚みにする
WIREFRAME_USE_CREASE = False

SUBDIV_LEVELS        = 3     # Subdivision levels（3〜4が実用的）
SUBDIV_TYPE          = 'CATMULL_CLARK'

OBJ_NAME = "VoronoiSphere"


def parse_args(argv):
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    p = argparse.ArgumentParser()
    p.add_argument("--input",       required=True,  help="voronoi_data.json")
    p.add_argument("--output",      required=True,  help="出力 .blend")
    p.add_argument("--stl",         default=None,   help="STL出力パス（省略可）")
    p.add_argument("--thickness",   type=float, default=WIREFRAME_THICKNESS)
    p.add_argument("--subdivisions",type=int,   default=SUBDIV_LEVELS)
    p.add_argument("--project_r",   type=float, default=None,
                   help="球面投影半径（省略時はJSONのr_outer）")
    p.add_argument("--apply",       action="store_true",
                   help="モディファイアを適用してメッシュに焼き込む")
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


def project_to_sphere(v: Vector, r: float) -> Vector:
    """ベクトルを半径rの球面上に投影"""
    length = v.length
    if length < 1e-10:
        return Vector((r, 0, 0))
    return v * (r / length)


def build_voronoi_mesh(data: dict, r: float) -> bpy.types.Object:
    """
    Voronoiデータから球面メッシュを構築
    各セル = 多角形面（頂点は球面上）
    """
    verts_raw = data["vertices"]   # 単位球面上の頂点座標

    # 全頂点を球面にスケール
    verts_3d = [Vector(v) * r for v in verts_raw]

    # セル情報：各regionが1つの多角形面
    regions = data.get("regions")  # face定義があればそれを使う
    edges   = data.get("edges")    # エッジリスト

    mesh = bpy.data.meshes.new(OBJ_NAME)
    bm   = bmesh.new()

    # 頂点を追加
    bm_verts = [bm.verts.new(v) for v in verts_3d]
    bm.verts.ensure_lookup_table()

    if regions:
        # セル面を追加（regionは頂点インデックスの順序付きリスト）
        face_count = 0
        for region in regions:
            if len(region) < 3:
                continue
            face_verts = [bm_verts[i] for i in region]
            try:
                bm.faces.new(face_verts)
                face_count += 1
            except ValueError:
                # 重複面や既存エッジの問題はスキップ
                pass
        print(f"面数: {face_count} / {len(regions)}")
    else:
        # regionsがない場合はedgesだけ追加（Wireframeはエッジからも動作）
        edge_count = 0
        for a, b in edges:
            try:
                bm.edges.new([bm_verts[a], bm_verts[b]])
                edge_count += 1
            except ValueError:
                pass
        print(f"エッジ数: {edge_count}")

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(OBJ_NAME, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    return obj


def add_modifiers(obj: bpy.types.Object, thickness: float,
                  subdiv_levels: int, apply_mods: bool):
    """
    Wireframe + Subdivision Surfaceモディファイアを追加
    apply_mods=True のときはメッシュに焼き込む
    """

    # ── 1. Wireframe ──────────────────────────────────────
    wf = obj.modifiers.new(name="Wireframe", type='WIREFRAME')
    wf.thickness         = thickness
    wf.use_even_offset   = WIREFRAME_USE_EVEN
    wf.use_replace       = True   # 元の面を削除して純粋なリブだけにする
    wf.offset            = WIREFRAME_OFFSET
    wf.use_crease        = WIREFRAME_USE_CREASE
    # 境界エッジも含める（球全体に穴が開く）
    wf.use_boundary      = False
    print(f"Wireframe: thickness={thickness}mm")

    # ── 2. Subdivision Surface ────────────────────────────
    sub = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    sub.subdivision_type = SUBDIV_TYPE
    sub.levels           = subdiv_levels           # ビューポート
    sub.render_levels    = subdiv_levels            # レンダー
    print(f"Subdivision: levels={subdiv_levels} ({SUBDIV_TYPE})")

    # ── モディファイアの適用 ──────────────────────────────
    if apply_mods:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        for mod in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)
            print(f"  モディファイア適用: {mod.name}")

        vcount = len(obj.data.vertices)
        fcount = len(obj.data.polygons)
        print(f"適用後: 頂点={vcount}, 面={fcount}")


def export_stl(obj: bpy.types.Object, stl_path: str):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_mesh.stl(
        filepath=stl_path,
        use_selection=True,
        global_scale=1.0,
        use_mesh_modifiers=True,   # モディファイア未適用でもSTLに反映
    )
    print(f"✅ STL: {stl_path}")


def main():
    args = parse_args(sys.argv)

    # JSON読み込み
    with open(args.input) as f:
        data = json.load(f)

    r = args.project_r if args.project_r else data["r_outer"]
    print(f"=== Voronoi Wireframe Sphere ===")
    print(f"  R={r}mm  seeds={data['n_seeds']}")
    print(f"  thickness={args.thickness}mm  subdivisions={args.subdivisions}")

    clear_scene()

    obj = build_voronoi_mesh(data, r)
    add_modifiers(obj, args.thickness, args.subdivisions, args.apply)

    if args.stl:
        export_stl(obj, args.stl)

    bpy.ops.wm.save_as_mainfile(filepath=args.output)
    print(f"✅ Blend: {args.output}")


if __name__ == "__main__":
    main()
