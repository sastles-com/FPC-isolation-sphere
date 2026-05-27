import numpy as np
import pandas as pd
import plotly.graph_objects as go
import os

# --- 設定 ---
input_csv_path = 'kicad_diodes_padded.csv'
output_html_name = 'dodecahedron_leds_corrected.html'

# 各面の回転角度設定 (0〜4 の整数 × 72度)
# ここを変更することで、各面を72度刻みで回転させても、必ず隣の辺と整合します
face_phases = [0] * 12 
# テスト用ランダムパターン（コメントアウトを外して試せます）
# face_phases = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1] 

def generate_dodecahedron_leds_corrected():
    if not os.path.exists(input_csv_path):
        print(f"エラー: {input_csv_path} が見つかりません。")
        return

    # 1. データ読み込み
    df = pd.read_csv(input_csv_path)
    points_2d = df[['X_mm', 'Y_mm']].values
    points_local = np.hstack((points_2d, np.zeros((points_2d.shape[0], 1))))

    # 2. 幾何学定義 (正十二面体)
    # 黄金比
    phi = (1 + np.sqrt(5)) / 2  
    
    # 正五角形の一辺の長さ (ユーザー定義)
    a_user = 28.55 
    
    # 正規化された正十二面体の定義 (辺の長さ = 2/phi)
    # Step A: 面の中心（＝正二十面体の頂点）の定義 => これが法線ベクトルになる
    face_centers_norm = []
    for i in [-1, 1]:
        for j in [-1, 1]:
            face_centers_norm.append([0, i, j * phi])
            face_centers_norm.append([i, j * phi, 0])
            face_centers_norm.append([j * phi, 0, i])
    face_centers_norm = np.array(face_centers_norm)
    # 正規化
    face_centers_norm = face_centers_norm / np.linalg.norm(face_centers_norm, axis=1)[:, None]

    # Step B: 正十二面体の頂点座標の定義 (幾何学的に正しい位置)
    # (±1, ±1, ±1)
    verts = []
    for i in [-1, 1]:
        for j in [-1, 1]:
            for k in [-1, 1]:
                verts.append([i, j, k])
    # (0, ±phi, ±1/phi) とその巡回
    for i in [-1, 1]:
        for j in [-1, 1]:
            verts.append([0, i * phi, j / phi])
            verts.append([j / phi, 0, i * phi])
            verts.append([i * phi, j / phi, 0])
    verts = np.array(verts)
    
    # Step C: スケール合わせ
    # 定義上の正十二面体の一辺の長さを計算
    # 頂点 (1, 1, 1) と (phi, 1/phi, 0) の距離
    p1 = np.array([1, 1, 1])
    p2 = np.array([phi, 1/phi, 0])
    dist_std = np.linalg.norm(p1 - p2) # これが幾何学定義上の辺の長さ
    
    # ユーザー指定の辺の長さ(a_user)になるようにスケール倍率を決定
    scale_factor = a_user / dist_std
    
    # 頂点と中心を実際のサイズに拡大
    real_verts = verts * scale_factor
    real_centers = face_centers_norm * np.linalg.norm(real_verts[0]) # 近似: 面の中心距離を計算してもよいが、法線方向へ移動させるため下記を使用
    
    # 正確な内接球半径 (原点から面までの距離)
    ri = (a_user / 2) * np.sqrt((25 + 11 * np.sqrt(5)) / 10)


    # 3. 座標変換と配置
    all_leds = []
    
    # 基板上の「上」方向ベクトル（Y軸プラス）
    pcb_up_vector = np.array([0, 1, 0])

    for i, normal in enumerate(face_centers_norm):
        # 現在の面(i)の中心位置
        center_pos = normal * ri
        
        # この面に属する5つの頂点を探す
        # 方法: 中心位置から各頂点への距離が最小になる5点を選ぶ
        dists = np.linalg.norm(real_verts - center_pos, axis=1)
        # 距離が近い順にインデックスを取得（上位5つ）
        closest_indices = np.argsort(dists)[:5]
        face_vertices = real_verts[closest_indices]
        
        # ターゲットとなる頂点を決定する (基準となる1つを選ぶ)
        # ここでは単純にリストの最初の1つを「0度（基準）」とする
        # ※実際には頂点の並び順を時計回りに整理したほうが直感的だが、計算上は「ある頂点」があれば良い
        base_vertex = face_vertices[0]
        
        # 基準頂点への方向ベクトル (ローカル平面上でのターゲットY軸)
        # 面の中心から、その頂点に向かうベクトル
        target_up_vector = base_vertex - center_pos
        target_up_vector = target_up_vector / np.linalg.norm(target_up_vector)
        
        # --- 回転行列の作成 (Gram-Schmidt的な構築) ---
        # 新しい座標系のZ軸 = 面の法線 (normal)
        new_z = normal
        
        # 新しい座標系のY軸 = さきほど決めたターゲット方向 (target_up_vector)
        # ただし、厳密に直交しているか確認（計算誤差対策）
        # target_up_vector は面上の点へのベクトルなので、normalとは直交しているはず
        new_y = target_up_vector
        
        # 新しい座標系のX軸 = Y cross Z
        new_x = np.cross(new_y, new_z)
        
        # 基準の回転行列 (Local -> Global)
        # [ new_x, new_y, new_z ] を列ベクトルとして並べる
        R_base = np.column_stack((new_x, new_y, new_z))
        
        # --- ユーザー指定の回転 (Phase) ---
        # Z軸周りに追加で回転させる
        theta = face_phases[i] * 72 * (np.pi / 180)
        c, s = np.cos(theta), np.sin(theta)
        R_phase = np.array([
            [c, -s, 0],
            [s, c, 0],
            [0, 0, 1]
        ])
        
        # 最終的な回転行列 = R_base * R_phase
        # (ローカル点をまずphase回転し、そのあとBase配置する順序)
        R_final = R_base @ R_phase
        
        # 座標変換実行
        rotated_points = points_local @ R_final.T
        final_points = rotated_points + center_pos
        
        # 保存
        for j, p in enumerate(final_points):
            ref_name = df.iloc[j]['Ref']
            all_leds.append([i, ref_name, p[0], p[1], p[2]])

    led_df = pd.DataFrame(all_leds, columns=['Face_ID', 'Ref', 'X', 'Y', 'Z'])

    # 4. Plotly描画
    fig = go.Figure()

    # 面ごとにプロット
    for face_id in range(12):
        face_data = led_df[led_df['Face_ID'] == face_id]
        
        # 色分け（隣り合う面が見やすいように）
        fig.add_trace(go.Scatter3d(
            x=face_data['X'],
            y=face_data['Y'],
            z=face_data['Z'],
            mode='markers',
            marker=dict(size=3),
            name=f'Face {face_id}',
            text=[f"{r} (Face {face_id})" for r in face_data['Ref']],
            hoverinfo='text'
        ))

    # ワイヤーフレーム表示（正十二面体の辺を表示して整合性を確認）
    # 全面の頂点を集めてHullを描くのは重いので、簡易的に線を引く
    # (ここでは省略しますが、LEDの配置自体が辺を形成しているはずです)

    fig.update_layout(
        title="Correctly Aligned Dodecahedron LED Array",
        scene=dict(
            xaxis_title='X (mm)',
            yaxis_title='Y (mm)',
            zaxis_title='Z (mm)',
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=40)
    )

    fig.write_html(output_html_name)
    print(f"完了: 補正済みファイルを保存しました -> {output_html_name}")

if __name__ == "__main__":
    generate_dodecahedron_leds_corrected()

