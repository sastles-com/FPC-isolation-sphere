"""Goldberg polyhedron G(m, 0) generator (Class I, achiral).

For T = m^2:
  - Faces:    10 m^2 + 2  (12 pentagons + (10 m^2 - 10) hexagons)
  - Vertices: 20 m^2
  - Edges:    30 m^2

Construction:
  1. Icosahedron with 5-fold axis on +Z (1 vertex at north pole, 1 at south pole,
     5 in upper ring at z = +1/sqrt(5), 5 in lower ring at z = -1/sqrt(5)).
  2. Geodesic subdivision of each triangular face into m^2 small triangles using
     barycentric coords. Project all vertices to unit sphere.
  3. Dual: face centroids become new vertices; for each geodesic vertex, gather
     adjacent face centroids in CCW order (by atan2 around outward normal) to
     form the Goldberg face. Pentagons appear at the 12 original icosahedron
     vertex positions (5-valent); hexagons everywhere else (6-valent).

Run:
    uv run python shell-cad/scripts/goldberg.py            # default m=9, T=81
    uv run python shell-cad/scripts/goldberg.py -m 3 -r 50 # G(3,0), T=9, r=50mm
"""

from __future__ import annotations

import argparse
import math
from collections import defaultdict
from pathlib import Path

import numpy as np


# ---- Icosahedron --------------------------------------------------------------

def icosahedron() -> tuple[np.ndarray, np.ndarray]:
    """Return (V (12,3), F (20,3)) for unit-sphere icosahedron, 5-fold axis on Z."""
    z = 1.0 / math.sqrt(5.0)
    r = 2.0 / math.sqrt(5.0)
    V = np.zeros((12, 3))
    V[0] = (0.0, 0.0, 1.0)
    V[11] = (0.0, 0.0, -1.0)
    for i in range(5):
        th_u = 2.0 * math.pi * i / 5.0
        V[1 + i] = (r * math.cos(th_u), r * math.sin(th_u), z)
        th_l = th_u + math.pi / 5.0
        V[6 + i] = (r * math.cos(th_l), r * math.sin(th_l), -z)

    F = np.array(
        [
            (0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 5), (0, 5, 1),
            (1, 2, 6), (2, 3, 7), (3, 4, 8), (4, 5, 9), (5, 1, 10),
            (2, 7, 6), (3, 8, 7), (4, 9, 8), (5, 10, 9), (1, 6, 10),
            (11, 7, 6), (11, 8, 7), (11, 9, 8), (11, 10, 9), (11, 6, 10),
        ],
        dtype=int,
    )

    return V, _fix_winding(V, F)


