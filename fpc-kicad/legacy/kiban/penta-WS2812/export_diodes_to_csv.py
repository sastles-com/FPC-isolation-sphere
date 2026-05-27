import pcbnew
import csv
import os
import re

# --- 設定 ---
output_path = os.path.join(os.path.expanduser("~"), "kicad_diodes_padded.csv")

def export_diodes_to_csv(filepath):
    board = pcbnew.GetBoard()
    diodes = []

    for fp in board.GetFootprints():
        ref = fp.GetReference()
        
        # リファレンスが "D" で始まるものを対象
        if ref.startswith("D"):
            # 数値部分を抽出してゼロ埋め処理を行う
            # 正規表現で D の後ろの数字を探す
            match = re.match(r"(D)(\d+)(.*)", ref)
            if match:
                prefix = match.group(1) # "D"
                number = int(match.group(2)) # 数字部分 (例: 1)
                suffix = match.group(3) # もし "D1A" のような場合の "A" (通常は空)
                
                # 2桁ゼロ埋めフォーマット (02d)
                formatted_ref = f"{prefix}{number:02d}{suffix}"
            else:
                # 数字が含まれない場合などはそのまま
                formatted_ref = ref

            # 座標と角度の取得
            pos = fp.GetPosition()
            x_mm = pcbnew.ToMM(pos.x)
            y_mm = pcbnew.ToMM(pos.y)
            rotation = fp.GetOrientation() / 10.0
            side = "Bottom" if fp.IsFlipped() else "Top"
            
            diodes.append([formatted_ref, x_mm, y_mm, side, rotation])

    # リファレンス名で並び替え（オプション：D01, D02...の順に並ぶと見やすいため）
    diodes.sort(key=lambda x: x[0])

    # CSV書き出し
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Ref', 'X_mm', 'Y_mm', 'Side', 'Rotation'])
            writer.writerows(diodes)
        print(f"成功: {len(diodes)} 個のダイオードを保存しました。\n保存先: {filepath}")
    except IOError as e:
        print(f"エラー: {e}")

export_diodes_to_csv(output_path)
