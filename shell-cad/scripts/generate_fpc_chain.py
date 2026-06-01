#!/usr/bin/env python3
"""
generate_fpc_chain.py

WS2812 data-chain path (一筆書き) for one half-gore FPC cassette.
Inner sphere φ90 mm (r = 45 mm), Goldberg T=81 G(9,0).

Visits all 79 hex-face centroids exactly once.
Both DIN and DOUT are at the equator (motherboard-ring side).

Outputs:
  shell-cad/output/fpc_chain_c<N>.png  — flat equirectangular view
  shell-cad/output/fpc_chain_c<N>.csv  — chain sequence

Usage:
    uv run python shell-cad/scripts/generate_fpc_chain.py
    uv run python shell-cad/scripts/generate_fpc_chain.py --cassette 3 --show
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import deque, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from goldberg import goldberg

# ── Constants ──────────────────────────────────────────────────────────────
R_INNER = 45.0   # inner-sphere radius  (φ90 mm)
M       = 9      # Goldberg G(M,0), T = M² = 81
N_LON   = 5      # longitude slices


# ── Face helpers ───────────────────────────────────────────────────────────

def centroid(V: np.ndarray, face: list[int]) -> np.ndarray:
    return V[face].mean(axis=0)

def lon_rad(c: np.ndarray) -> float:
    """Longitude [0, 2π)."""
    return math.atan2(float(c[1]), float(c[0])) % (2 * math.pi)

def lat_rad(c: np.ndarray) -> float:
    """Latitude [-π/2, π/2]."""
    r = float(np.linalg.norm(c))
    return math.asin(max(-1.0, min(1.0, float(c[2]) / r)))

def cassette_of(c: np.ndarray) -> int:
    """
    Cassette index 0‥9.
      0‥4  north (z ≥ 0)  lon-slices centred at  0°, 72°, 144°, 216°, 288°
      5‥9  south (z < 0)  lon-slices centred at 36°, 108°, 180°, 252°, 324°
    """
    lon = lon_rad(c)
    w   = 2 * math.pi / N_LON
    if c[2] >= 0:
        si = int((lon + w / 2) / w) % N_LON
        return si
    else:
        si = int(lon / w) % N_LON
        return N_LON + si

def lon_centre_of(cid: int) -> float:
    si = cid % N_LON
    w  = 2 * math.pi / N_LON
    return si * w if cid < N_LON else si * w + w / 2

def is_pole_pent(c: np.ndarray) -> bool:
    return abs(float(c[2])) > 0.7 * float(np.linalg.norm(c))


# ── Face adjacency (shared edges) ─────────────────────────────────────────

def build_adj(F: list[list[int]], fi_set: set[int]) -> dict[int, list[int]]:
    edge: dict[tuple[int, int], list[int]] = {}
    for fi in fi_set:
        face = F[fi]
        n = len(face)
        for k in range(n):
            e = (min(face[k], face[(k + 1) % n]),
                 max(face[k], face[(k + 1) % n]))
            edge.setdefault(e, []).append(fi)
    adj: dict[int, list[int]] = {fi: [] for fi in fi_set}
    for e, flist in edge.items():
        if len(flist) == 2:
            a, b = flist
            if a in fi_set and b in fi_set:
                adj[a].append(b)
                adj[b].append(a)
    return adj


# ── Greedy Warnsdorff (no backtracking, O(n²)) ────────────────────────────

def warnsdorff(
    adj: dict[int, list[int]],
    start: int,
    end: int,
    nodes: set[int],
) -> list[int] | None:
    """
    Greedy Warnsdorff: always pick the neighbour with the fewest unvisited
    onward moves (no backtracking → completes in milliseconds).
    Returns [start, …, end] visiting all nodes, or None if stuck.
    """
    N    = len(nodes)
    path = [start]
    vis  = {start}

    while len(path) < N:
        cur  = path[-1]
        nbrs = [nb for nb in adj[cur] if nb not in vis]
        if not nbrs:
            return None  # dead end

        # On the penultimate step, reach `end` directly
        if len(path) == N - 1:
            return path + [end] if end in nbrs else None

        # Don't visit `end` prematurely (save it for last)
        main = [nb for nb in nbrs if nb != end] or nbrs

        def wdeg(v: int) -> int:
            return sum(1 for nb in adj[v] if nb not in vis)

        main.sort(key=wdeg)
        nxt = main[0]
        vis.add(nxt)
        path.append(nxt)

    return path if path[-1] == end else None


def find_chain(
    adj: dict[int, list[int]],
    equator_row: list[dict],
    hex_set: set[int],
    lon_cen: float,
) -> tuple[list[int], str]:
    """
    Try Warnsdorff with multiple DIN/DOUT candidate pairs from equator_row.
    Returns (path, description).
    """
    w = 2 * math.pi / N_LON
    left_lon  = lon_cen - w / 2
    right_lon = lon_cen + w / 2

    def lon_dist(a: float, b: float) -> float:
        return abs((a - b + math.pi) % (2 * math.pi) - math.pi)

    # Sort candidates by distance to left/right boundary
    left_cands  = sorted(equator_row, key=lambda f: lon_dist(f['lon'], left_lon))
    right_cands = sorted(equator_row, key=lambda f: lon_dist(f['lon'], right_lon))

    # Try top-3 × top-3 = up to 9 pairs
    for din_f in left_cands[:3]:
        for dout_f in right_cands[:3]:
            if din_f['fi'] == dout_f['fi']:
                continue
            path = warnsdorff(adj, din_f['fi'], dout_f['fi'], hex_set)
            if path:
                return path, f'Warnsdorff  DIN=fi{din_f["fi"]} DOUT=fi{dout_f["fi"]}'
            # also try reversed
            path = warnsdorff(adj, dout_f['fi'], din_f['fi'], hex_set)
            if path:
                return path[::-1], f'Warnsdorff(rev)  DIN=fi{din_f["fi"]} DOUT=fi{dout_f["fi"]}'

    return [], ''  # caller falls through to column-snake


# ── Column-snake fallback ──────────────────────────────────────────────────

def column_snake(
    hexs: list[dict],
    lon_cen: float,
) -> list[int]:
    """
    Column-snake: sort by Δlon into columns, snake up/down each column.
    Fast and deterministic.  Bridges may skip non-adjacent faces but stay short.
    With an odd column count both DIN and DOUT land at the equator.
    """
    R = R_INNER

    for f in hexs:
        dl       = (f['lon'] - lon_cen + math.pi) % (2 * math.pi) - math.pi
        f['_fx'] = R * dl
        f['_fy'] = R * abs(f['lat'])

    # Cluster by flat_x using gap detection (gap > 2 mm → new column)
    all_x = sorted(set(round(f['_fx'] * 2) / 2 for f in hexs))
    groups: list[list[float]] = [[all_x[0]]]
    for x in all_x[1:]:
        if x - groups[-1][-1] <= 2.0:
            groups[-1].append(x)
        else:
            groups.append([x])

    col_cen = [sum(g) / len(g) for g in groups]

    def col_of(fx: float) -> int:
        return min(range(len(col_cen)), key=lambda i: abs(col_cen[i] - fx))

    cols: dict[int, list[dict]] = defaultdict(list)
    for f in hexs:
        cols[col_of(f['_fx'])].append(f)
    for ci in cols:
        cols[ci].sort(key=lambda f: f['_fy'])

    path: list[int] = []
    for ci in sorted(cols.keys()):
        col = cols[ci]
        # Even col: equator→pole (ascending fy), odd: pole→equator (descending)
        path.extend(f['fi'] for f in (col if ci % 2 == 0 else reversed(col)))

    return path


# ── 2-D equirectangular projection ────────────────────────────────────────

def equirect(c: np.ndarray, lon_cen: float) -> tuple[float, float]:
    """
    fx = R × Δlon    (mm, positive = rightward / east)
    fy = R × |lat|   (mm, positive = poleward; equator = 0)
    """
    R  = float(np.linalg.norm(c))
    dl = (lon_rad(c) - lon_cen + math.pi) % (2 * math.pi) - math.pi
    return R * dl, R * abs(lat_rad(c))


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cassette', '-c', type=int, default=0,
                    help='Cassette ID 0‥9 (0‥4=north, 5‥9=south). Default 0.')
    ap.add_argument('--show', action='store_true',
                    help='Open interactive matplotlib window.')
    args = ap.parse_args()

    # 1 ── Generate Goldberg ───────────────────────────────────────────────
    V, F = goldberg(M, R_INNER)
    print(f"Goldberg G({M},0) T={M*M}  r={R_INNER} mm  "
          f"{len(V)} verts  {len(F)} faces")

    # 2 ── Assign all faces to cassettes ──────────────────────────────────
    face_info: list[dict] = []
    for fi, face in enumerate(F):
        c    = centroid(V, face)
        kind = 'pent' if len(face) == 5 else 'hex'
        cid  = cassette_of(c)
        face_info.append(dict(
            fi=fi, face=face, c=c,
            lon=lon_rad(c), lat=lat_rad(c),
            kind=kind, cid=cid,
            is_pole_pent=(kind == 'pent' and is_pole_pent(c)),
            is_screw=(kind == 'pent' and not is_pole_pent(c)),
        ))

    from collections import Counter
    cnt = Counter(f['cid'] for f in face_info)
    print(f"Faces per cassette: {dict(sorted(cnt.items()))}")

    # 3 ── Extract target cassette ─────────────────────────────────────────
    cid     = args.cassette
    hemi    = 'north' if cid < N_LON else 'south'
    si      = cid % N_LON
    lon_cen = lon_centre_of(cid)

    cas   = [f for f in face_info if f['cid'] == cid]
    hexs  = [f for f in cas if f['kind'] == 'hex']
    pents = [f for f in cas if f['kind'] == 'pent']

    print(f"\nCassette {cid}  ({hemi}, lon-slice {si}, "
          f"lon_cen={math.degrees(lon_cen):.1f}°)")
    print(f"  {len(cas)} faces: {len(hexs)} hex + {len(pents)} pent")
    for p in pents:
        tag = 'POLE' if p['is_pole_pent'] else 'SCREW'
        print(f"  [{tag}] fi={p['fi']:4d}  "
              f"lat={math.degrees(p['lat']):+.1f}°  lon={math.degrees(p['lon']):.1f}°")

    # 4 ── Adjacency (hex-only) ────────────────────────────────────────────
    hex_set = {f['fi'] for f in hexs}
    adj     = build_adj(F, hex_set)

    start_fi = next(iter(hex_set))
    q, seen_bfs = deque([start_fi]), {start_fi}
    while q:
        v = q.popleft()
        for nb in adj[v]:
            if nb not in seen_bfs:
                seen_bfs.add(nb); q.append(nb)
    if seen_bfs != hex_set:
        print(f"  ⚠ Adjacency: only {len(seen_bfs)}/{len(hex_set)} hexes reachable")

    # 5 ── Equator row (DIN / DOUT candidates) ────────────────────────────
    by_abs_lat  = sorted(hexs, key=lambda f: abs(f['lat']))
    equator_row = by_abs_lat[:12]

    # 6 ── Find Hamiltonian path ────────────────────────────────────────────
    print(f"\n  Searching Hamiltonian path through {len(hex_set)} hexes …")
    path, method = find_chain(adj, equator_row, hex_set, lon_cen)

    if not path:
        print("  Warnsdorff exhausted candidates — using column-snake fallback")
        path   = column_snake(hexs, lon_cen)
        method = 'column-snake (non-adjacent)'

    if len(path) != len(hex_set):
        print(f"  ✗ Path length {len(path)} ≠ {len(hex_set)}")
        sys.exit(1)

    print(f"  ✓ {method}")

    # Identify DIN / DOUT info
    fi_to    = {f['fi']: f for f in face_info}
    din_info = fi_to[path[0]]
    dout_info = fi_to[path[-1]]
    print(f"  DIN  fi={din_info['fi']:4d}  "
          f"lat={math.degrees(din_info['lat']):+.1f}°  lon={math.degrees(din_info['lon']):.1f}°")
    print(f"  DOUT fi={dout_info['fi']:4d}  "
          f"lat={math.degrees(dout_info['lat']):+.1f}°  lon={math.degrees(dout_info['lon']):.1f}°")

    # 7 ── Check for non-adjacent bridges ──────────────────────────────────
    non_adj = [(i, path[i], path[i+1])
               for i in range(len(path)-1)
               if path[i+1] not in adj[path[i]]]
    if non_adj:
        print(f"  ⚠  {len(non_adj)} non-adjacent bridge(s) in path "
              f"(first: step {non_adj[0][0]+1})")
    else:
        print("  ✓  All bridges face-adjacent")

    # 8 ── Flat projection ─────────────────────────────────────────────────
    flat = [equirect(fi_to[fi]['c'], lon_cen) for fi in path]

    # 9 ── Export CSV ──────────────────────────────────────────────────────
    outdir   = Path('shell-cad/output')
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / f'fpc_chain_c{cid}.csv'

    with csv_path.open('w', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow([
            'chain_seq', 'face_idx', 'cassette_id',
            'lon_deg', 'lat_deg', 'x_mm', 'y_mm', 'z_mm',
            'flat_x_mm', 'flat_y_mm', 'is_din', 'is_dout',
        ])
        for seq, fi in enumerate(path):
            info = fi_to[fi]
            c    = info['c']
            fx, fy = flat[seq]
            wr.writerow([
                seq, fi, cid,
                round(math.degrees(info['lon']), 3),
                round(math.degrees(info['lat']), 3),
                round(float(c[0]), 4), round(float(c[1]), 4), round(float(c[2]), 4),
                round(fx, 4), round(fy, 4),
                seq == 0, seq == len(path) - 1,
            ])

    print(f"\n  → {csv_path}")

    # 10 ── Visualise ──────────────────────────────────────────────────────
    try:
        import matplotlib.pyplot as plt
        from matplotlib.colors import Normalize
    except ImportError:
        print("  matplotlib not available — skipping plot (uv add matplotlib)")
        return

    fig, ax = plt.subplots(figsize=(9, 12))

    norm = Normalize(vmin=0, vmax=len(path) - 1)
    cmap = plt.cm.plasma

    # Bridge traces
    for i in range(len(path) - 1):
        x0, y0 = flat[i]
        x1, y1 = flat[i + 1]
        # red dashed for non-adjacent, grey for adjacent
        color = '#ff6666' if path[i+1] not in adj[path[i]] else '#cccccc'
        ls    = '--' if path[i+1] not in adj[path[i]] else '-'
        ax.plot([x0, x1], [y0, y1], color=color, lw=1.0, ls=ls, zorder=1)

    # Directional arrows every 8 steps
    for i in range(0, len(path) - 1, 8):
        x0, y0 = flat[i]
        x1, y1 = flat[i + 1]
        ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle='->', color='#888888',
                                   lw=1.2, mutation_scale=10),
                    zorder=2)

    # LED nodes coloured by sequence
    xs = [p[0] for p in flat]
    ys = [p[1] for p in flat]
    sc = ax.scatter(xs, ys, c=range(len(path)), cmap=cmap, norm=norm,
                    s=100, zorder=3, edgecolors='k', linewidths=0.3)
    plt.colorbar(sc, ax=ax, label='Chain sequence →', shrink=0.65)

    # Sequence labels every 5
    for i, (fx, fy) in enumerate(flat):
        if i == 0 or i == len(path) - 1 or i % 5 == 0:
            ax.text(fx, fy, str(i + 1), fontsize=5.5,
                    ha='center', va='center', color='white',
                    zorder=4, fontweight='bold')

    # DIN / DOUT
    ax.scatter(*flat[0],  s=280, c='#00ff88', marker='D', zorder=5,
               edgecolors='k', linewidths=0.8, label='DIN  (seq 1)')
    ax.scatter(*flat[-1], s=280, c='#ff4444', marker='D', zorder=5,
               edgecolors='k', linewidths=0.8, label=f'DOUT (seq {len(path)})')
    ax.annotate('DIN',  flat[0],  xytext=(-20, -2), textcoords='offset points',
                fontsize=9, color='#00cc66', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='#00cc66', lw=0.8))
    ax.annotate('DOUT', flat[-1], xytext=(6, -2),  textcoords='offset points',
                fontsize=9, color='#cc2222', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='#cc2222', lw=0.8))

    # Pent markers
    for p in [f for f in cas if f['is_screw']]:
        fx, fy = equirect(p['c'], lon_cen)
        ax.scatter(fx, fy, s=320, marker='p', c='#ff9900', zorder=5,
                   edgecolors='k', linewidths=0.8, label='non-polar pent (screw hole)')
        ax.annotate('screw\nhole', (fx, fy), xytext=(5, 2),
                    textcoords='offset points', fontsize=7, color='#cc6600')

    for p in [f for f in cas if f['is_pole_pent']]:
        fx, fy = equirect(p['c'], lon_cen)
        ax.scatter(fx, fy, s=220, marker='*', c='#00cfff', zorder=5,
                   edgecolors='k', linewidths=0.5, label='pole pent → polar PCB')
        ax.annotate('polar PCB', (fx, fy), xytext=(4, 2),
                    textcoords='offset points', fontsize=7, color='#0080aa')

    # Equator reference
    ax.axhline(0, color='#dd4444', lw=1.2, ls='--', alpha=0.7, zorder=0)

    # Cassette-width guides (±36°)
    half_w_mm = R_INNER * math.pi / N_LON
    ax.axvline(-half_w_mm, color='#888888', lw=0.7, ls=':', alpha=0.5)
    ax.axvline(+half_w_mm, color='#888888', lw=0.7, ls=':', alpha=0.5)

    ax.set_xlabel('Δlon × r  (mm)   ← left ─── right →', fontsize=10)
    ax.set_ylabel('|lat| × r  (mm)   equator (0) ─── pole ↑', fontsize=10)
    n_nonadj = len(non_adj)
    ax.set_title(
        f'Cassette {cid}  ({hemi}, lon-slice {si}, lon_cen={math.degrees(lon_cen):.0f}°)\n'
        f'LED chain · {len(path)} hexes · r={R_INNER} mm (inner φ90 mm)\n'
        f'{method}  |  non-adjacent bridges: {n_nonadj}',
        fontsize=9,
    )
    ax.set_aspect('equal')

    handles, labels = ax.get_legend_handles_labels()
    seen_l: set[str] = set()
    uh, ul = [], []
    for h, l in zip(handles, labels):
        if l not in seen_l:
            seen_l.add(l); uh.append(h); ul.append(l)
    ax.legend(uh, ul, loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.25)

    plt.tight_layout()
    png_path = outdir / f'fpc_chain_c{cid}.png'
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"  → {png_path}")

    if args.show:
        plt.show()
    plt.close()


if __name__ == '__main__':
    main()