def _fix_winding(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    """Ensure each face is CCW from outside (cross-product points outward)."""
    out = F.copy()
    for i, (a, b, c) in enumerate(F):
        n = np.cross(V[b] - V[a], V[c] - V[a])
        centroid = (V[a] + V[b] + V[c]) / 3.0
        if float(n @ centroid) < 0.0:
            out[i] = (a, c, b)
    return out


# ---- Geodesic subdivide -------------------------------------------------------

def geodesic_subdivide(V: np.ndarray, F: np.ndarray, m: int) -> tuple[np.ndarray, np.ndarray]:
    """Subdivide each triangle into m^2 sub-triangles. Vertices projected to unit sphere."""
    vert_map: dict[tuple[float, float, float], int] = {}
    new_V: list[np.ndarray] = []

    def add(p: np.ndarray) -> int:
        key = tuple(np.round(p, 9))
        idx = vert_map.get(key)
        if idx is not None:
            return idx
        idx = len(new_V)
        new_V.append(p)
        vert_map[key] = key  # placeholder, replaced below
        vert_map[key] = idx
        return idx

    new_F: list[tuple[int, int, int]] = []

    for face in F:
        A, B, C = V[face[0]], V[face[1]], V[face[2]]
        grid: dict[tuple[int, int], int] = {}
        for i in range(m + 1):
            for j in range(m - i + 1):
                k = m - i - j
                p = (i * A + j * B + k * C) / m
                p = p / np.linalg.norm(p)
                grid[(i, j)] = add(p)

        for i in range(m):
            for j in range(m - i):
                # Up triangle
                new_F.append((grid[(i, j)], grid[(i + 1, j)], grid[(i, j + 1)]))
                # Down triangle (if it fits)
                if i + j + 2 <= m:
                    new_F.append((grid[(i + 1, j)], grid[(i + 1, j + 1)], grid[(i, j + 1)]))

    return np.asarray(new_V), np.asarray(new_F, dtype=int)


# ---- Dual ---------------------------------------------------------------------

def dual(V: np.ndarray, F: np.ndarray) -> tuple[np.ndarray, list[list[int]]]:
    """Return (new_vertices, new_faces) where new vertices are face centroids
    on the sphere and new faces are the cyclic ordering of adjacent centroids
    around each original vertex."""
    centroids = np.array(
        [(V[f[0]] + V[f[1]] + V[f[2]]) / 3.0 for f in F]
    )
    centroids = centroids / np.linalg.norm(centroids, axis=1, keepdims=True)

    vert_to_faces: dict[int, list[int]] = defaultdict(list)
    for fi, f in enumerate(F):
        for v in f:
            vert_to_faces[int(v)].append(fi)

    dual_faces: list[list[int]] = []
    for vi in range(len(V)):
        adj = vert_to_faces[vi]
        center = V[vi]
        n = center / np.linalg.norm(center)
        # Build right-handed frame (u, v, n) in the tangent plane
        ref = np.array([0.0, 0.0, 1.0]) if abs(n[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        u = np.cross(n, ref)
        u = u / np.linalg.norm(u)
        v = np.cross(n, u)

        def angle_of(fi: int) -> float:
            d = centroids[fi] - center
            return math.atan2(float(d @ v), float(d @ u))

        ordered = sorted(adj, key=angle_of)
        dual_faces.append(ordered)

    return centroids, dual_faces


# ---- Top-level ---------------------------------------------------------------

def goldberg(m: int, radius: float = 1.0) -> tuple[np.ndarray, list[list[int]]]:
    """Build Goldberg G(m, 0) inscribed in a sphere of given radius."""
    Vi, Fi = icosahedron()
    Vg, Fg = geodesic_subdivide(Vi, Fi, m)
    Vd, Fd = dual(Vg, Fg)
    return Vd * radius, Fd


# ---- OBJ output --------------------------------------------------------------

def write_obj(path: str | Path, V: np.ndarray, F: list[list[int]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        f.write(f"# Goldberg polyhedron — {len(V)} verts, {len(F)} faces\n")
        for v in V:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for face in F:
            f.write("f " + " ".join(str(i + 1) for i in face) + "\n")


# ---- Stats / verification ----------------------------------------------------

def report(m: int, radius: float, V: np.ndarray, F: list[list[int]]) -> None:
    n_pent = sum(1 for f in F if len(f) == 5)
    n_hex = sum(1 for f in F if len(f) == 6)
    others = [len(f) for f in F if len(f) not in (5, 6)]
    expect_V = 20 * m * m
    expect_F = 10 * m * m + 2
    expect_hex = 10 * m * m - 10

    print(f"Goldberg G({m}, 0)  T = {m * m}  radius = {radius} mm")
    print(f"  Vertices : {len(V):5d}   (expected {expect_V})")
    print(f"  Faces    : {len(F):5d}   (expected {expect_F})")
    print(f"  Pentagons: {n_pent:5d}   (expected 12)")
    print(f"  Hexagons : {n_hex:5d}   (expected {expect_hex})")
    if others:
        print(f"  ⚠ Other-sided faces: {others}")

    # Equator analysis
    z_centers = np.array([np.mean([V[i][2] for i in f]) for f in F])
    z_min_centers = np.min(np.abs(z_centers))
    n_straddle = sum(
        1 for f in F
        if min(V[i][2] for i in f) < 0.0 < max(V[i][2] for i in f)
    )
    print(f"  Min |face-center Z|: {z_min_centers:.4f} mm "
          f"({z_min_centers / radius * 100:.3f}% of radius)")
    print(f"  Faces straddling Z=0: {n_straddle} (these get trimmed by equator cut)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("-m", type=int, default=9, help="Goldberg parameter m (T = m^2). Default 9 for T=81")
    parser.add_argument("-r", "--radius", type=float, default=50.0, help="Outer radius in mm (default 50 = φ100mm)")
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output OBJ path. Default: shell-cad/output/goldberg_t<T>.obj"
    )
    args = parser.parse_args()

    m = args.m
    radius = args.radius
    out = args.output or f"shell-cad/output/goldberg_t{m * m}.obj"

    V, F = goldberg(m, radius)
    report(m, radius, V, F)
    write_obj(out, V, F)
    print(f"  → wrote {out}")


if __name__ == "__main__":
    main()
