"""place_fpc.py — 既存フットプリントを CSV 位置へ「移動 + 回転」(pcbnew)。

ライブラリから新規配置するのではなく、**すでにボード上にある** D(LED)/ C(0603)/
J1(POGO)を参照名で探して、CSV の座標へ移動し bridge 角度に回転する。ネット/接続は
そのまま保持される。

対応(チェーン order i → 参照):
  D{i+1} : WS2812 LED  → kicad_x/y に移動、次 LED 方向(bridge 角度)へ回転
  C{i+1} : 0603 cap    → 同座標・同角度(任意で裏面へ)
  J1     : POGO 6pin   → LED01(原点)へ移動

入力: output/fpc_unfold_c<N>.csv (order/kicad_x_mm/kicad_y_mm) + fpc_outline_c<N>.json

実行(KiCad 同梱 Python のみ): PCB エディタ → Tools → Scripting Console:
  exec(open('/Users/katano/work/FPC-isolation-sphere/fpc-kicad/scripts/place_fpc.py').read())
"""
import csv
import json
import math
import os

import pcbnew

# --- Config ------------------------------------------------------------------
REPO = "/Users/katano/work/FPC-isolation-sphere"
CID  = 0
CSV          = os.path.join(REPO, f"output/fpc_unfold_c{CID}.csv")
OUTLINE_JSON = os.path.join(REPO, f"output/fpc_outline_c{CID}.json")
TAB_JSON     = os.path.join(REPO, f"output/fpc_tab_c{CID}.json")

LED_PREFIX = "D"          # D{order+1}
CAP_PREFIX = "C"          # C{order+1}(= 同 index の LED のバイパス)
J1_REF     = "J1"

MOVE_LED = True
MOVE_CAP = True
MOVE_J1  = False          # ← 旧: LED01 へ移動。新: PLACE_TAB で 2 本指へ分配
PLACE_TAB = True          # fpc_tab_c<N>.json を読み、J1 の 6 pad を 2 本指へ再配置
DRAW_FINGER_EDGES = True  # 指の外形を Edge.Cuts に追加
CAP_TO_BACK     = True    # 0603 を裏面(B.Cu)に揃える(既に裏なら何もしない)
ROTATE_TO_CHAIN = True    # bridge 角度(次 LED 方向)に回転
FP_ANGLE_OFFSET = 0.0     # フットプリント基準向き補正(deg)
J1_OFFSET_MM    = (0.0, -4.0)   # J1 を LED01 から少しずらす(重なり回避)

DRAW_EDGE_CUTS        = True
CLEAR_EDGE_CUTS_FIRST = True
EDGE_WIDTH_MM         = 0.10
# ------------------------------------------------------------------------------


def mm(v):
    return pcbnew.FromMM(float(v))


