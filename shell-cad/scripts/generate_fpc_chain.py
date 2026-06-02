#!/usr/bin/env python3
"""
generate_fpc_chain.py

WS2812 one-stroke data-chain + polyhedral *unfolding* (展開図) for one half-gore
FPC cassette.  Goldberg T=81 G(9,0), inner sphere φ90 mm (r = 45 mm).

Two-stage workflow (Warnsdorff draft → legend hand-edit):
  1. Draft : a robust Hamiltonian path (Warnsdorff order + backtracking) between
             a specified start (DIN) and end (DOUT).  Default endpoints:
               DIN  = equator-row hex nearest the cassette centre
               DOUT = a face-adjacent neighbour of DIN
             The order is written to a *legend* CSV.
  2. Legend: pass --legend <csv> to consume a hand-edited order instead of
             re-solving (Phase-2 Blender editor writes this file).

Unfolding (展開図):
  Because the cassette inner surface is a *polyhedron* (flat hex faces), it can
  be unfolded with ZERO in-plane distortion: place each face in the plane by
  hinging it flat about the edge it shares with the previous face in the chain
  (dihedral → 180°).  Island (LED) centres land exactly where they belong, and
  bridge lengths equal the true cross-edge surface distance.  Residual curvature
  lives at the (excluded) pentagons, so a hex-only half-gore unfolds nearly flat.
  The only risk is self-overlap of the net → reported + drawn.

Outputs (shell-cad/output/):
  fpc_legend_c<N>.csv   order,face_idx                       (the editable legend)
  fpc_unfold_c<N>.csv   per-LED 3D + unfolded 2D coords
  fpc_unfold_c<N>.png   unfolded net (hex polygons + chain + DIN/DOUT)

Usage:
    uv run python shell-cad/scripts/generate_fpc_chain.py --cassette 0
    uv run python shell-cad/scripts/generate_fpc_chain.py -c 0 --legend shell-cad/output/fpc_legend_c0.csv
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

sys.setrecursionlimit(100000)

# ── Constants ──────────────────────────────────────────────────────────────
R_INNER = 45.0   # inner-sphere radius  (φ90 mm)
M       = 9      # Goldberg G(M,0), T = M² = 81
N_LON   = 5      # longitude slices
OUTDIR  = Path('output')          # top-level output/ (gitignored)

# Skeleton FPC outline (unfolded): a circular island per hex + a band per
# chain bridge.  Tunable.
ISLAND_R = 2.25  # mm, LED island (round land) radius
BRIDGE_W = 3.0   # mm, connecting band width (along the one-stroke chain)


# ── Face helpers ───────────────────────────────────────────────────────────

def centroid(V: np.ndarray, face: list[int]) -> np.ndarray:
    return V[face].mean(axis=0)

def lon_rad(c: np.ndarray) -> float:
    return math.atan2(float(c[1]), float(c[0])) % (2 * math.pi)

def lat_rad(c: np.ndarray) -> float:
    r = float(np.linalg.norm(c))
    return math.asin(max(-1.0, min(1.0, float(c[2]) / r)))

def cassette_of(c: np.ndarray) -> int:
    lon = lon_rad(c)
    w   = 2 * math.pi / N_LON
    if c[2] >= 0:
        return int((lon + w / 2) / w) % N_LON
    return N_LON + int(lon / w) % N_LON

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
            e = (min(face[k], face[(k + 1) % n]), max(face[k], face[(k + 1) % n]))
            edge.setdefault(e, []).append(fi)
    adj: dict[int, list[int]] = {fi: [] for fi in fi_set}
    for flist in edge.values():
        if len(flist) == 2:
            a, b = flist
            if a in fi_set and b in fi_set:
                adj[a].append(b)
                adj[b].append(a)
    return adj

def shared_edge(F, fi, fj) -> tuple[int, int] | None:
    s = [v for v in F[fi] if v in set(F[fj])]
    return (s[0], s[1]) if len(s) >= 2 else None


# ── Robust chain solver: Warnsdorff order + backtracking ──────────────────

def solve_chain(adj, start, end, nodes, max_steps=3_000_000):
    """Hamiltonian path start→end visiting all `nodes`, or None.

    DFS with Warnsdorff ordering (fewest onward moves first) + backtracking →
    finds a path if one exists; the ordering keeps it fast (~80 nodes).
    """
    N = len(nodes)
    visited = {start}
    path = [start]
    steps = [0]

    def dfs(cur):
        if len(path) == N:
            return cur == end
        steps[0] += 1
        if steps[0] > max_steps:
            return False
        avail = [nb for nb in adj[cur] if nb not in visited]
        if len(path) == N - 1:
            cand = [end] if end in avail else []
        else:
            cand = [nb for nb in avail if nb != end]
            cand.sort(key=lambda v: sum(1 for nb in adj[v] if nb not in visited))
        for nb in cand:
            visited.add(nb); path.append(nb)
            if dfs(nb):
                return True
            visited.remove(nb); path.pop()
        return False

    return path[:] if dfs(start) else None


def pick_endpoints(hexs, adj, lon_cen, fi_to):
    """Yield (start, end) candidate pairs: start = equator hex nearest centre,
    end = a face-adjacent neighbour (equator-row preferred)."""
    def lon_dist(a, b):
        return abs((a - b + math.pi) % (2 * math.pi) - math.pi)

    by_lat   = sorted(hexs, key=lambda f: abs(f['lat']))
    eq_row   = by_lat[:12]
    eq_set   = {f['fi'] for f in eq_row}
    centre   = sorted(eq_row, key=lambda f: lon_dist(f['lon'], lon_cen))

    for din_f in centre[:4]:
        din = din_f['fi']
        nbrs = sorted(
            adj[din],
            key=lambda nb: (0 if nb in eq_set else 1, lon_dist(fi_to[nb]['lon'], lon_cen)),
        )
        for dout in nbrs:
            yield din, dout


# ── Polyhedral unfolding (zero-distortion net) ────────────────────────────

def intrinsic_2d(V, face):
    """Planarise a (near-planar) face onto its best-fit plane; return the
    vertices as complex 2D coords with the face centroid at the origin."""
    P = np.array([V[i] for i in face], float)
    Q = P - P.mean(axis=0)
    _, _, vt = np.linalg.svd(Q)
    e1, e2 = vt[0], vt[1]
    return [complex(float(q @ e1), float(q @ e2)) for q in Q]

def _map_edge(zs, qa, qb, A2, B2, reflect):
    """Rigid map sending intrinsic edge (qa,qb) onto placed edge (A2,B2)."""
    if reflect:
        k = (B2 - A2) / ((qb - qa).conjugate())
        return [A2 + k * ((z - qa).conjugate()) for z in zs]
    k = (B2 - A2) / (qb - qa)
    return [A2 + k * (z - qa) for z in zs]

def _side(A2, B2, P):
    return ((B2 - A2).conjugate() * (P - A2)).imag

def path_unfold(V, F, chain):
    """Unfold faces along `chain` by hinging each flat about the shared edge.

    Returns (centres2d, polys2d): per-sequence LED centre (complex) and the
    face polygon vertices (list of complex)."""
    centres, polys = [], []
    prev_v2d, prev_cen = {}, None

    for pos, fi in enumerate(chain):
        face = F[fi]
        q = intrinsic_2d(V, face)            # centroid at 0+0j
        if pos == 0:
            poly, cen = q, complex(0, 0)
        else:
            e = shared_edge(F, fi, chain[pos - 1])
            if e is None:                    # non-adjacent (shouldn't happen): offset
                off = prev_cen + complex(8, 0)
                poly = [z + off for z in q]; cen = off
            else:
                a, b = e
                A2, B2 = prev_v2d[a], prev_v2d[b]
                qa, qb = q[face.index(a)], q[face.index(b)]
                chosen = None
                for reflect in (False, True):
                    cand = _map_edge(q, qa, qb, A2, B2, reflect)
                    cc   = _map_edge([complex(0, 0)], qa, qb, A2, B2, reflect)[0]
                    if (_side(A2, B2, cc) > 0) != (_side(A2, B2, prev_cen) > 0):
                        chosen = (cand, cc); break
                if chosen is None:
                    cand = _map_edge(q, qa, qb, A2, B2, False)
                    cc   = _map_edge([complex(0, 0)], qa, qb, A2, B2, False)[0]
                    chosen = (cand, cc)
                poly, cen = chosen
        centres.append(cen); polys.append(poly)
        prev_v2d = {face[j]: poly[j] for j in range(len(face))}
        prev_cen = cen
    return centres, polys


# ── Skeleton FPC outline (islands + chain bands) ──────────────────────────

def _band_corners(p0, p1, w):
    """4 corners (complex) of a width-w band from p0 to p1."""
    d = p1 - p0
    L = abs(d)
    if L < 1e-9:
        return [p0, p0, p1, p1]
    n = (d / L) * 1j * (w / 2.0)     # perpendicular half-width
    return [p0 + n, p1 + n, p1 - n, p0 - n]

def write_skeleton_outline_svg(path, centres, island_r, bridge_w, margin=4.0,
                               json_path=None):
    """Union islands+bands into ONE silhouette. Writes:
      - SVG: stroked fill:none closed paths (preview / manual import)
      - JSON (optional): outline rings in the **KiCad frame** (origin=LED01,
        Y-down) so pcbnew can draw Edge.Cuts in the exact same frame as the
        LED placements (kicad_x/y). Returns False if shapely is unavailable."""
    try:
        from shapely.geometry import Point, Polygon
        from shapely.ops import unary_union
    except ImportError:
        return False

    geoms = [Point(z.real, z.imag).buffer(island_r, quad_segs=12) for z in centres]
    for i in range(len(centres) - 1):
        cs = _band_corners(centres[i], centres[i + 1], bridge_w)
        geoms.append(Polygon([(c.real, c.imag) for c in cs]))
    merged = unary_union(geoms).simplify(0.03, preserve_topology=True)

    polys = list(merged.geoms) if merged.geom_type == "MultiPolygon" else [merged]
    # Origin at LED01 (chain start / DIN). KiCad/SVG frame = Y-down → flip Y.
    ox, oy = centres[0].real, centres[0].imag
    xs = [z.real for z in centres]; ys = [z.imag for z in centres]
    minx, maxx = min(xs) - island_r - margin - ox, max(xs) + island_r + margin - ox
    miny = -(max(ys) + island_r + margin - oy)
    maxy = -(min(ys) - island_r - margin - oy)
    w, h = maxx - minx, maxy - miny

    def ring_kicad(ring):
        return [(round(px - ox, 4), round(-(py - oy), 4)) for px, py in ring.coords]

    rings = []           # list of {"exterior":[...], "holes":[[...],...]}
    d = []
    for pg in polys:
        ext = ring_kicad(pg.exterior)
        holes = [ring_kicad(h) for h in pg.interiors]
        rings.append({"exterior": ext, "holes": holes})
        d.append("M " + " L ".join(f"{x},{y}" for x, y in ext) + " Z")
        for hl in holes:
            d.append("M " + " L ".join(f"{x},{y}" for x, y in hl) + " Z")

    Path(path).write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w:.2f}mm" height="{h:.2f}mm" viewBox="{minx:.3f} {miny:.3f} {w:.3f} {h:.3f}">\n'
        f'  <!-- origin (0,0) = LED01 / DIN (chain start) -->\n'
        f'  <path d="{" ".join(d)}" fill="none" stroke="#000000" '
        f'stroke-width="0.15"/>\n</svg>\n')

    if json_path:
        import json
        Path(json_path).write_text(json.dumps(
            {"frame": "kicad (origin=LED01, Y-down, mm)", "rings": rings}, indent=0))
    return True


def write_skeleton_svg(path, centres, island_r, bridge_w, margin=4.0):
    """Write the skeleton silhouette (islands + chain bands) as an SVG in mm.
    Elements overlap; union in KiCad/Inkscape for a single outline."""
    xs = [z.real for z in centres]; ys = [z.imag for z in centres]
    x0, x1 = min(xs) - island_r - margin, max(xs) + island_r + margin
    y0, y1 = min(ys) - island_r - margin, max(ys) + island_r + margin
    w, h = x1 - x0, y1 - y0
    def X(v): return v - x0
    def Y(v): return y1 - v          # flip Y (SVG y-down) → mm y-up
    el = []
    for i in range(len(centres) - 1):           # bands first (under islands)
        cs = _band_corners(centres[i], centres[i + 1], bridge_w)
        pts = ' '.join(f'{X(c.real):.3f},{Y(c.imag):.3f}' for c in cs)
        el.append(f'<polygon points="{pts}" fill="#c08040"/>')
    for z in centres:
        el.append(f'<circle cx="{X(z.real):.3f}" cy="{Y(z.imag):.3f}" '
                  f'r="{island_r:.3f}" fill="#c08040"/>')
    body = "\n  ".join(el)
    Path(path).write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w:.2f}mm" height="{h:.2f}mm" viewBox="0 0 {w:.3f} {h:.3f}">\n'
        f'  {body}\n</svg>\n')


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cassette', '-c', type=int, default=0,
                    help='Cassette ID 0‥9 (0‥4=north, 5‥9=south). Default 0.')
    ap.add_argument('--legend', type=str, default=None,
                    help='Read an existing legend CSV (order,face_idx) instead of solving.')
    ap.add_argument('--show', action='store_true', help='Open matplotlib window.')
    args = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)

    # 1 ── Goldberg + cassette assignment ──────────────────────────────────
    V, F = goldberg(M, R_INNER)
    print(f"Goldberg G({M},0) T={M*M}  r={R_INNER} mm  {len(V)} verts  {len(F)} faces")

    face_info = []
    for fi, face in enumerate(F):
        c = centroid(V, face)
        face_info.append(dict(
            fi=fi, c=c, lon=lon_rad(c), lat=lat_rad(c),
            kind='pent' if len(face) == 5 else 'hex', cid=cassette_of(c),
            is_pole=(len(face) == 5 and is_pole_pent(c)),
            is_screw=(len(face) == 5 and not is_pole_pent(c)),
        ))
    fi_to = {f['fi']: f for f in face_info}

    cid     = args.cassette
    hemi    = 'north' if cid < N_LON else 'south'
    lon_cen = lon_centre_of(cid)
    cas     = [f for f in face_info if f['cid'] == cid]
    hexs    = [f for f in cas if f['kind'] == 'hex']
    hex_set = {f['fi'] for f in hexs}
    adj     = build_adj(F, hex_set)
    print(f"\nCassette {cid} ({hemi}, lon_cen={math.degrees(lon_cen):.1f}°): "
          f"{len(hexs)} hex")

    # 2 ── Chain order: load legend OR solve a draft ───────────────────────
    legend_path = OUTDIR / f'fpc_legend_c{cid}.csv'
    if args.legend:
        with open(args.legend) as fh:
            rows = list(csv.DictReader(fh))
        chain = [int(r['face_idx']) for r in rows]
        if set(chain) != hex_set:
            print(f"  ✗ legend covers {len(set(chain))} faces, cassette has {len(hex_set)}")
            sys.exit(1)
        method = f'legend ({Path(args.legend).name})'
        print(f"  Loaded legend: {len(chain)} faces  DIN=fi{chain[0]} DOUT=fi{chain[-1]}")
    else:
        chain, method = None, ''
        for din, dout in pick_endpoints(hexs, adj, lon_cen, fi_to):
            p = solve_chain(adj, din, dout, hex_set)
            if p:
                chain  = p
                method = f'Warnsdorff+backtrack DIN=fi{din} DOUT=fi{dout}(adj)'
                break
        if chain is None:
            print("  ✗ no Hamiltonian path found for centre-start/neighbour-end pairs")
            sys.exit(1)
        with legend_path.open('w', newline='') as fh:
            wr = csv.writer(fh); wr.writerow(['order', 'face_idx'])
            for i, fidx in enumerate(chain):
                wr.writerow([i, fidx])
        print(f"  ✓ {method}")
        print(f"  → {legend_path}  (edit this, then re-run with --legend)")

    # 3 ── Verify face-adjacency of the chain ──────────────────────────────
    non_adj = [i for i in range(len(chain) - 1)
               if chain[i + 1] not in adj[chain[i]]]
    print("  ✓ all bridges face-adjacent" if not non_adj
          else f"  ⚠ {len(non_adj)} non-adjacent step(s)")

    # 4 ── Unfold (zero-distortion polyhedral net) ─────────────────────────
    centres, polys = path_unfold(V, F, chain)

    # bridge length: flat (unfolded) vs 3D chord  (should match by construction)
    flat_d, d3d = [], []
    for i in range(len(chain) - 1):
        flat_d.append(abs(centres[i + 1] - centres[i]))
        d3d.append(float(np.linalg.norm(fi_to[chain[i+1]]['c'] - fi_to[chain[i]]['c'])))
    err = [abs(f - t) / t for f, t in zip(flat_d, d3d)]
    print(f"  bridge flat vs 3D-chord: mean err {np.mean(err)*100:.2f}%  "
          f"max {np.max(err)*100:.2f}%   (flat {np.mean(flat_d):.2f}mm)")

    # self-overlap heuristic: closest non-consecutive island centres
    med = float(np.median(flat_d))
    mind, worst = math.inf, None
    for i in range(len(centres)):
        for j in range(i + 2, len(centres)):
            d = abs(centres[i] - centres[j])
            if d < mind:
                mind, worst = d, (chain[i], chain[j])
    flag = '⚠ possible overlap' if mind < 0.55 * med else 'ok'
    print(f"  min non-adjacent island gap {mind:.2f}mm (median bridge {med:.2f}mm) → {flag}"
          + (f"  faces {worst}" if flag.startswith('⚠') else ''))

    # 5 ── Export unfolded CSV ─────────────────────────────────────────────
    csv_path = OUTDIR / f'fpc_unfold_c{cid}.csv'
    with csv_path.open('w', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['order', 'face_idx', 'cassette_id',
                     'x3d_mm', 'y3d_mm', 'z3d_mm',
                     'flat_x_mm', 'flat_y_mm',        # unfold frame (Y up, math)
                     'kicad_x_mm', 'kicad_y_mm',      # KiCad/SVG frame (Y down, origin=LED01)
                     'is_din', 'is_dout'])
        for seq, fidx in enumerate(chain):
            c = fi_to[fidx]['c']; z = centres[seq]
            # KiCad/SVG share origin=LED01 (centres[0]=0) and Y-down → flip Y.
            wr.writerow([seq, fidx, cid,
                         round(float(c[0]), 4), round(float(c[1]), 4), round(float(c[2]), 4),
                         round(z.real, 4), round(z.imag, 4),
                         round(z.real, 4), round(-z.imag, 4),
                         seq == 0, seq == len(chain) - 1])
    print(f"  → {csv_path}  (kicad_x/y match the outline SVG exactly)")

    # 6 ── Plot the unfolded net ───────────────────────────────────────────
    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Polygon as MplPoly
        from matplotlib.colors import Normalize
    except ImportError:
        print("  matplotlib not available — skipping plot")
        return

    fig, ax = plt.subplots(figsize=(11, 11))
    for poly in polys:
        ax.add_patch(MplPoly([(z.real, z.imag) for z in poly], closed=True,
                             fill=False, ec='#aaccff', lw=0.8, zorder=1))
    xs = [z.real for z in centres]; ys = [z.imag for z in centres]
    # Skeleton FPC silhouette: 3mm chain bands + island circles
    for i in range(len(centres) - 1):
        cs = _band_corners(centres[i], centres[i + 1], BRIDGE_W)
        ax.add_patch(MplPoly([(c.real, c.imag) for c in cs], closed=True,
                             fc='#e8c39a', ec='none', alpha=0.7, zorder=1.4))
    for z in centres:
        ax.add_patch(plt.Circle((z.real, z.imag), ISLAND_R,
                                fc='#d9a066', ec='#a06a30', lw=0.4,
                                alpha=0.85, zorder=1.5))
    ax.plot(xs, ys, '-', color='#cc4444', lw=1.0, zorder=2)
    sc = ax.scatter(xs, ys, c=range(len(centres)), cmap='plasma',
                    norm=Normalize(0, len(centres) - 1), s=80, zorder=3,
                    edgecolors='k', linewidths=0.3)
    plt.colorbar(sc, ax=ax, label='chain seq →', shrink=0.6)
    for i, z in enumerate(centres):
        if i == 0 or i == len(centres) - 1 or i % 5 == 0:
            ax.text(z.real, z.imag, str(i + 1), fontsize=6, ha='center', va='center',
                    color='white', zorder=4, fontweight='bold')
    ax.scatter(xs[0], ys[0], s=260, c='#00ff88', marker='D', zorder=5,
               edgecolors='k', label=f'DIN (fi{chain[0]})')
    ax.scatter(xs[-1], ys[-1], s=260, c='#ff4444', marker='D', zorder=5,
               edgecolors='k', label=f'DOUT (fi{chain[-1]})')

    ax.set_aspect('equal'); ax.autoscale_view()
    ax.set_title(f'Cassette {cid} - polyhedral unfold (tenkai-zu)\n'
                 f'{len(chain)} hex · {method}\n'
                 f'bridge err max {np.max(err)*100:.2f}% · gap {mind:.2f}mm ({flag})',
                 fontsize=9)
    ax.legend(loc='upper right', fontsize=8); ax.grid(True, alpha=0.25)
    plt.tight_layout()
    png = OUTDIR / f'fpc_unfold_c{cid}.png'
    plt.savefig(png, dpi=150, bbox_inches='tight')
    print(f"  → {png}")

    svg = OUTDIR / f'fpc_skeleton_c{cid}.svg'
    write_skeleton_svg(svg, centres, ISLAND_R, BRIDGE_W)
    print(f"  → {svg}  (filled preview, island r={ISLAND_R}mm, band w={BRIDGE_W}mm)")

    osvg = OUTDIR / f'fpc_skeleton_c{cid}_outline.svg'
    ojson = OUTDIR / f'fpc_outline_c{cid}.json'
    if write_skeleton_outline_svg(osvg, centres, ISLAND_R, BRIDGE_W, json_path=ojson):
        print(f"  → {osvg}  (outline preview, fill:none)")
        print(f"  → {ojson}  (outline rings in KiCad frame → place_fpc.py Edge.Cuts)")
    else:
        print("  (shapely not installed — outline skipped; uv add shapely)")
    if args.show:
        plt.show()
    plt.close()


if __name__ == '__main__':
    main()
