import csv
import pcbnew

def place_powerloop(csv_path="placement_powerloop.csv"):
    board = pcbnew.GetBoard()
    placed = []
    missing = []

    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            ref = row["Ref"].strip()
            fp = board.FindFootprintByReference(ref)
            if fp:
                x_mm = float(row["X"])
                y_mm = float(row["Y"])
                rot = float(row["Angle"])
                
                # KiCad 9.0での複数の方法を試行
                success = False
                
                # 方法1: pcbnew.wxPointMM を使用 (mm単位直接指定)
                if not success:
                    try:
                        position = pcbnew.wxPointMM(x_mm, y_mm)
                        fp.SetPosition(position)
                        success = True
                        print(f"✅ Method 1 (wxPointMM) worked for {ref}")
                    except Exception as e1:
                        print(f"Method 1 failed for {ref}: {e1}")
                
                # 方法2: pcbnew.FromMM + wxPoint
                if not success:
                    try:
                        x_internal = pcbnew.FromMM(x_mm)
                        y_internal = pcbnew.FromMM(y_mm)
                        position = pcbnew.wxPoint(int(x_internal), int(y_internal))
                        fp.SetPosition(position)
                        success = True
                        print(f"✅ Method 2 (FromMM + wxPoint) worked for {ref}")
                    except Exception as e2:
                        print(f"Method 2 failed for {ref}: {e2}")
                
                # 方法3: VECTOR2I with manual property setting
                if not success:
                    try:
                        x_internal = int(pcbnew.FromMM(x_mm))
                        y_internal = int(pcbnew.FromMM(y_mm))
                        position = pcbnew.VECTOR2I()
                        position.x = x_internal
                        position.y = y_internal
                        fp.SetPosition(position)
                        success = True
                        print(f"✅ Method 3 (VECTOR2I manual) worked for {ref}")
                    except Exception as e3:
                        print(f"Method 3 failed for {ref}: {e3}")
                
                if not success:
                    print(f"❌ All positioning methods failed for {ref}")
                    continue
                
                # 角度設定
                try:
                    fp.SetOrientationDegrees(rot)
                except:
                    try:
                        # 古いバージョン用のフォールバック (度 * 10)
                        fp.SetOrientation(int(rot * 10))
                    except Exception as e:
                        print(f"⚠️ Could not set orientation for {ref}: {e}")

                placed.append(ref)
            else:
                missing.append(ref)

    pcbnew.Refresh()
    print(f"✅ Placed: {placed}")
    if missing:
        print(f"⚠️ Missing footprints: {missing}")

if __name__ == "__main__":
    place_powerloop()
