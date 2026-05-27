import pcbnew
import csv
import os

# --- 設定 ---

# ユーザー指定のパスを設定済み
CSV_FILE_PATH = "/Users/katano/isolation-sphere/kiban/WS2813-square-9x9/place_parts.csv"

# CSVファイルで座標が指定されている列の名前
# (id, parts, x, y 形式に対応)
REF_COLUMN_NAME = "parts"
X_COLUMN_NAME = "x"
Y_COLUMN_NAME = "y"

# --- スクリプト本体 ---

def place_parts_from_csv():

    board = pcbnew.GetBoard()
    if not board:
        print("エラー: 基板が開かれていません。")
    elif not os.path.exists(CSV_FILE_PATH):
        print(f"エラー: CSVファイルが見つかりません。")
        print(f"指定されたパス: {CSV_FILE_PATH}")
    else:
        print(f"CSVファイル '{CSV_FILE_PATH}' を読み込んで配置を開始します。")
        
        try:
            footprints_placed = 0
            footprints_not_found = 0

            # CSVファイルを辞書型で読み込む
            with open(CSV_FILE_PATH, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                for i, row in enumerate(reader):
                    try:
                        # CSVからリファレンスと座標を取得
                        ref = row[REF_COLUMN_NAME]
                        x_mm = float(row[X_COLUMN_NAME])
                        y_mm = float(row[Y_COLUMN_NAME])

                        # === 修正点 ===
                        # KiCad v6以降のAPI (FindFootprintByReference) に変更
                        footprint = board.FindFootprintByReference(ref)

                        if footprint:
                            # 座標をmmからKiCad内部単位 (nm) に変換
                            pos_x_nm = pcbnew.FromMM(x_mm)
                            pos_y_nm = pcbnew.FromMM(y_mm)
                            
                            # 新しい座標 (VECTOR2I) を設定
                            new_pos = pcbnew.VECTOR2I(pos_x_nm, pos_y_nm)
                            
                            # === 修正点 ===
                            footprint.SetPosition(new_pos)
                            
                            footprints_placed += 1
                        else:
                            print(f"警告: 部品 '{ref}' (CSV {i+2}行目) が基板上に見つかりません。")
                            footprints_not_found += 1

                    except KeyError as e:
                        print(f"エラー: CSVファイルに必要な列 ({e}) がありません。")
                        print(f"'{REF_COLUMN_NAME}', '{X_COLUMN_NAME}', '{Y_COLUMN_NAME}' が必要です。")
                        break
                    except ValueError as e:
                        print(f"エラー: CSV {i+2}行目の座標値が無効です。({e})")
                        print(f"  リファレンス: {row.get(REF_COLUMN_NAME, 'N/A')}, X: {row.get(X_COLUMN_NAME, 'N/A')}, Y: {row.get(Y_COLUMN_NAME, 'N/A')}")
                    except Exception as e:
                        print(f"予期せぬエラー (行: {row}) - {e}")

            # Pcbnewエディタの表示を更新
            pcbnew.Refresh()
            print("---")
            print("配置が完了しました。")
            print(f"配置されたフットプリント数: {footprints_placed}")
            if footprints_not_found > 0:
                print(f"見つからなかったフットプリント数: {footprints_not_found}")

        except Exception as e:
            print(f"スクリプト実行中にエラーが発生しました: {e}")