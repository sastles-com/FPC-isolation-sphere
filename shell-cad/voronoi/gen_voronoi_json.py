"""
Step 1: Voronoi計算 → JSON出力
通常のPython環境で実行（scipy必要）

出力JSON:
  r_outer   : 外半径 (mm)
  n_seeds   : セル数
  vertices  : Voronoi頂点座標（単位球面上）
  edges     : エッジ [(a,b), ...]
  regions   : セル面 [[v0,v1,...], ...]  ← Wireframe用に追加
"""
import numpy as np
from scipy.spatial import SphericalVoronoi, geometric_slerp
import json, math, sys, argparse

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("output", help="出力JSONパス")
    p.add_argument("--seeds",  type=int,   default=400)
    p.add_argument("--radius", type=float, default=30.0)
    return p.parse_args()

args = parse_args()
N_SEEDS = args.seeds
R_OUTER = args.radius

# Fibonacci Lattice
golden_ratio = (1 + math.sqrt(5)) / 2
idx   = np.arange(N_SEEDS)
theta = 2 * math.pi * idx / golden_ratio
phi   = np.arccos(1 - 2*(idx+0.5)/N_SEEDS)
pts   = np.column_stack([np.sin(phi)*np.cos(theta),
                          np.sin(phi)*np.sin(theta),
                          np.cos(phi)])

sv = SphericalVoronoi(pts, radius=1.0, center=np.zeros(3))
sv.sort_vertices_of_regions()

# エッジ収集
seen = set()
edges = []
for region in sv.regions:
    n = len(region)
    for i in range(n):
        a, b = region[i], region[(i+1)%n]
        key = (min(a,b), max(a,b))
        if key in seen: continue
        seen.add(key)
        v0, v1 = sv.vertices[a], sv.vertices[b]
        if np.linalg.norm(v0-v1) < 1e-3: continue
        edges.append([int(a), int(b)])

# セル面（regionは既にソート済みの頂点インデックス列）
regions = []
for region in sv.regions:
    if len(region) >= 3:
        regions.append([int(i) for i in region])

out = {
    "r_outer":  R_OUTER,
    "n_seeds":  N_SEEDS,
    "vertices": sv.vertices.tolist(),
    "edges":    edges,
    "regions":  regions,
}

with open(args.output, "w") as f:
    json.dump(out, f)

print(f"Voronoi頂点数: {len(sv.vertices)}")
print(f"エッジ数:       {len(edges)}")
print(f"セル面数:       {len(regions)}")
print(f"✅ JSON: {args.output}")
