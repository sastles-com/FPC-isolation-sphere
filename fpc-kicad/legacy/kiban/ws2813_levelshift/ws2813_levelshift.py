#!/usr/bin/env python3
"""
KiCad GUI内（Scripting Console専用）版
74HCT245 + WS2813 4ch レベルシフト基板配置テンプレート
"""
import pcbnew

board = pcbnew.GetBoard()
if board is None:
    raise RuntimeError("KiCad board not open. Open PCB Editor first.")

print(f"[INFO] Board name: {board.GetFileName() or '(unsaved board)'}")

# 単位変換
def mm(v): return int(v * 1_000_000)

# 枠線追加
outline = pcbnew.PCB_SHAPE(board)
outline.SetShape(pcbnew.SHAPE_T_RECT)
outline.SetStart(pcbnew.wxPoint(mm(0), mm(0)))
outline.SetEnd(pcbnew.wxPoint(mm(80), mm(50)))
outline.SetLayer(pcbnew.Edge_Cuts)
board.Add(outline)
print("[OK] Outline added")

# 配置座標表
placements = [
    ("IC1", (40, 25), 0),
    ("R1", (60, 15), 0),
    ("R2", (60, 20), 0),
    ("R3", (60, 25), 0),
    ("R4", (60, 30), 0),
    ("C1", (38, 22), 0),
    ("C2", (38, 27), 0),
    ("J1", (10, 25), 180),
    ("J2", (75, 15), 0),
    ("J3", (75, 20), 0),
    ("J4", (75, 25), 0),
    ("J5", (75, 30), 0),
]

for ref, (x, y), rot in placements:
    footprint = pcbnew.Footprint()
    footprint.SetReference(ref)
    footprint.SetPosition(pcbnew.wxPoint(mm(x), mm(y)))
    footprint.SetOrientationDegrees(rot)
    board.Add(footprint)
    print(f" - Added {ref}")

pcbnew.Refresh()
print("[DONE] All footprints placed. Save board manually (File → Save As).")
