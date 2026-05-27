import pandas as pd
import numpy as np
import trimesh
import plotly.graph_objects as go
from collections import defaultdict

path = '/Users/katano/isolation-sphere/'


# ---------------------------
# 1. CSV から 3D 六角形データの読み込み
# ---------------------------
# df = pd.read_csv("hexa-8-tri.csv")
# df = pd.read_csv("/Users/katano/Documents/home/neon/git/isolation_sphere/_kiban/FPC_45/tri_hexagons.csv")
df = pd.read_csv(path + 'side-all.csv')

# FaceIDごとに6頂点の3D座標を辞書に格納
face_vertices = {}
face_ids = sorted(df["FaceID"].unique())
for fid in face_ids:
    row = df[df["FaceID"] == fid].iloc[0]
    verts = np.array([[row[f"V{i}X"], row[f"V{i}Y"], row[f"V{i}Z"]] for i in range(1, 7)])
    face_vertices[fid] = verts

# ---------------------------
# 2. vertex_connections.csv の読み込み
# ---------------------------
try:
    # vertex_connections.csv は以下の列を持つと仮定：
    # FaceID, VertexIndex, ConnectedFaceID, ConnectedVertexIndex, Reverse
    # vertex_conn_df = pd.read_csv("/Users/katano/Documents/home/neon/git/isolation_sphere/_kiban/FPC_45/tri_vertex_connections.csv")
    vertex_conn_df = pd.read_csv(path + 'tri_vertex_connections-side.csv')
    


    # 面間の接続情報を構築
    vertex_connections = defaultdict(list)
    connection_pairs = {}
    
    # 頂点接続情報を読み込む
    for _, row in vertex_conn_df.iterrows():
        fid = int(row["FaceID"])
        vertex_idx = int(row["VertexIndex"])
        connected_fid = int(row["ConnectedFaceID"])
        connected_vertex_idx = int(row["ConnectedVertexIndex"])
        reverse = bool(row["Reverse"])
        
        # 頂点接続情報を保存
        vertex_connections[(fid, vertex_idx)].append((connected_fid, connected_vertex_idx, reverse))
        
        # 面のペアごとに接続情報を集める
        pair_key = tuple(sorted([fid, connected_fid]))
        if pair_key not in connection_pairs:
            connection_pairs[pair_key] = []
        
        connection_pairs[pair_key].append((fid, vertex_idx, connected_fid, connected_vertex_idx, reverse))
    
    # 面のペアから接続シーケンスを構築
    connection_sequence = {}
    
    for (fid1, fid2), connections in connection_pairs.items():
        if len(connections) >= 2:  # 少なくとも2点の接続が必要
            # 面の順序を統一（小さいIDから大きいIDへの接続として記録）
            if fid1 < fid2:
                from_id, to_id = fid1, fid2
            else:
                from_id, to_id = fid2, fid1
            
            # 接続情報を整理
            from_vertices = []
            to_vertices = []
            reverse_flags = []
            
            for (src_fid, src_vertex, dst_fid, dst_vertex, rev) in connections:
                if src_fid == from_id:
                    from_vertices.append(src_vertex)
                    to_vertices.append(dst_vertex)
                    reverse_flags.append(rev)
                else:
                    from_vertices.append(dst_vertex)
                    to_vertices.append(src_vertex)
                    reverse_flags.append(rev)
            
            # 全ての接続で同じReverse値を使用（通常は同じはず）
            reverse = reverse_flags[0]
            
            # 接続シーケンスを保存
            connection_sequence[to_id] = (from_id, from_vertices, to_vertices, reverse)
    
    print(f"vertex_connections.csv から {len(connection_sequence)} 個の接続情報を構築しました。")
except Exception as e:
    print(f"vertex_connections.csv の読み込みに失敗しました: {e}")
    print(f"エラー詳細: {e}")
    connection_sequence = {}
    vertex_connections = defaultdict(list)
    print("連結情報がないため、展開を行いません。")

