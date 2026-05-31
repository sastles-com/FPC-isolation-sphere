import bpy
import csv
import os

def export_selected_objects_to_csv(filepath):
    """
    選択されたオブジェクトのワールド座標を取得し、CSVファイルに書き出します。
    """
    selected_objects = bpy.context.selected_objects
    
    if not selected_objects:
        print("オブジェクトが選択されていません。")
        return

    # データを収集
    data = []
    for obj in selected_objects:
        # ワールド行列から移動成分（ワールド座標）を取得
        world_pos = obj.matrix_world.to_translation()
        data.append([obj.name, world_pos.x, world_pos.y, world_pos.z])
    
    # ディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # CSV書き出し
    try:
        with open(filepath, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["name", "x", "y", "z"]) # Header
            writer.writerows(data)
        print(f"CSV exported successfully to: {filepath}")
        print(f"Exported {len(data)} objects.")
    except Exception as e:
        print(f"Error exporting CSV: {e}")

# 出力パスの設定
# results フォルダに出力するようにします。
output_filename = "selected_objects_coords.csv"
output_path = os.path.join(os.path.dirname(bpy.data.filepath), "results", output_filename)

if __name__ == "__main__":
    export_selected_objects_to_csv(output_path)