def vec(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def load_leds(path):
    with open(path) as fh:
        rows = sorted(csv.DictReader(fh), key=lambda r: int(r["order"]))
    return [(int(r["order"]), float(r["kicad_x_mm"]), float(r["kicad_y_mm"])) for r in rows]


def chain_angle_deg(leds, i):
    if i < len(leds) - 1:
        ax, ay, bx, by = leds[i][1], leds[i][2], leds[i + 1][1], leds[i + 1][2]
    else:
        ax, ay, bx, by = leds[i - 1][1], leds[i - 1][2], leds[i][1], leds[i][2]
    return math.degrees(math.atan2(-(by - ay), bx - ax)) + FP_ANGLE_OFFSET


def move_fp(board, ref, x, y, ang, to_back=None):
    """既存フットプリントを移動+回転(無ければ False)。"""
    fp = board.FindFootprintByReference(ref)
    if fp is None:
        return False
    if to_back is not None and bool(fp.IsFlipped()) != bool(to_back):
        fp.Flip(fp.GetPosition(), False)          # 表裏を合わせる
    fp.SetPosition(vec(x, y))
    fp.SetOrientationDegrees(ang)
    return True


def clear_edge_cuts(board):
    for d in list(board.GetDrawings()):
        if d.GetLayer() == pcbnew.Edge_Cuts:
            board.Remove(d)


def draw_edge(board, rings):
    w = mm(EDGE_WIDTH_MM)
    nseg = 0
    for ring in rings:
        for pts in [ring["exterior"]] + ring.get("holes", []):
            for a, b in zip(pts, pts[1:] + pts[:1]):
                seg = pcbnew.PCB_SHAPE(board)
                seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
                seg.SetStart(vec(a[0], a[1])); seg.SetEnd(vec(b[0], b[1]))
                seg.SetLayer(pcbnew.Edge_Cuts); seg.SetWidth(w)
                board.Add(seg); nseg += 1
    return nseg


def place_tab(board):
    """Reposition J1's 6 pads onto the two fold-out fingers (by net) and draw
    the finger outlines on Edge.Cuts.  Nets stay intact (pads keep their net);
    we only move pad geometry.  fpc_tab_c<N>.json uses the same KiCad frame
    (origin=LED01, Y-down, mm) as the LED placements.

      START finger pads: 5V · GND · DIN     (chain begin / D1)
      END   finger pads: DOUT · GND · 5V    (chain end   / D80)
    Assembled on the inner_deck → 5V-GND-DIN-DOUT-GND-5V."""
    with open(TAB_JSON) as fh:
        tab = json.load(fh)
    # flat list of pad targets: (net_kicad, x, y)
    NET_ALIAS = {"5V": "+5V"}                       # json '5V' → board net '+5V'
    targets = []                                    # [(net, x, y, used)]
    for fg in tab["fingers"]:
        for p in fg["pads"]:
            targets.append([NET_ALIAS.get(p["net"], p["net"]),
                            float(p["x"]), float(p["y"]), False])

    fp = board.FindFootprintByReference(J1_REF)
    if fp is None:
        print(f"  ⚠ {J1_REF} not found — skip tab"); return 0
    nset = 0
    for pad in fp.Pads():
        net = pad.GetNetname()                      # '+5V' / 'GND' / 'DIN' / 'DOUT'
        for t in targets:                           # first unused target on this net
            if not t[3] and t[0] == net:
                pad.SetPosition(vec(t[1], t[2])); t[3] = True; nset += 1
                break
    leftover = [t for t in targets if not t[3]]
    if leftover:
        print(f"  ⚠ {len(leftover)} tab pad(s) unmatched to a J1 net: "
              f"{[t[0] for t in leftover]}")
    print(f"  tab: repositioned {nset}/6 J1 pads onto the two fingers")

    nseg = 0
    if DRAW_FINGER_EDGES:
        w = mm(EDGE_WIDTH_MM)
        for fg in tab["fingers"]:
            pts = [vec(x, y) for x, y in fg["outline"]]
            for a, b in zip(pts, pts[1:] + pts[:1]):
                seg = pcbnew.PCB_SHAPE(board)
                seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
                seg.SetStart(a); seg.SetEnd(b)
                seg.SetLayer(pcbnew.Edge_Cuts); seg.SetWidth(w)
                board.Add(seg); nseg += 1
        print(f"  tab: drew {nseg} finger Edge.Cuts segments")
    return nset


def run(board=None):
    board = board or pcbnew.GetBoard()
    leds = load_leds(CSV)
    print(f"=== move_fpc cassette {CID}: {len(leds)} positions ===")

    nled = ncap = miss = 0
    for i, (order, x, y) in enumerate(leds):
        ang = chain_angle_deg(leds, i) if ROTATE_TO_CHAIN else 0.0
        if MOVE_LED:
            ok = move_fp(board, f"{LED_PREFIX}{order + 1}", x, y, ang, to_back=False)
            nled += ok; miss += (not ok)
        if MOVE_CAP:
            ok = move_fp(board, f"{CAP_PREFIX}{order + 1}", x, y, ang,
                         to_back=CAP_TO_BACK)
            ncap += ok; miss += (not ok)

    nj1 = 0
    if MOVE_J1:
        ox, oy = leds[0][1] + J1_OFFSET_MM[0], leds[0][2] + J1_OFFSET_MM[1]
        nj1 = int(move_fp(board, J1_REF, ox, oy, 0.0))

    nseg = 0
    if DRAW_EDGE_CUTS:
        if CLEAR_EDGE_CUTS_FIRST:
            clear_edge_cuts(board)
        with open(OUTLINE_JSON) as fh:
            nseg = draw_edge(board, json.load(fh)["rings"])

    ntab = 0
    if PLACE_TAB:
        ntab = place_tab(board)            # draws finger Edge.Cuts after skeleton

    pcbnew.Refresh()
    print(f"  moved D={nled} C={ncap} J1={nj1} tab_pads={ntab}  (not found: {miss})")
    print(f"  Edge.Cuts segs={nseg} (+finger segs)")
    print("  ✓ 既存 footprint をネット保持のまま移動+回転(LED1=原点)")
    print("  次: DIN(D1→START指)/DOUT(D80→END指)/電源を配線 → DRC")


run()