# ---------------------------
# 3. 各面の2D展開（最小二乗平面による剛体変換）
# ---------------------------
def project_face_to_2d(verts_3d):
    """
    6頂点の3D座標から、重心周りの最小二乗平面を求め、
    法線を Z軸に合わせる剛体変換のみで XY 平面に射影する。
    戻り値: (6×2) の2D頂点座標
    """
    centroid = np.mean(verts_3d, axis=0)
    centered = verts_3d - centroid
    # SVD により法線を取得
    _, _, vh = np.linalg.svd(centered)
    normal = vh[2]
    target = np.array([0, 0, 1])
    v = np.cross(normal, target)
    c = np.dot(normal, target)
    if np.linalg.norm(v) < 1e-8:
        R = np.eye(3)
    else:
        vx = np.array([
            [0, -v[2], v[1]],
            [v[2], 0, -v[0]],
            [-v[1], v[0], 0]
        ])
        R = np.eye(3) + vx + vx @ vx * (1/(1+c))
    rotated = (R @ centered.T).T
    return rotated[:, :2]

projected_faces_2d = {}
for fid, verts in face_vertices.items():
    projected_faces_2d[fid] = project_face_to_2d(verts)

# ---------------------------
# 4. 連結グループの識別と連続接続の再構築
# ---------------------------
def connect_faces(face_from_2d, face_to_2d, shared_info):
    """
    face_from_2D: 接続済みの前面の2D頂点座標 (6×2 numpy array)
    face_to_2D: 次面の元の2D展開前頂点座標 (6×2 numpy array)
    shared_info: (from_vertices, to_vertices, reverse) のタプル
    戻り値: face_to_2D に変換（回転＋平行移動＋必要なら反転）を施し、共有頂点の一致を実現した2D座標
    """
    from_vertices, to_vertices, reverse = shared_info
    
    # 接続する頂点ペアの座標を取得
    src_points = np.array([face_from_2d[v] for v in from_vertices])
    dst_points = np.array([face_to_2d[v] for v in to_vertices])
    
    # 反転が必要かどうかを確認
    flipped = False
    face_to_transformed = face_to_2d.copy()
    
    if reverse:
        # Reverseフラグがある場合、Y座標を反転して向きを変える
        face_to_transformed[:, 1] = -face_to_transformed[:, 1]
        flipped = True
    
    # 最小二乗法で回転・移動変換を求める
    # こちらの変換は、指定された頂点ペアが可能な限り近くなるようにする
    
    # 回転行列を求めるためのポイント座標
    src_center = np.mean(src_points, axis=0)
    dst_center = np.mean([face_to_transformed[v] for v in to_vertices], axis=0)
    
    # 中心からの相対座標
    src_centered = src_points - src_center
    dst_centered = np.array([face_to_transformed[v] for v in to_vertices]) - dst_center
    
    # 回転行列を計算（Kabsch algorithm）
    H = src_centered.T @ dst_centered
    U, _, Vt = np.linalg.svd(H)
    R = U @ Vt
    
    # 反射行列になっていないか確認（行列式が負なら反射）
    if np.linalg.det(R) < 0:
        Vt[-1, :] = -Vt[-1, :]
        R = U @ Vt
    
    # 回転を適用
    rotated = (R @ (face_to_transformed - dst_center).T).T + src_center
    
    # 最適な平行移動を計算（接続頂点の誤差を最小化）
    avg_error = 0
    for i, src_idx in enumerate(from_vertices):
        dst_idx = to_vertices[i]
        error = face_from_2d[src_idx] - rotated[dst_idx]
        avg_error += error
    
    avg_error /= len(from_vertices)
    
    # 最終的な変換を適用
    aligned = rotated + avg_error
    
    return aligned, flipped

# 連結情報から連結グループを識別
def identify_groups():
    """連結グループを識別する"""
    # 接続グラフを構築
    graph = defaultdict(list)
    for fid, (from_id, _, _, _) in connection_sequence.items():
        graph[from_id].append(fid)
        graph[fid].append(from_id)
    
    # グループの識別（BFSアルゴリズム）
    visited = set()
    groups = []
    
    for fid in face_ids:
        if fid in visited:
            continue
        
        # グラフに存在する面だけを処理（連結情報がある面）
        if fid not in graph and fid not in connection_sequence:
            continue
        
        group = []
        queue = [fid]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            
            visited.add(current)
            group.append(current)
            
            for neighbor in graph.get(current, []):
                if neighbor not in visited:
                    queue.append(neighbor)
        
        if group:  # 空でないグループのみ追加
            groups.append(group)
    
    return groups

connected_faces = {}
# 共有辺の情報と反転状態を格納
connected_info = {}
flipped_faces = set()

