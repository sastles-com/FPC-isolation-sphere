"""script_ tool: 選択頂点に「原点→頂点」方向を軸とする円柱を生成。

EDIT MODE でメッシュの頂点を選択 → このスクリプトを実行すると、OBJECT MODE 上に
各選択頂点の位置へ **原点からの位置ベクトルを軸(=垂直方向)** とする 16 分割円柱を作る。
hex 交点(Goldberg 頂点)を手で選んでボス/カッターの土台を置く用途。

  - 軸 = normalize(頂点のワールド座標)  → 球面なら radial 方向
  - 16 分割、直径・高さ・原点方向オフセットはスクリプト先頭で指定
  - 生成円柱は OBJECT MODE のコレクション "VertexCylinders" に追加(元メッシュは不変)

使い方:
  1. 対象メッシュを選択 → Tab で EDIT MODE
  2. 円柱を立てたい頂点を選択(複数可)
  3. Scripting タブでこのスクリプトを Run(EDIT/OBJECT どちらの mode でも可)

Blender 直: /Applications/Blender.app/Contents/MacOS/Blender --python <this>
"""
import bpy
import bmesh
from mathutils import Vector

# --- Parameters (mm) ---------------------------------------------------------
CYL_D       = 3.0     # 円柱直径
CYL_H       = 8.0     # 円柱の高さ(軸方向長さ) — ここで指定
CYL_SEGS    = 16      # 分割数
CYL_OFFSET  = 0.0     # 軸方向オフセット (頂点中心から; 負=原点側へ押し込む)
COLL_NAME   = "VertexCylinders"
# ------------------------------------------------------------------------------


def selected_world_coords(obj):
    """選択頂点のワールド座標リスト (EDIT/OBJECT 両対応)。"""
    mw = obj.matrix_world
    if obj.mode == "EDIT":
        bm = bmesh.from_edit_mesh(obj.data)
        return [mw @ v.co.copy() for v in bm.verts if v.select]
    return [mw @ v.co.copy() for v in obj.data.vertices if v.select]


def get_collection(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def make_radial_cylinder(p, coll, idx):
    """頂点ワールド座標 p に、原点→p を軸とする円柱を生成。"""
    d = p.normalized()
    if d.length < 1e-9:
        d = Vector((0.0, 0.0, 1.0))
    center = p + d * CYL_OFFSET
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=CYL_SEGS, radius=CYL_D / 2.0, depth=CYL_H, location=center)
    cyl = bpy.context.active_object
    cyl.name = f"VCyl_{idx:03d}"
    # +Z を radial 方向 d に向ける
    cyl.rotation_mode = "QUATERNION"
    cyl.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(d)
    # アクティブコレクションから外して指定コレクションへ
    for c in list(cyl.users_collection):
        c.objects.unlink(cyl)
    coll.objects.link(cyl)
    return cyl


def main():
    obj = bpy.context.active_object
    if obj is None or obj.type != "MESH":
        print("✗ アクティブなメッシュがありません。対象メッシュを選択してください。")
        return

    coords = selected_world_coords(obj)
    if not coords:
        print("✗ 選択頂点がありません。EDIT MODE で頂点を選択してください。")
        return

    # 円柱生成は OBJECT MODE で
    if obj.mode == "EDIT":
        bpy.ops.object.mode_set(mode="OBJECT")
    coll = get_collection(COLL_NAME)

    made = []
    for i, p in enumerate(coords):
        cyl = make_radial_cylinder(p, coll, i)
        r = p.length
        print(f"  VCyl_{i:03d} @ ({p.x:.2f},{p.y:.2f},{p.z:.2f})  r={r:.2f}  axis=radial")
        made.append(cyl)

    print(f"✓ {len(made)} radial cylinders (Ø{CYL_D}, h{CYL_H}, {CYL_SEGS}-seg) "
          f"→ collection '{COLL_NAME}'")


if __name__ == "__main__":
    main()
