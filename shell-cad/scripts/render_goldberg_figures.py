#!/usr/bin/env python3
"""
render_goldberg_figures.py

Publication figures for the blog article "ゴールドバーグ多面体をnumpyで生成する".
Pure matplotlib (no Blender). Renders straight from goldberg.py internals.

Outputs (output/):
  goldberg_t81.png       hero: G(9,0) T=81, hexes gray + 12 pentagons highlighted
  goldberg_pipeline.png  3 panels: icosahedron → geodesic dome → Goldberg dual
                         (illustrated at small m for clarity)

Run:
  uv run python shell-cad/scripts/render_goldberg_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

sys.path.insert(0, str(Path(__file__).parent))
from goldberg import icosahedron, geodesic_subdivide, dual, goldberg

OUTDIR = Path("output")
HEX_C  = "#d9d9d9"   # hexagon fill (light gray)
PENT_C = "#e8804d"   # pentagon fill (orange) — the 12 that carry no LED
TRI_C  = "#cfe3f2"   # triangle fill (light blue) for the subdivision panels
EDGE_C = "#37474f"   # edge line


def _set_view(ax, V, elev=22, azim=35):
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    r = float(np.max(np.linalg.norm(V, axis=1)))
    ax.set_xlim(-r, r); ax.set_ylim(-r, r); ax.set_zlim(-r, r)
    ax.set_axis_off()


def _draw(ax, V, F, by_kind=False, tri=False):
    """Add faces of (V,F) to a 3D axis as a Poly3DCollection."""
    polys, colors = [], []
    for f in F:
        polys.append([tuple(V[i]) for i in f])
        if tri:
            colors.append(TRI_C)
        elif by_kind:
            colors.append(PENT_C if len(f) == 5 else HEX_C)
        else:
            colors.append(HEX_C)
    pc = Poly3DCollection(polys, facecolors=colors, edgecolors=EDGE_C,
                          linewidths=0.3, alpha=1.0)
    ax.add_collection3d(pc)
    _set_view(ax, V)


def render_hero(m=9):
    V, F = goldberg(m, 1.0)
    n_pent = sum(1 for f in F if len(f) == 5)
    n_hex = sum(1 for f in F if len(f) == 6)
    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(111, projection="3d")
    _draw(ax, V, F, by_kind=True)
    ax.set_title(f"Goldberg G({m},0)   T = {m*m}\n"
                 f"{len(F)} faces = {n_hex} hexagons (gray) + {n_pent} pentagons (orange)",
                 fontsize=11)
    fig.tight_layout()
    out = OUTDIR / "goldberg_t81.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {out}")


def render_pipeline(m=3):
    """3 panels at small m so the subdivision is legible."""
    Vi, Fi = icosahedron()
    Vg, Fg = geodesic_subdivide(Vi, Fi, m)
    Vd, Fd = dual(Vg, Fg)

    fig = plt.figure(figsize=(13, 4.6))
    titles = [
        "1. Icosahedron\n(20 triangles)",
        f"2. Geodesic subdivision (m={m})\n(geodesic dome)",
        f"3. Dual -> Goldberg G({m},0) T={m*m}",
    ]
    data = [(Vi, Fi, dict(tri=True)),
            (Vg, Fg, dict(tri=True)),
            (Vd, Fd, dict(by_kind=True))]
    for k, (V, F, kw) in enumerate(data, 1):
        ax = fig.add_subplot(1, 3, k, projection="3d")
        _draw(ax, np.asarray(V), F, **kw)
        ax.set_title(titles[k - 1], fontsize=11)
    fig.suptitle("Goldberg construction pipeline (shown at m=3; real build is m=9)",
                 fontsize=12, y=1.02)
    fig.tight_layout()
    out = OUTDIR / "goldberg_pipeline.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {out}")


def render_cassettes(m=9):
    """Color the G(m,0) faces by cassette assignment (5 longitude × 2 hemi = 10),
    with the 2 polar pentagons left white — illustrates the 10-way split + the
    Goldberg-edge zigzag boundaries (no Boolean cut)."""
    import math
    V, F = goldberg(m, 1.0)
    cmap = plt.get_cmap("tab10")
    AZ_SHIFT, N_SL = 54.0, 5
    polys, colors = [], []
    for f in F:
        c = V[f].mean(axis=0)
        polar = abs(float(c[2])) > 0.9 * float(np.linalg.norm(c))
        polys.append([tuple(V[i]) for i in f])
        if polar and len(f) == 5:
            colors.append("#ffffff")
        else:
            az = (math.degrees(math.atan2(float(c[1]), float(c[0]))) % 360.0)
            sl = int(((az + AZ_SHIFT) % 360.0) // (360.0 / N_SL)) % N_SL
            hemi = 0 if c[2] >= 0.0 else 1
            colors.append(cmap((hemi * N_SL + sl) % 10))
    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(111, projection="3d")
    pc = Poly3DCollection(polys, facecolors=colors, edgecolors=EDGE_C,
                          linewidths=0.3, alpha=1.0)
    ax.add_collection3d(pc)
    _set_view(ax, V, elev=18, azim=35)
    ax.set_title("10 half-gore cassettes (5 longitude x 2 hemisphere)\n"
                 "+ 2 polar pentagons (white). Boundaries follow Goldberg edges.",
                 fontsize=11)
    fig.tight_layout()
    out = OUTDIR / "goldberg_cassettes.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {out}")


def fibonacci_sphere(n, r=1.0):
    """N points spread on a sphere via the golden-angle spiral."""
    i = np.arange(n)
    ga = np.pi * (3.0 - np.sqrt(5.0))          # golden angle ≈ 137.5°
    z = 1.0 - 2.0 * (i + 0.5) / n              # z evenly in (-1, 1)
    rad = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    th = ga * i
    return r * np.column_stack([np.cos(th) * rad, np.sin(th) * rad, z])


def render_distribution_compare(n_fib=800, m=9):
    """Side-by-side: Fibonacci sphere (points) vs Goldberg polyhedron (faces)."""
    P = fibonacci_sphere(n_fib, 1.0)
    Vg, Fg = goldberg(m, 1.0)

    fig = plt.figure(figsize=(12, 6))
    ax1 = fig.add_subplot(1, 2, 1, projection="3d")
    ax1.scatter(P[:, 0], P[:, 1], P[:, 2], s=10, c=PENT_C, depthshade=True)
    _set_view(ax1, P, elev=18, azim=35)
    ax1.set_title(f"Fibonacci sphere ({n_fib} points)\npoint-based / any N / spiral", fontsize=11)

    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    _draw(ax2, Vg, Fg, by_kind=True)
    ax2.set_title(f"Goldberg G({m},0) T={m*m} ({len(Fg)} faces)\nface-based / 5-fold sym / adjacency",
                  fontsize=11)
    fig.tight_layout()
    out = OUTDIR / "sphere_distribution_compare.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {out}")


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    render_hero(9)
    render_pipeline(3)
    render_cassettes(9)
    render_distribution_compare(800, 9)


if __name__ == "__main__":
    main()
