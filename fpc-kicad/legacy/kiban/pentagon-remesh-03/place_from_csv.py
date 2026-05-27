import pcbnew
import csv

csv_path = "/Users/katano/isolation-sphere/kiban/pentagon-big/pentagon_90.csv"
board = pcbnew.GetBoard()


def toggle_ref_value_display(ref_prefix="C", show_ref=False, show_value=False):
    board = pcbnew.GetBoard()

    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith(ref_prefix):  # 例: D1, D2, ...
            fp.Reference().SetVisible(show_ref)
            fp.Value().SetVisible(show_value)
            print(f"{ref}: Reference={'ON' if show_ref else 'OFF'}, Value={'ON' if show_value else 'OFF'}")

    print("✅ Visibility update complete.")


def set_reference_text_size(ref_prefix="D", height_mm=1.0, width_mm=1.0, thickness_mm=0.15):
    board = pcbnew.GetBoard()
    for fp in board.GetFootprints():
        if fp.GetReference().startswith(ref_prefix):
            ref = fp.Reference()
            ref.SetHeight(pcbnew.FromMM(height_mm))
            ref.SetWidth(pcbnew.FromMM(width_mm))
            ref.SetThickness(pcbnew.FromMM(thickness_mm))
            print(f"{fp.GetReference()}: Set size={height_mm}mm, thickness={thickness_mm}mm")

    print("✅ Reference size updated.")


# def draw_circles_on_footprints(layer_name="F.SilkS", radius_mm=1.0, linewidth_mm=0.15, ref_prefix="D"):
#     board = pcbnew.GetBoard()
    
#     if layer_name == "F.SilkS":
#         layer = pcbnew.F_SilkS
#     elif layer_name == "Edge.Cuts":
#         layer = pcbnew.Edge_Cuts
#     else:
#         raise ValueError("Invalid layer name. Use 'F.SilkS' or 'Edge.Cuts'.")

#     for fp in board.GetFootprints():
#         if fp.GetReference().startswith(ref_prefix):
#             circle = pcbnew.PCB_SHAPE(board)
#             circle.SetShape(pcbnew.SHAPE_T.CIRCLE)
#             circle.SetLayer(layer)
#             circle.SetCenter(fp.GetPosition())
#             circle.SetRadius(pcbnew.FromMM(radius_mm))
#             circle.SetWidth(pcbnew.FromMM(linewidth_mm))  # ✅ 線幅指定
#             board.Add(circle)
#             print(f"◯ {fp.GetReference()}: radius={radius_mm}mm, width={linewidth_mm}mm on {layer_name}")

#     print(f"✅ All circles added on {layer_name}")
def draw_circles_on_footprints(layer_name="F.SilkS", radius_mm=1.75, linewidth_mm=0.05, ref_prefix="D"):
    board = pcbnew.GetBoard()

    # レイヤー変換
    if layer_name == "F.SilkS":
        layer = pcbnew.F_SilkS
    elif layer_name == "Edge.Cuts":
        layer = pcbnew.Edge_Cuts
    else:
        raise ValueError("Invalid layer name. Use 'F.SilkS' or 'Edge.Cuts'.")

    for fp in board.GetFootprints():
        if fp.GetReference().startswith(ref_prefix):
            center = fp.GetPosition()
            radius = pcbnew.FromMM(radius_mm)

            # 円を描く（100%円形のアークとして実装）
            circle = pcbnew.PCB_SHAPE(board)
            circle.SetLayer(layer)
            circle.SetShape(pcbnew.S_CIRCLE)
            circle.SetCenter(center)
            circle.SetRadius(radius)
            circle.SetWidth(pcbnew.FromMM(linewidth_mm))

            board.Add(circle)
            print(f"◯ {fp.GetReference()} at {center} → radius={radius_mm}mm")

    print(f"✅ All circles added on layer {layer_name}")

def delete_circles_on_layer(layer_name="F.SilkS", ref_prefix=None):
    board = pcbnew.GetBoard()

    # レイヤー取得
    if layer_name == "F.SilkS":
        layer = pcbnew.F_SilkS
    elif layer_name == "Edge.Cuts":
        layer = pcbnew.Edge_Cuts
    else:
        raise ValueError("Invalid layer name")

    # フットプリントの中心位置一覧（ref_prefixが指定されていれば）
    center_set = set()
    if ref_prefix:
        for fp in board.GetFootprints():
            if fp.GetReference().startswith(ref_prefix):
                center_set.add(fp.GetPosition())

    shapes_to_delete = []
    for drawing in board.GetDrawings():
        if isinstance(drawing, pcbnew.PCB_SHAPE):
            if drawing.GetLayer() == layer and drawing.GetShape() == pcbnew.S_CIRCLE:
                if ref_prefix:
                    if drawing.GetCenter() not in center_set:
                        continue  # 中心が一致しなければ除外
                shapes_to_delete.append(drawing)

    for shape in shapes_to_delete:
        board.Remove(shape)
        print(f"🗑 Deleted circle at {shape.GetCenter()} on {layer_name}")

    print(f"✅ {len(shapes_to_delete)} circle(s) deleted from {layer_name}")




def set_footprint(ref_prefix="D", csv_path=csv_path):
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ref = ref_prefix + f"{int(row['FaceID']) + 1}"  # 必要に応じて+1を外す
            # ref = f"D{int(row['FaceID']) + 1}"  # 必要に応じて+1を外す
            x = float(row['x'])
            y = float(row['y'])
            theta = float(row['theta'])

            fp = board.FindFootprintByReference(ref)
            if fp is None:
                print(f"[Warning] {ref} not found")
                continue

            # ✅ KiCad 6/7共通：VECTOR2Iに明示的に変換
            pos = pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
            fp.SetPosition(pos)

            fp.SetOrientationDegrees(theta)
            print(f"Set {ref}: x={x}mm, y={y}mm, theta={theta}deg")

    print("✅ Placement complete.")


# with open(csv_path, "r", newline="") as f:
#     reader = csv.DictReader(f)
#     for row in reader:
#         ref = f"C{int(row['FaceID']) + 1}"  # 必要に応じて+1を外す
#         # ref = f"D{int(row['FaceID']) + 1}"  # 必要に応じて+1を外す
#         x = float(row['x'])
#         y = float(row['y'])
#         theta = float(row['theta'])

#         fp = board.FindFootprintByReference(ref)
#         if fp is None:
#             print(f"[Warning] {ref} not found")
#             continue

#         # ✅ KiCad 6/7共通：VECTOR2Iに明示的に変換
#         pos = pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
#         fp.SetPosition(pos)

#         fp.SetOrientationDegrees(theta)

# print("✅ Placement complete.")
