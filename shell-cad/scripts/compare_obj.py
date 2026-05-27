"""Compare two Goldberg OBJ outputs (numpy-script vs Blender addon).

Compares basic shape invariants without depending on vertex/face order:
  - Vertex radii distribution
  - Edge length distribution
  - Face area distribution (per-polygon)
  - Min |Z| of face centers (equator clearance)
  - 5-fold axis orientation hint

Usage:
    uv run python shell-cad/scripts/compare_obj.py \
        shell-cad/output/goldberg_t81.obj \
        shell-cad/output/goldberg_t81_addon.obj
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np


def load_obj(path: Path) -> tuple[np.ndarray, list[list[int]]]:
    verts: list[tuple[float, float, float]] = []
    faces: list[list[int]] = []
    with path.open() as f:
        for line in f:
            tok = line.split()
            if not tok:
                continue
            if tok[0] == "v":
                verts.append((float(tok[1]), float(tok[2]), float(tok[3])))
            elif tok[0] == "f":
                # OBJ is 1-indexed; ignore any "v/vt/vn" texture/normal refs
                idx = [int(t.split("/")[0]) - 1 for t in tok[1:]]
                faces.append(idx)
    return np.array(verts), faces


def edge_lengths(V: np.ndarray, F: list[list[int]]) -> np.ndarray:
    edges = set()
    for face in F:
        n = len(face)
        for i in range(n):
            a, b = face[i], face[(i + 1) % n]
            edges.add((min(a, b), max(a, b)))
    return np.array([
        np.linalg.norm(V[a] - V[b]) for a, b in edges
    ])


def polygon_area(V: np.ndarray, face: list[int]) -> float:
    """Planar polygon area in 3D (using the centroid fan)."""
    pts = V[face]
    c = pts.mean(axis=0)
    area = 0.0
    n = len(face)
    for i in range(n):
        a = pts[i] - c
        b = pts[(i + 1) % n] - c
        area += 0.5 * np.linalg.norm(np.cross(a, b))
    return area


def stats(name: str, arr: np.ndarray) -> str:
    return (f"  {name}: n={len(arr)}  "
            f"min={arr.min():.4f}  "
            f"max={arr.max():.4f}  "
            f"mean={arr.mean():.4f}  "
            f"std={arr.std():.6f}")


def face_z_min(V: np.ndarray, F: list[list[int]]) -> float:
    return float(min(abs(np.mean([V[i][2] for i in f])) for f in F))


def axis_hint(V: np.ndarray) -> str:
    """Look at vertex z-spread to guess if a vertex sits at z=±R (5-fold pole)."""
    zmax = V[:, 2].max()
    zmin = V[:, 2].min()
    r = max(abs(zmin), abs(zmax))
    # Find vertices very close to ±R along Z
    close_top = np.sum(np.abs(V[:, 2] - r) < 1e-3)
    close_bot = np.sum(np.abs(V[:, 2] + r) < 1e-3)
    return f"vertices within 1µm of ±R along Z: top={close_top}, bot={close_bot}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("a", type=Path)
    parser.add_argument("b", type=Path)
    args = parser.parse_args()

    for label, path in [("A", args.a), ("B", args.b)]:
        V, F = load_obj(path)
        radii = np.linalg.norm(V, axis=1)
        edges = edge_lengths(V, F)
        areas = np.array([polygon_area(V, f) for f in F])
        size_hist: dict[int, int] = {}
        for f in F:
            size_hist[len(f)] = size_hist.get(len(f), 0) + 1
        total_area = areas.sum()
        sphere_area = 4 * math.pi * radii.mean() ** 2
        coverage = total_area / sphere_area

        print(f"\n=== {label}: {path.name} ===")
        print(f"  verts={len(V)} faces={len(F)} sizes={size_hist}")
        print(stats("radius   ", radii))
        print(stats("edge_len ", edges))
        print(stats("face_area", areas))
        print(f"  total area: {total_area:.3f}  sphere area: {sphere_area:.3f}  "
              f"coverage: {coverage*100:.2f}%")
        print(f"  min |face-center Z|: {face_z_min(V, F):.4f}")
        print(f"  {axis_hint(V)}")


if __name__ == "__main__":
    main()
