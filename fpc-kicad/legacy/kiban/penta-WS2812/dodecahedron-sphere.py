import numpy as np
import pandas as pd
import plotly.graph_objects as go
import os

# --- 設定 ---
input_csv_path = 'kicad_diodes_padded.csv'
output_csv_name = 'sphere_leds.csv'
output_html_name = 'sphere_leds.html'

# 各面の回転角度設定 (0〜4 の整数 × 72度)
face_phases = [0] * 12 

def generate_spherical_leds():
    if not os.path.exists(input_csv_path):
        print(f"エラー: {input_csv_path} が見つかりません。")
        return

    # 1. データ読み込み & 2D座標取得
    df = pd.read_csv(input_csv_path)
    points_2d = df[['X_mm', 'Y_mm']].values
    points_local = np.hstack((points_2d, np.zeros((points_2d.shape[0], 1))))

    # 2. 幾何学定義 (正十二面体構築用)
    phi = (1 + np.sqrt(5)) / 2  
    a_user = 28.55 
    
    # 面の中心（法線）定義
    face_centers_norm = []
    for i in [-1, 1]:
        for j in [-1, 1]:
            face_centers_norm.append([0, i, j * phi])
            face_centers_norm.append([i, j * phi, 0])
            face_centers_norm.append([j * phi, 0, i])
    face_centers_norm = np.array(face_centers_norm)
    face_centers_norm = face_centers_norm / np.linalg.norm(face_centers_norm, axis=1)[:, None]

    # 正十二面体の頂点定義（位置合わせ用）
    verts = []
    for i in [-1, 1]:
        for j in [-1, 1]:
            for k in [-1, 1]:
                verts.append([i, j, k])
    for i in [-1, 1]:
        for j in [-1, 1]:
            verts.append([0, i * phi, j / phi])
            verts.append([j / phi, 0, i * phi])
            verts.append([i * phi, j / phi, 0])
    verts = np.array(verts)
    
    # スケール計算
    p1 = np.array([1, 1, 1])
    p2 = np.array([phi, 1/phi, 0])
    dist_std = np.linalg.norm(p1 - p2)
    scale_factor = a_user / dist_std
    real_verts = verts * scale_factor
    ri = (a_user / 2) * np.sqrt((25 + 11 * np.sqrt(5)) / 10)

    # 3. 正十二面体配置の計算 (一旦3D配置を作る)
    dodeca_points = []
    
    for i, normal in enumerate(face_centers_norm):
        center_pos = normal * ri
        
        # 頂点合わせロジック
        dists = np.linalg.norm(real_verts - center_pos, axis=1)
        closest_indices = np.argsort(dists)[:5]
        face_vertices = real_verts[closest_indices]
        base_vertex = face_vertices[0]
        
        target_up_vector = base_vertex - center_pos
        target_up_vector = target_up_vector / np.linalg.norm(target_up_vector)
        
        new_z = normal
        new_y = target_up_vector
        new_x = np.cross(new_y, new_z)
        
        R_base = np.column_stack((new_x, new_y, new_z))
        
        theta = face_phases[i] * 72 * (np.pi / 180)
        c, s = np.cos(theta), np.sin(theta)
        R_phase = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        
        R_final = R_base @ R_phase
        
        rotated_points = points_local @ R_final.T
        final_points = rotated_points + center_pos
        
        for j, p in enumerate(final_points):
            ref_name = df.iloc[j]['Ref']
            dodeca_points.append([i, ref_name, p[0], p[1], p[2]])

    dodeca_df = pd.DataFrame(dodeca_points, columns=['Face_ID', 'Ref', 'X', 'Y', 'Z'])

    # 4. 球面への投影処理
    # 全点の原点からの距離を計算
    coords = dodeca_df[['X', 'Y', 'Z']].values
    distances = np.linalg.norm(coords, axis=1)
    
    # 平均半径を計算 (これを球の半径とする)
    avg_radius = np.mean(distances)
    print(f"投影球の半径: {avg_radius:.2f} mm")
    
    # 投影実行: (x,y,z) / distance * avg_radius
    # 各点を正規化して半径倍する
    sphere_coords = (coords / distances[:, None]) * avg_radius
    
    # 結果をデータフレームに格納
    sphere_df = dodeca_df.copy()
    sphere_df['X'] = sphere_coords[:, 0]
    sphere_df['Y'] = sphere_coords[:, 1]
    sphere_df['Z'] = sphere_coords[:, 2]
    
    # CSV保存
    sphere_df.to_csv(output_csv_name, index=False)
    print(f"保存完了: CSVファイル -> {output_csv_name}")

    # 5. Plotly描画 (球面版)
    fig = go.Figure()

    for face_id in range(12):
        face_data = sphere_df[sphere_df['Face_ID'] == face_id]
        
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

    # 球のワイヤーフレームを参考表示 (薄く)
    # 半径 avg_radius の球を描画
    u = np.linspace(0, 2 * np.pi, 50)
    v = np.linspace(0, np.pi, 50)
    x_sphere = avg_radius * np.outer(np.cos(u), np.sin(v))
    y_sphere = avg_radius * np.outer(np.sin(u), np.sin(v))
    z_sphere = avg_radius * np.outer(np.ones(np.size(u)), np.cos(v))

    fig.add_trace(go.Surface(
        x=x_sphere, y=y_sphere, z=z_sphere,
        opacity=0.1, # 透明度を高くして中身が見えるように
        showscale=False,
        colorscale='Greys',
        name='Reference Sphere'
    ))

    fig.update_layout(
        title=f"Spherical Projection of LED Array (R={avg_radius:.1f}mm)",
        scene=dict(
            xaxis_title='X (mm)',
            yaxis_title='Y (mm)',
            zaxis_title='Z (mm)',
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=40)
    )

    fig.write_html(output_html_name)
    print(f"保存完了: HTMLファイル -> {output_html_name}")

if __name__ == "__main__":
    generate_spherical_leds()


