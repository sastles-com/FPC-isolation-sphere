#!/usr/bin/env python3
"""mother_ring_holes.py — マザーリングの固定穴(Φ3 ×10)とゾーン中心(×5)の座標を CSV 出力。

定義(2026-06-04):
  - ポゴゾーン中心: 経度 0/72/144/216/288°(5 ゾーン)
  - 固定穴(Φ3): 各ゾーン中心から ±20° → 10 穴、半径 R_HOLE = 41.25 (Φ82.5)
  - ゾーン中心: 半径方向に 0.5mm 短縮 → R_ZONE = 40.75
  - いずれも z=0(マザーリング平面)

出力: output/mother_ring_points.csv
  kind(fix_hole/zone), zone, label, angle_deg, radius_mm, x_mm, y_mm, z_mm

Usage: uv run python shell-cad/scripts/mother_ring_holes.py
"""
import csv
import math
from pathlib import Path

# --- Parameters --------------------------------------------------------------
ZONE_ANGLES = [0.0, 72.0, 144.0, 216.0, 288.0]   # deg, ポゴゾーン中心(経度)
FIX_OFFSET  = 20.0       # deg, 固定穴は中心 ±20°
R_HOLE      = 41.25      # mm, 固定穴 PCD (Φ82.5)
R_ZONE      = 41.25 - 0.5  # mm, ゾーン中心は 0.5mm 短縮 = 40.75
Z           = 0.0
OUT = Path("output/mother_ring_points.csv")
# ------------------------------------------------------------------------------


def polar(r, deg):
    a = math.radians(deg)
    return round(r * math.cos(a), 4), round(r * math.sin(a), 4)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    # 5 zone centres (R shortened 0.5mm)
    for zi, za in enumerate(ZONE_ANGLES):
        x, y = polar(R_ZONE, za)
        rows.append(["zone", zi, f"zone{zi}", round(za, 3), R_ZONE, x, y, Z])
    # 10 fixing holes (±20° per zone, R_HOLE)
    for zi, za in enumerate(ZONE_ANGLES):
        for s, tag in ((-1, "m"), (+1, "p")):
            ang = (za + s * FIX_OFFSET) % 360.0
            x, y = polar(R_HOLE, ang)
            rows.append(["fix_hole", zi, f"hole{zi}{tag}", round(ang, 3),
                         R_HOLE, x, y, Z])

    with OUT.open("w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["kind", "zone", "label", "angle_deg", "radius_mm",
                     "x_mm", "y_mm", "z_mm"])
        wr.writerows(rows)

    print(f"→ {OUT}")
    print(f"  zones: {len(ZONE_ANGLES)} @ R={R_ZONE}  /  fix_holes: "
          f"{len(ZONE_ANGLES) * 2} @ R={R_HOLE} (±{FIX_OFFSET}°)")
    for r in rows:
        print(f"  {r[0]:8s} {r[2]:8s} ang={r[3]:6.1f}  ({r[5]:8.3f}, {r[6]:8.3f}, {r[7]})")


if __name__ == "__main__":
    main()
