"""Hexagonal pyramid (六角錐) generator for each hex face of Goldberg T=81.

For each hexagonal face:
  - Base  : the 6 face vertices radially scaled to base_r (default = sphere radius)
  - Apex  : base centroid shifted l_h mm inward (toward origin)
  - Bevel : single-segment vertex bevel with offset bevel_r mm (0 = no bevel)

Bevel geometry (vertex bevel, segments=1):
  Each original vertex is replaced by a bevel polygon.
  - Apex  (6-valent) → hexagonal cap            (pa[0..5])
  - Base vertex (3-valent) × 6 → triangle cap   (bl[i], ba[i], br[i])
  - Each side triangle → 6-gon panel             (4 tris)
  - Base hexagon → 12-gon                        (10 tris)
  Vertex count per pyramid: 7 (no bevel) or 24 (bevel > 0)
  Triangle count          : 10 (no bevel) or 44 (bevel > 0)

Output: OBJ with one named group per pyramid (g hex_NNNN).
Pentagon faces are skipped (12 total; non-polar pentagons become screw holes).

Usage:
    uv run python shell-cad/scripts/hex_pyramids.py
    uv run python shell-cad/scripts/hex_pyramids.py --l_h 3.0 --base_r 52
    uv run python shell-cad/scripts/hex_pyramids.py --l_h 5.0 --bevel 0.5
    uv run python shell-cad/scripts/hex_pyramids.py --l_h 5.0 --bevel 0.8 --base_r 52
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from goldberg import goldberg, report  # noqa: E402


# ---- helpers -----------------------------------------------------------------

def _normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


# ---- pyramid construction ----------------------------------------------------

def _pyramid_plain(B: np.ndarray, apex: np.ndarray) -> tuple[np.ndarray, list[list[int]]]:
    """No-bevel pyramid: 7 verts, 10 triangles.
    Winding: CCW from outside → outward normals → positive manifold volume.
    """
    V = np.vstack([B, apex])  # apex = index 6
    tris: list[list[int]] = []
    for i in range(6):
        tris.append([(i + 1) % 6, i, 6])          # 6 side triangles (outward winding)
    for i in range(1, 5):
        tris.append([0, i, i + 1])                 # base hexagon fan (outward winding)
    return V, tris


def _pyramid_beveled(B: np.ndarray, apex: np.ndarray, d: float) -> tuple[np.ndarray, list[list[int]]]:
    """Single-segment vertex bevel: 24 verts, 44 triangles.

    Vertex layout in returned V (24 total):
         0- 5 : pa[i] — on lateral edge apex→B[i], distance d from apex
         6-11 : ba[i] — on lateral edge B[i]→apex, distance d from B[i]
        12-17 : bl[i] — on base edge B[i]→B[i-1], distance d from B[i]
        18-23 : br[i] — on base edge B[i]→B[i+1], distance d from B[i]
    """
    A = apex

    pa = np.array([A + d * _normalize(B[i] - A)           for i in range(6)])
    ba = np.array([B[i] + d * _normalize(A - B[i])         for i in range(6)])
    bl = np.array([B[i] + d * _normalize(B[(i-1)%6] - B[i]) for i in range(6)])
    br = np.array([B[i] + d * _normalize(B[(i+1)%6] - B[i]) for i in range(6)])

    V = np.vstack([pa, ba, bl, br])  # (24, 3)

    # Index shortcuts (all mod-6 safe)
    def ip(i): return int(i) % 6
    def ib(i): return 6  + int(i) % 6
    def il(i): return 12 + int(i) % 6
    def ir(i): return 18 + int(i) % 6

    tris: list[list[int]] = []

    # Apex hexagonal cap — inward-facing (toward origin)
    for i in range(1, 5):
        tris.append([ip(0), ip(i+1), ip(i)])

    # Side panels: outward winding (reversed face order)
    for i in range(6):
        j = i + 1
        face = [ip(i), ip(j), ib(j), il(j), ir(i), ib(i)]
        for k in range(1, 5):
            tris.append([face[0], face[k], face[k+1]])

    # Base vertex bevel caps — outward winding
    for i in range(6):
        tris.append([il(i), ib(i), ir(i)])

    # Inset base 12-gon — outward winding (away from origin)
    base12 = []
    for i in range(6):
        base12.append(ir(i))
        base12.append(il(i+1))
    for i in range(1, 11):
        tris.append([base12[0], base12[i], base12[i+1]])

    return V, tris


def _pyramid(
    verts: np.ndarray,
    l_h: float,
    base_r: float | None = None,
    bevel: float = 0.0,
) -> tuple[np.ndarray, list[list[int]]]:
    """Build one hexagonal pyramid.

    Args:
        verts : (6, 3) base vertices from Goldberg mesh
        l_h   : inward depth of apex from base centroid (mm)
        base_r: if given, radially scale each base vertex to this radius first
        bevel : bevel offset in mm (0 = no bevel, plain pyramid)
    """
    if base_r is not None:
        norms = np.linalg.norm(verts, axis=1, keepdims=True)
        verts = verts / norms * base_r

    centroid = verts.mean(axis=0)
    apex = centroid - _normalize(centroid) * l_h

    if bevel > 0.0:
        return _pyramid_beveled(verts, apex, bevel)
    return _pyramid_plain(verts, apex)


def build_all_pyramids(
    V: np.ndarray,
    F: list[list[int]],
    l_h: float,
    base_r: float | None = None,
    bevel: float = 0.0,
) -> list[tuple[int, np.ndarray, list[list[int]]]]:
    """Return list of (original_face_idx, verts, tris) for every hex face."""
    result = []
    for fi, face in enumerate(F):
        if len(face) != 6:
            continue
        verts, tris = _pyramid(V[face], l_h, base_r, bevel)
        result.append((fi, verts, tris))
    return result


# ---- OBJ / STL output --------------------------------------------------------

def write_obj(path: Path, pyramids: list[tuple[int, np.ndarray, list[list[int]]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total_verts = sum(len(v) for _, v, _ in pyramids)
    total_tris  = sum(len(t) for _, _, t in pyramids)

    with path.open("w") as fh:
        fh.write(f"# Goldberg T=81 hexagonal pyramids — {len(pyramids)} faces\n")

        vert_offsets: list[int] = []
        global_idx = 0
        for fi, verts, _ in pyramids:
            vert_offsets.append(global_idx)
            fh.write(f"\n# hex_{fi:04d}\n")
            for v in verts:
                fh.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            global_idx += len(verts)

        for k, (fi, _, tris) in enumerate(pyramids):
            offset = vert_offsets[k] + 1  # OBJ is 1-based
            fh.write(f"\ng hex_{fi:04d}\n")
            for tri in tris:
                fh.write("f " + " ".join(str(i + offset) for i in tri) + "\n")

    print(f"  → wrote {path}  ({len(pyramids)} pyramids, "
          f"{total_verts} verts, {total_tris} triangles)")


def write_stl(path: Path, pyramids: list[tuple[int, np.ndarray, list[list[int]]]]) -> None:
    """Write ASCII STL. Normals are computed per-triangle via cross product."""
    path.parent.mkdir(parents=True, exist_ok=True)
    total_tris = sum(len(t) for _, _, t in pyramids)

    with path.open("w") as fh:
        fh.write(f"solid hex_pyramids\n")
        for _, verts, tris in pyramids:
            for tri in tris:
                a, b, c = verts[tri[0]], verts[tri[1]], verts[tri[2]]
                n = np.cross(b - a, c - a)
                nn = np.linalg.norm(n)
                n = n / nn if nn > 1e-12 else np.array([0.0, 0.0, 1.0])
                fh.write(
                    f"  facet normal {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n"
                    f"    outer loop\n"
                    f"      vertex {a[0]:.6f} {a[1]:.6f} {a[2]:.6f}\n"
                    f"      vertex {b[0]:.6f} {b[1]:.6f} {b[2]:.6f}\n"
                    f"      vertex {c[0]:.6f} {c[1]:.6f} {c[2]:.6f}\n"
                    f"    endloop\n"
                    f"  endfacet\n"
                )
        fh.write("endsolid hex_pyramids\n")

    print(f"  → wrote {path}  ({len(pyramids)} pyramids, {total_tris} triangles)")


def write_mesh(path: Path, pyramids: list[tuple[int, np.ndarray, list[list[int]]]]) -> None:
    """Dispatch to write_stl or write_obj based on file extension."""
    if path.suffix.lower() == ".stl":
        write_stl(path, pyramids)
    else:
        write_obj(path, pyramids)


# ---- stats -------------------------------------------------------------------

def stats(
    pyramids: list[tuple[int, np.ndarray, list[list[int]]]],
    l_h: float,
    base_r: float | None,
    bevel: float,
) -> None:
    verts_per = len(pyramids[0][1])
    tris_per  = len(pyramids[0][2])
    apex_radii = [np.linalg.norm(v[-1]) for _, v, _ in pyramids]   # last vert ≈ apex center
    base_radii = [np.linalg.norm(v[:6].mean(axis=0)) for _, v, _ in pyramids]
    print(f"  l_h            : {l_h:.3f} mm")
    print(f"  base_r         : {base_r if base_r is not None else '(same as sphere radius)'}")
    print(f"  bevel          : {bevel:.3f} mm  ({'vertex bevel, segments=1' if bevel > 0 else 'none'})")
    print(f"  Hex pyramids   : {len(pyramids)}")
    print(f"  Verts / tris   : {verts_per} / {tris_per} per pyramid")
    print(f"  Base centroid r: {np.mean(base_radii):.3f} ± {np.std(base_radii):.4f} mm")
    print(f"  Apex center r  : {np.mean(apex_radii):.3f} ± {np.std(apex_radii):.4f} mm")


# ---- CLI ---------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("-m", type=int, default=9,
                        help="Goldberg m (T=m^2). Default 9")
    parser.add_argument("-r", "--radius", type=float, default=50.0,
                        help="Sphere radius mm. Default 50")
    parser.add_argument("--l_h", type=float, default=5.0,
                        help="Inward depth of apex from base centroid mm. Default 5.0")
    parser.add_argument("--base_r", type=float, default=None,
                        help="Base vertex radius mm. Default: same as --radius.")
    parser.add_argument("--bevel", type=float, default=0.0,
                        help="Bevel offset mm. 0 = no bevel. "
                             "Max ~(shortest_edge / 2); for T=81 r=50 typically < 1.5 mm.")
    parser.add_argument("-o", "--output", default=None,
                        help="Output path. Extension determines format: .obj (default) or .stl")
    args = parser.parse_args()

    V, F = goldberg(args.m, args.radius)
    report(args.m, args.radius, V, F)

    pyramids = build_all_pyramids(V, F, args.l_h, args.base_r, args.bevel)
    stats(pyramids, args.l_h, args.base_r, args.bevel)

    suffix = f"_b{args.bevel:.1f}" if args.bevel > 0 else ""
    out = Path(args.output or f"shell-cad/output/hex_pyramids_l{args.l_h:.0f}{suffix}.obj")
    write_mesh(out, pyramids)


if __name__ == "__main__":
    main()
