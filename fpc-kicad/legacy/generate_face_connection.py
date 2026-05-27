import pandas as pd
import numpy as np
import csv

# ファイルパス（適宜変更）
input_csv = "/Users/katano/isolation-sphere/side-all.csv"
output_csv = "/Users/katano/isolation-sphere/tri_vertex_connections-side.csv"

# 誤差許容
TOL = 1e-5

# 読み込み
df = pd.read_csv(input_csv)

# ヘッダーから頂点数を推定
num_vertex = (len(df.columns) - 5) // 3  # 例: V1X〜V6Z なら 6頂点

# 頂点座標を抽出（FaceIDごとにリストに）
def extract_vertices(row):
    verts = []
    for i in range(num_vertex):
        x = row[f"V{i+1}X"]
        y = row[f"V{i+1}Y"]
        z = row[f"V{i+1}Z"]
        verts.append(np.array([x, y, z]))
    return verts

face_data = []
for _, row in df.iterrows():
    face_id = int(row["FaceID"])
    verts = extract_vertices(row)
    face_data.append((face_id, verts))

# 出力リスト
connections = []

# 隣接するFaceID間で頂点比較
for i in range(len(face_data) - 1):
    face_id_a, verts_a = face_data[i]
    face_id_b, verts_b = face_data[i + 1]

    match_pairs = []

    for idx_a, va in enumerate(verts_a):
        for idx_b, vb in enumerate(verts_b):
            if np.linalg.norm(va - vb) < TOL:
                match_pairs.append((idx_a, idx_b))

    if len(match_pairs) != 2:
        print(f"⚠️ FaceID {face_id_a} ⇄ {face_id_b} で一致点が {len(match_pairs)} 個")
        continue

    for idx_a, idx_b in match_pairs:
        connections.append({
            "FaceID": face_id_a,
            "VertexIndex": idx_a,
            "ConnectedFaceID": face_id_b,
            "ConnectedVertexIndex": idx_b,
            "Reverse": True
        })

# CSV出力
with open(output_csv, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["FaceID", "VertexIndex", "ConnectedFaceID", "ConnectedVertexIndex", "Reverse"])
    writer.writeheader()
    writer.writerows(connections)

print(f"✅ 書き出し完了: {output_csv}")
