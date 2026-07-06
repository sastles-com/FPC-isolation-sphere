#!/usr/bin/env python3
"""
export_led_positions.py

Emit the full 800-LED 3-D placement of Isolation Sphere V2 as ONE CSV:

    FaceID,strip,strip_num,x,y,z

  FaceID    int  — Goldberg G(9,0) face index (inner sphere r=45 mm, φ90)
  strip     int  — data strip 0‥4 (= longitude slice).  ESP32 drives 5 in parallel.
  strip_num int  — position along the strip 0‥159.
                     0‥79   = NORTH cassette chain order (DIN→DOUT)
                     80‥159 = SOUTH cassette chain order (DIN→DOUT, terminal)
                   i.e. the real wired order: north → equator mother-ring cross → south.
  x,y,z     mm   — LED 3-D centre on the inner sphere (same frame as fpc_unfold_c*).

Physical model (CLAUDE.md §2.4): ONE common skeleton-FPC Gerber is fabbed ×10 and
all 10 cassettes are PROPER-rotation congruent.  So every cassette IS the same FPC,
just rotated — NOT independently re-solved.  We take the two reference cassettes
(c0 = north slice 0, c5 = south slice 0, whose hand-checked chain legends live in
output/fpc_unfold_c{0,5}.csv) and rotate each by Rz(72°·s) to materialise strips 0‥4.
Goldberg has exact 5-fold (72°) symmetry about Z, so a rotated face-centre lands
EXACTLY on another face centre → FaceID is recovered by nearest match (residual ~0).

Run:
    uv run python shell-cad/scripts/export_led_positions.py
    uv run python shell-cad/scripts/export_led_positions.py -o shared/led_positions.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from goldberg import goldberg

R_INNER = 45.0   # inner-sphere radius (φ90 mm) — matches generate_fpc_chain.py
M       = 9      # Goldberg G(9,0), T = 81
N_LON   = 5      # longitude slices → 5 strips, 72° apart
OUTDIR  = Path('output')

# Reference cassettes whose chain order is already solved/legend-checked.
REF = {'north': 0, 'south': 5}   # cassette_id of the slice-0 reference per hemisphere


def rot_z(p: np.ndarray, deg: float) -> np.ndarray:
    """Rotate point(s) about +Z by `deg` degrees."""
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    R = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    return p @ R.T


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('-o', '--output', default=str(OUTDIR / 'led_positions_3d.csv'),
                    help='Output CSV path (default: output/led_positions_3d.csv).')
    args = ap.parse_args()

    # 1 ── Goldberg face centres → FaceID lookup (exact within float eps) ──────
    V, F = goldberg(M, R_INNER)
    cents = np.array([V[face].mean(axis=0) for face in F])     # (n_faces, 3)

    def face_id_of(p: np.ndarray) -> tuple[int, float]:
        d = np.linalg.norm(cents - p, axis=1)
        i = int(np.argmin(d))
        return i, float(d[i])

    # 2 ── Load the two reference chains (order, face_idx, x3d, y3d, z3d) ──────
    def load_ref(cid: int) -> list[tuple[int, int, np.ndarray]]:
        path = OUTDIR / f'fpc_unfold_c{cid}.csv'
        if not path.exists():
            sys.exit(f"✗ missing reference {path} — run generate_fpc_chain.py -c {cid} first")
        out = []
        with path.open() as fh:
            for r in csv.DictReader(fh):
                out.append((int(r['order']), int(r['face_idx']),
                            np.array([float(r['x3d_mm']), float(r['y3d_mm']),
                                      float(r['z3d_mm'])])))
        out.sort(key=lambda t: t[0])
        return out

    ref_north = load_ref(REF['north'])
    ref_south = load_ref(REF['south'])
    if len(ref_north) != 80 or len(ref_south) != 80:
        sys.exit(f"✗ expected 80 LED/ref, got north={len(ref_north)} south={len(ref_south)}")

    # 3 ── Materialise 5 strips (north 0‥79 then south 80‥159), rotate Rz(72·s) ─
    rows = []
    max_res = 0.0
    for s in range(N_LON):
        deg = (360.0 / N_LON) * s          # 72°·s
        # north half: strip_num 0‥79
        for order, fidx0, p0 in ref_north:
            p = rot_z(p0, deg)
            fid, res = (fidx0, 0.0) if s == 0 else face_id_of(p)
            max_res = max(max_res, res)
            rows.append((fid, s, order, p))
        # south half: strip_num 80‥159
        for order, fidx0, p0 in ref_south:
            p = rot_z(p0, deg)
            fid, res = (fidx0, 0.0) if s == 0 else face_id_of(p)
            max_res = max(max_res, res)
            rows.append((fid, s, 80 + order, p))

    # 4 ── Sanity: 800 unique LEDs on 800 distinct faces ──────────────────────
    assert len(rows) == 800, len(rows)
    fids = {r[0] for r in rows}
    if len(fids) != 800:
        print(f"  ⚠ FaceID collisions: {800 - len(fids)} duplicate(s)")
    print(f"Goldberg G({M},0) r={R_INNER}mm  {len(F)} faces")
    print(f"  rows={len(rows)}  unique FaceIDs={len(fids)}  "
          f"max rotation→face residual={max_res:.2e} mm")

    # 5 ── Write CSV ──────────────────────────────────────────────────────────
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['FaceID', 'strip', 'strip_num', 'x', 'y', 'z'])
        for fid, s, sn, p in rows:
            wr.writerow([fid, s, sn,
                         round(float(p[0]), 4), round(float(p[1]), 4),
                         round(float(p[2]), 4)])
    print(f"  → {out_path}  (5 strips × 160 = 800 LEDs)")


if __name__ == '__main__':
    main()
