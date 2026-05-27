import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist
from scipy.optimize import minimize
import plotly.graph_objects as go
import os

# --- 設定 ---
input_csv = 'kicad_diodes_padded.csv'
output_csv = 'kicad_sphere_leds_rotated.csv'
output_html = 'kicad_sphere_leds_rotated.html'

# ★各面の回転角度設定 (0〜4 の整数 × 72度)
# Face 0〜11 に対応
face_phases = [0, 1, 1, 2, 2, 1, 4, 4, 4, 4, 4, 4]

# 例: [0, 1, 2, 3, 4, 0, 1, 2, 3, 4, 0, 1]

def main():
    if not os.path.exists(input_csv):
        print(f"エラー: {input_csv} が見つかりません。")
        return

    # 1. データ読み込み
    df = pd.read_csv(input_csv)
    df = df.sort_values('Ref') # Ref順にソート
    original_xy = df[['X_mm', 'Y_mm']].values
    refs = df['Ref'].values
    
    # 2. 幾何学定義
    phi = (1 + np.sqrt(5)) / 2  
    a_user = 28.55
    
    face_centers = []
    for i in [-1, 1]:
        for j in [-1, 1]:
            face_centers.append([0, i, j * phi])
            face_centers.append([i, j * phi, 0])
            face_centers.append([j * phi, 0, i])
    face_centers = np.array(face_centers)
    face_centers = face_centers / np.linalg.norm(face_centers, axis=1)[:, None]

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
    
    p1 = np.array([1, 1, 1])
    p2 = np.array([phi, 1/phi, 0])
    dist_std = np.linalg.norm(p1 - p2)
    scale_factor = a_user / dist_std
    
    real_verts = verts * scale_factor
    ri = (a_user / 2) * np.sqrt((25 + 11 * np.sqrt(5)) / 10)

    # 3. 北極合わせ
    pole = np.array([0, 0, 1])
    dists_to_pole = np.linalg.norm(face_centers - pole, axis=1)
    target_idx = np.argmin(dists_to_pole)
    v_from = face_centers[target_idx]
    
    def rotation_matrix(vec1, vec2):
        a, b = (vec1 / np.linalg.norm(vec1)).reshape(3), (vec2 / np.linalg.norm(vec2)).reshape(3)
        v = np.cross(a, b)
        c = np.dot(a, b)
        s = np.linalg.norm(v)
        if s == 0: return np.eye(3) if c > 0 else -np.eye(3)
        k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        return np.eye(3) + k + k.dot(k) * ((1 - c) / (s ** 2))

    R_align = rotation_matrix(v_from, pole)
    face_centers_rotated = face_centers @ R_align.T
    real_verts_rotated = real_verts @ R_align.T

    # 4. ID割り当て順序の決定
    indices = np.arange(12)
    z_vals = face_centers_rotated[:, 2]
    
    idx_top_center = indices[np.argmax(z_vals)]
    idx_bottom_center = indices[np.argmin(z_vals)]
    
    remaining = [i for i in indices if i != idx_top_center and i != idx_bottom_center]
    top_ring_indices = [i for i in remaining if z_vals[i] > 0]
    bottom_ring_indices = [i for i in remaining if z_vals[i] < 0]
    
    def get_angle(idx):
        x, y, z = face_centers_rotated[idx]
        return np.arctan2(y, x)

    top_ring_sorted = sorted(top_ring_indices, key=get_angle, reverse=True)
    bottom_ring_sorted = sorted(bottom_ring_indices, key=get_angle, reverse=False)
    
    ordered_indices = [idx_top_center] + top_ring_sorted + [idx_bottom_center] + bottom_ring_sorted
    
    # 5. 各面の配置パラメータ準備 (★ここで回転を適用)
    face_params = []
    for face_id, original_idx in enumerate(ordered_indices):
        normal = face_centers_rotated[original_idx]
        center_pos = normal * ri
        
        # 幾何学的ロック（頂点合わせ）
        dists = np.linalg.norm(real_verts_rotated - center_pos, axis=1)
        closest_idx = np.argsort(dists)[:5]
        face_verts = real_verts_rotated[closest_idx]
        face_verts = face_verts[np.argsort(-face_verts[:, 2])]
        base_vertex = face_verts[0]
        
        target_up = base_vertex - center_pos
        target_up /= np.linalg.norm(target_up)
        
        z_axis = normal
        y_axis = target_up
        x_axis = np.cross(y_axis, z_axis)
        
        # 基準行列
        R_face = np.column_stack((x_axis, y_axis, z_axis))
        
        # ★追加回転の適用
        phase = face_phases[face_id]
        theta = phase * 72 * (np.pi / 180)
        c, s = np.cos(theta), np.sin(theta)
        R_phase = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        
        # 合成
        R_final = R_face @ R_phase
        
        face_params.append({'R': R_final, 'T': center_pos})

    R_stack = np.array([fp['R'] for fp in face_params])
    T_stack = np.array([fp['T'] for fp in face_params])

    # 6. 最適化計算
    X0 = original_xy.flatten()

    def get_global_points(params):
        current_xy = params.reshape((64, 2))
        local_pts = np.hstack((current_xy, np.zeros((64, 1))))
        rotated = np.matmul(local_pts, R_stack.transpose(0, 2, 1))
        global_pts = rotated + T_stack[:, np.newaxis, :]
        all_pts = global_pts.reshape(-1, 3)
        dists = np.linalg.norm(all_pts, axis=1)
        avg_r = np.mean(dists)
        sphere_pts = (all_pts / dists[:, None]) * avg_r
        return sphere_pts, avg_r

    def objective(params):
        diff = (params - X0).reshape((64, 2))
        moves = np.linalg.norm(diff, axis=1)
        penalty = np.sum(np.maximum(0, moves - 3.0)**2) * 1e6
        pts, _ = get_global_points(params)
        dists = pdist(pts)
        energy = np.sum(1.0 / (dists**2))
        return energy + penalty

    print("最適化計算を開始します...")
    bounds = [(x - 3.1, x + 3.1) for x in X0]
    res = minimize(objective, X0, method='L-BFGS-B', bounds=bounds, 
                   options={'disp': True, 'maxiter': 200})
    print(f"最適化完了: {res.message}")
    
    # 7. 出力
    final_pts, final_radius = get_global_points(res.x)
    
    out_data = []
    idx = 0
    for face_id in range(12):
        for led_idx in range(64):
            ref = refs[led_idx]
            px, py, pz = final_pts[idx]
            hemisphere = "Top" if face_id <= 5 else "Bottom"
            out_data.append([face_id, hemisphere, ref, px, py, pz])
            idx += 1
            
    df_out = pd.DataFrame(out_data, columns=['Face_ID', 'Hemisphere', 'Ref', 'X', 'Y', 'Z'])
    df_out.to_csv(output_csv, index=False)
    print(f"CSV保存完了: {output_csv}")
    
    # HTML
    fig = go.Figure()
    colors = dict(zip(range(12), ['#E6194B', '#3CB44B', '#FFE119', '#4363D8', '#F58231', '#911EB4',
                                  '#46F0F0', '#F032E6', '#BCF60C', '#FABEBE', '#008080', '#E6BEFF']))
    
    for face_id in range(12):
        face_df = df_out[df_out['Face_ID'] == face_id]
        color = colors[face_id]
        
        # 線
        fig.add_trace(go.Scatter3d(
            x=face_df['X'], y=face_df['Y'], z=face_df['Z'],
            mode='lines',
            line=dict(color=color, width=2),
            name=f"Face {face_id} (Line)",
            visible=True
        ))
        
        # 点
        fig.add_trace(go.Scatter3d(
            x=face_df['X'], y=face_df['Y'], z=face_df['Z'],
            mode='markers',
            marker=dict(size=4, color=color),
            name=f"Face {face_id} (LEDs)",
            text=[f"{r}" for r in face_df['Ref']],
            hoverinfo='text',
            visible=True
        ))

    # 球
    u = np.linspace(0, 2 * np.pi, 50)
    v = np.linspace(0, np.pi, 50)
    x_s = final_radius * np.outer(np.cos(u), np.sin(v))
    y_s = final_radius * np.outer(np.sin(u), np.sin(v))
    z_s = final_radius * np.outer(np.ones(np.size(u)), np.cos(v))
    fig.add_trace(go.Surface(x=x_s, y=y_s, z=z_s, opacity=0.1, showscale=False, colorscale='Greys', name='Sphere'))
    
    fig.update_layout(title="LED Sphere with Rotation Control", scene=dict(aspectmode='data'))
    fig.write_html(output_html)
    print(f"HTML保存完了: {output_html}")

if __name__ == "__main__":
    main()
