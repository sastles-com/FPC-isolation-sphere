import bpy
import mathutils

def align_objects_to_radius(radius=60.0):
    """
    選択されたオブジェクトを原点中心の半径radiusの球面上に配置し、
    ローカルZ軸を外側（原点からのベクトル方向）に向けます。
    """
    # 選択されたオブジェクトを取得
    selected_objects = bpy.context.selected_objects
    
    if not selected_objects:
        print("オブジェクトが選択されていません。")
        return

    for obj in selected_objects:
        # 現在のワールド座標での位置
        current_pos = obj.location
        
        # 原点からのベクトルを取得
        vec = mathutils.Vector(current_pos)
        
        # 原点にいる場合は(0,0,1)をデフォルトの方向とする
        if vec.length == 0:
            vec = mathutils.Vector((0.0, 0.0, 1.0))
        
        # 指定された半径に移動
        new_pos = vec.normalized() * radius
        obj.location = new_pos
        
        # 回転の設定: ローカルZ軸を法線方向(new_posの正規化ベクトル)に合わせる
        # to_track_quat(track_axis, up_axis)
        # 'Z'軸を法線方向に向け、'Y'を上向きにする（一般的な姿勢）
        rotation_quat = vec.to_track_quat('Z', 'Y')
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = rotation_quat
        
        print(f"Object '{obj.name}' positioned at {new_pos}")

# 半径を指定して実行（100mm = 0.1m などの場合は単位系に注意）
# ユーザーの要件に合わせて、ここで半径を指定します。
TARGET_RADIUS = 52.0 

if __name__ == "__main__":
    align_objects_to_radius(radius=TARGET_RADIUS)