# 連結情報がある場合のみ処理
if connection_sequence:
    groups = identify_groups()
    print(f"{len(groups)} 個の連結グループを識別しました。")
    
    for i, group in enumerate(groups):
        print(f"グループ {i+1}: {group}")
        # 各グループの最初のFaceIDを基準面とする
        base_id = group[0]
        connected_faces[base_id] = projected_faces_2d[base_id]
        
        # 基準面から接続可能な面を順番に探索
        processed = {base_id}
        to_process = [(from_id, fid) for fid, (from_id, _, _, _) in connection_sequence.items() if from_id == base_id]
        
        while to_process:
            from_id, fid = to_process.pop(0)
            
            # 接続元が処理済みで、接続先が未処理の場合のみ処理
            if from_id in processed and fid not in processed:
                from_vertices, to_vertices, reverse = connection_sequence[fid][1:]
                face_aligned, flipped = connect_faces(connected_faces[from_id],
                                               projected_faces_2d[fid],
                                               (from_vertices, to_vertices, reverse))
                
                connected_faces[fid] = face_aligned
                
                # 反転状態を記録
                if flipped:
                    flipped_faces.add(fid)
                
                processed.add(fid)
                
                # 共有頂点の情報を記録
                connected_info[(from_id, fid)] = (from_vertices, to_vertices, reverse)
                
                # この面から接続される次の面を追加
                to_process.extend([(from_next, fid_next) for fid_next, (from_next, _, _, _) in connection_sequence.items() 
                               if from_next == fid and fid_next not in processed])

# ---------------------------
# 5. Plotly による可視化（頂点番号付き）
# ---------------------------
if connected_faces:  # 連結情報から処理された面がある場合のみ可視化
    fig = go.Figure()
    color_list = ['blue', 'orange', 'green', 'purple', 'red', 'brown', 'cyan', 'magenta']
    
    # 連結情報がある面のみ色を割り当て
    connected_face_ids = list(connected_faces.keys())
    face_colors = {fid: color_list[i % len(color_list)] for i, fid in enumerate(connected_face_ids)}
    
    # 各面をプロット
    for fid in connected_face_ids:
        coords = connected_faces[fid]
        
        # 六角形の線をプロット（閉じた線にするため、最初の点を最後にも追加）
        x = list(coords[:,0]) + [coords[0,0]]
        y = list(coords[:,1]) + [coords[0,1]]
        
        # 面のラベルに反転状態を追加
        face_label = f'FaceID {fid}'
        if fid in flipped_faces:
            face_label += ' (反転)'
        
        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            mode='lines',
            name=face_label,
            fill='toself',
            line=dict(color=face_colors[fid], width=2),
            hoveron='fills',
            hoverinfo='name'
        ))
        
        # 各頂点を個別にプロットし、頂点番号を表示するためのトレースを追加
        for i in range(6):
            # 共有点情報を集める
            shared_info = []
            for connected_fid, connected_vertex, reverse in vertex_connections.get((fid, i), []):
                shared_info.append(f"FaceID {connected_fid}, Vertex {connected_vertex}, Reverse {reverse}")
            
            # ホバーテキストの作成
            hover_text = f'FaceID {fid}, Vertex {i}'
            if shared_info:
                hover_text += '<br>共有: ' + '<br>'.join(shared_info)
            
            fig.add_trace(go.Scatter(
                x=[coords[i,0]],
                y=[coords[i,1]],
                mode='markers+text',
                marker=dict(
                    size=8,
                    color=face_colors[fid],
                    line=dict(width=1, color='black')
                ),
                text=f'{i}',
                textposition='top center',
                name=f'Vertex {i} of Face {fid}',
                showlegend=False,
                hoverinfo='text',
                hovertext=hover_text
            ))
    
    # 共有頂点を強調表示
    for (from_id, to_id), (from_vertices, to_vertices, reverse) in connected_info.items():
        if from_id in connected_faces and to_id in connected_faces:
            from_coords = connected_faces[from_id]
            to_coords = connected_faces[to_id]
            
            # 各接続頂点ペアを表示
            for i in range(len(from_vertices)):
                src_idx = from_vertices[i]
                dst_idx = to_vertices[i]
                
                # 共有頂点を点線で接続
                fig.add_trace(go.Scatter(
                    x=[from_coords[src_idx, 0], to_coords[dst_idx, 0]],
                    y=[from_coords[src_idx, 1], to_coords[dst_idx, 1]],
                    mode='lines',
                    line=dict(
                        color='black',
                        width=2,
                        dash='dot'
                    ),
                    name=f'共有点: Face{from_id}:{src_idx}-Face{to_id}:{dst_idx}',
                    showlegend=False,
                    hoverinfo='text',
                    hovertext=f'共有点: Face {from_id}, 頂点 {src_idx} ⟷ Face {to_id}, 頂点 {dst_idx}, Reverse={reverse}'
                ))
    
    fig.update_layout(
        title="展開された六角形構造（頂点番号付き）",
        xaxis_title="X",
        yaxis_title="Y",
        xaxis=dict(scaleanchor="y", scaleratio=1),
        showlegend=True,
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial"
        ),
        height=800,
        width=1000
    )
    fig.to_html(path + "tri_unfolded_hexagons-side.html", include_plotlyjs='cdn')
    print(path + "tri_unfolded_hexagons.html に展開結果を出力しました。")
    fig.show()
    
    # ---------------------------
    # 6. CSV 出力（展開結果と重心位置）
    # ---------------------------
    # 展開した六角形の座標と重心を出力
    records = []
    for fid in connected_face_ids:
        coords = connected_faces[fid]
        
        # 重心を計算
        centroid_x = np.mean(coords[:, 0])
        centroid_y = np.mean(coords[:, 1])
        
        row = {"FaceID": fid, "CentroidX": centroid_x, "CentroidY": centroid_y}
        
        # 頂点座標を追加
        for i in range(6):
            row[f"V{i+1}X"] = coords[i,0]
            row[f"V{i+1}Y"] = coords[i,1]
        records.append(row)
        
    result_df = pd.DataFrame(records).sort_values("FaceID")
    result_df.to_csv(path + "tri_unfolded_hexagons-side.csv", index=False)
    print("unfolded_hexagons.csv に展開座標と重心位置を出力しました。")
    
    # 重心位置のみの簡易版も出力
    centroid_records = []
    for fid in connected_face_ids:
        coords = connected_faces[fid]
        
        # 重心を計算
        centroid_x = np.mean(coords[:, 0])
        centroid_y = np.mean(coords[:, 1])
        
        centroid_records.append({
            "FaceID": fid,
            "CentroidX": centroid_x,
            "CentroidY": centroid_y,
            "Flipped": fid in flipped_faces
        })

    centroid_df = pd.DataFrame(centroid_records).sort_values("FaceID")
    centroid_df.to_csv(path + "tri_hexagon_centroids-side.csv", index=False)
    print("hexagon_centroids.csv に六角形の重心位置を出力しました。")
    
    # 頂点の接続関係を出力（コメントアウト）
    """
    vertex_records = []
    for (fid, vertex_idx), connections in vertex_connections.items():
        for connected_fid, connected_vertex, reverse in connections:
            vertex_records.append({
                "FaceID": fid,
                "VertexIndex": vertex_idx,
                "ConnectedFaceID": connected_fid,
                "ConnectedVertexIndex": connected_vertex,
                "Reverse": reverse
            })
    
    if vertex_records:
        vertex_df = pd.DataFrame(vertex_records)
        vertex_df.to_csv("vertex_connections.csv", index=False)
        print("vertex_connections.csv に頂点接続情報を出力しました。")
    """
    
    # 更新された接続シーケンスファイルを生成
    connection_records = []
    for fid, (from_id, idx_from_list, idx_to_list, reverse) in connection_sequence.items():
        if fid in connected_faces and from_id in connected_faces:
            # 対応する頂点のリストを文字列化
            from_vertices = "-".join([str(idx) for idx in idx_from_list])
            if reverse:
                # Reverse=Trueの場合、順序を逆にする
                to_vertices = "-".join([str(idx) for idx in reversed(idx_to_list)])
            else:
                to_vertices = "-".join([str(idx) for idx in idx_to_list])
                
            connection_records.append({
                "FaceID": fid,
                "FromFaceID": from_id,
                "FromVertices": from_vertices,
                "ToVertices": to_vertices,
                "Reverse": reverse
            })
    
    if connection_records:
        connection_df = pd.DataFrame(connection_records)
        connection_df.to_csv(path + "tri_detailed_connection_sequence-side.csv", index=False)
        print("detailed_connection_sequence.csv に詳細接続情報を出力しました。")
    
    # ---------------------------
    # 7. 辺の長さの比較と誤差分析
    # ---------------------------
    if connected_faces:
        print("\n辺の長さの比較と誤差分析:")
        print("------------------------")
        
        # 辺の長さの計算関数
        def calc_edge_lengths_2d(vertices_2d):
            """2D頂点座標から6つの辺の長さを計算"""
            lengths = []
            for i in range(6):
                p1 = vertices_2d[i]
                p2 = vertices_2d[(i+1) % 6]
                length = np.sqrt(np.sum((p2 - p1) ** 2))
                lengths.append(length)
            return lengths
        
        def calc_edge_lengths_3d(vertices_3d):
            """3D頂点座標から6つの辺の長さを計算"""
            lengths = []
            for i in range(6):
                p1 = vertices_3d[i]
                p2 = vertices_3d[(i+1) % 6]
                length = np.sqrt(np.sum((p2 - p1) ** 2))
                lengths.append(length)
            return lengths
        
        # 誤差統計
        all_errors = []
        max_error_info = {"fid": None, "edge": None, "error": 0}
        face_max_errors = {}
        
        # 各面ごとに辺の長さを比較
        for fid in connected_face_ids:
            # 2D展開後の辺の長さ
            lengths_2d = calc_edge_lengths_2d(connected_faces[fid])
            
            # 元の3D辺の長さ
            lengths_3d = calc_edge_lengths_3d(face_vertices[fid])
            
            # 誤差計算
            errors = []
            for i in range(6):
                # 絶対誤差
                abs_error = abs(lengths_2d[i] - lengths_3d[i])
                # 相対誤差 (%)
                rel_error = (abs_error / lengths_3d[i]) * 100
                
                errors.append(rel_error)
                all_errors.append(rel_error)
                
                # 最大誤差の更新
                if rel_error > max_error_info["error"]:
                    max_error_info = {"fid": fid, "edge": i, "error": rel_error}
            
            # この面の最大誤差
            face_max_errors[fid] = max(errors)
            
            # 結果出力
            print(f"Face ID {fid}:")
            for i in range(6):
                print(f"  辺 {i}-{(i+1)%6}: 2D長さ={lengths_2d[i]:.4f}, 3D長さ={lengths_3d[i]:.4f}, 差={lengths_2d[i]-lengths_3d[i]:.4f}, 相対誤差={errors[i]:.2f}%")
            print(f"  最大相対誤差: {max(errors):.2f}%\n")
        
        # 全体の統計情報
        avg_error = np.mean(all_errors)
        std_dev = np.std(all_errors)
        max_error = max(all_errors)
        min_error = min(all_errors)
        
        print("\n全体の誤差統計:")
        print(f"平均相対誤差: {avg_error:.2f}%")
        print(f"誤差の標準偏差: {std_dev:.2f}%")
        print(f"最小相対誤差: {min_error:.2f}%")
        print(f"最大相対誤差: {max_error:.2f}% (Face ID {max_error_info['fid']}, 辺 {max_error_info['edge']}-{(max_error_info['edge']+1)%6})")
        
        # 誤差の大きい順に面を表示
        print("\n誤差の大きい順の面:")
        sorted_faces = sorted(face_max_errors.items(), key=lambda x: x[1], reverse=True)
        for fid, error in sorted_faces[:10]:  # 上位10面を表示
            print(f"Face ID {fid}: 最大相対誤差 {error:.2f}%")
        
        # CSVに誤差情報を出力
        error_records = []
        for fid in connected_face_ids:
            lengths_2d = calc_edge_lengths_2d(connected_faces[fid])
            lengths_3d = calc_edge_lengths_3d(face_vertices[fid])
            
            row = {"FaceID": fid}
            max_rel_error = 0
            
            for i in range(6):
                edge_name = f"{i}-{(i+1)%6}"
                abs_error = abs(lengths_2d[i] - lengths_3d[i])
                rel_error = (abs_error / lengths_3d[i]) * 100
                
                row[f"Edge_{edge_name}_2D"] = lengths_2d[i]
                row[f"Edge_{edge_name}_3D"] = lengths_3d[i]
                row[f"Edge_{edge_name}_RelError"] = rel_error
                
                max_rel_error = max(max_rel_error, rel_error)
            
            row["MaxRelError"] = max_rel_error
            error_records.append(row)
        
        error_df = pd.DataFrame(error_records).sort_values("MaxRelError", ascending=False)
        error_df.to_csv(path + "edge_length_errors-side.csv", index=False)
        print("\nedge_length_errors-side.csv に辺の長さの誤差情報を出力しました。")
    else:
        print("連結情報がない、または有効な連結情報を持つ面がないため、誤差分析をスキップします。")
else:
    print("連結情報がない、または有効な連結情報を持つ面がないため、可視化と出力をスキップします。")
