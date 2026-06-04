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
# 2 本の 3 ピンヘッダ(ポゴピン用): J1=START リード(5V-GND-DIN) / J2=END リード(DOUT-GND-5V)
TAB_REFS   = {"start": "J1", "end": "J2"}
HEADER_ANCHOR_PIN = "2"   # ★ 3 ピンの真ん中(pin2)を配置原点にする

MOVE_LED = True
MOVE_CAP = True
PLACE_TAB = True          # fpc_tab_c<N>.json を読み、J1/J2 を pin2 基準で配置
HEADER_ANGLE_OFFSET = 0.0 # ヘッダ向き補正(deg、必要なら 180 等)
CAP_TO_BACK     = True    # 0603 を裏面(B.Cu)に揃える(既に裏なら何もしない)
ROTATE_TO_CHAIN = True    # bridge 角度(次 LED 方向)に回転
FP_ANGLE_OFFSET = 0.0     # フットプリント基準向き補正(deg)

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
    """Place the two 3-pin pogo headers J1 (START lead) and J2 (END lead) using
    pin 2 (the MIDDLE pin) as the anchor → pin2 lands on the lead's middle pad,
    the row oriented along pin1→pin3 (= pads[0]→pads[2]).

      J1 START pads: 5V · GND · DIN     (chain begin / D1)
      J2 END   pads: DOUT · GND · 5V    (chain end   / D80)
    The lead outlines (strip + square stiffener head) come from the unioned
    Edge.Cuts (fpc_outline_c<N>.json) — drawn in run(), not here."""
    with open(TAB_JSON) as fh:
        tab = json.load(fh)
    NET_ALIAS = {"5V": "+5V"}                       # json '5V' → board net '+5V'
    nset = 0
    for fg in tab["fingers"]:
        ref = TAB_REFS.get(fg["role"])
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            print(f"  ⚠ {ref} ({fg['role']}) not found — skip"); continue
        pads = fg["pads"]                           # [pin1, pin2, pin3]
        p0, p1, p2 = pads[0], pads[1], pads[2]
        # orientation: pin1→pin3 row direction (KiCad Y-down → math via -dy), the
        # 1xNN header's native pin axis is +Y → subtract 90°.
        ang = (math.degrees(math.atan2(-(p2["y"] - p0["y"]), p2["x"] - p0["x"]))
               - 90.0 + HEADER_ANGLE_OFFSET)
        fp.SetOrientationDegrees(ang)
        anchor = next((pd for pd in fp.Pads()
                       if pd.GetNumber() == HEADER_ANCHOR_PIN), None)
        if anchor is None:
            print(f"  ⚠ {ref} has no pin {HEADER_ANCHOR_PIN}"); continue
        off = anchor.GetPosition() - fp.GetPosition()    # pad2 offset (post-rotate)
        fp.SetPosition(vec(p1["x"], p1["y"]) - off)       # pin2 → middle pad
        # assign nets pin n → pads[n-1] (if that net exists on the board)
        for pd in fp.Pads():
            try:
                idx = int(pd.GetNumber()) - 1
            except ValueError:
                continue
            if 0 <= idx < 3:
                net = board.FindNet(NET_ALIAS.get(pads[idx]["net"], pads[idx]["net"]))
                if net is not None:
                    pd.SetNet(net)
        nset += 1
        print(f"  {ref}: pin2→({p1['x']},{p1['y']}) ang={ang:.1f}°  "
              f"pins {[p['net'] for p in pads]}")
    print(f"  tab: placed {nset}/2 pogo headers (J1/J2, anchored on pin{HEADER_ANCHOR_PIN})")
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

    nseg = 0
    if DRAW_EDGE_CUTS:
        if CLEAR_EDGE_CUTS_FIRST:
            clear_edge_cuts(board)
        with open(OUTLINE_JSON) as fh:     # includes the leads (strip + square head)
            nseg = draw_edge(board, json.load(fh)["rings"])

    ntab = 0
    if PLACE_TAB:
        ntab = place_tab(board)            # J1/J2 pogo headers, pin2-anchored

    pcbnew.Refresh()
    print(f"  moved D={nled} C={ncap} headers={ntab}  (not found: {miss})")
    print(f"  Edge.Cuts segs={nseg} (skeleton + 2 leads)")
    print("  ✓ 既存 footprint をネット保持のまま移動+回転(LED1=原点)")
    print("  次: DIN/DOUT/電源を J1/J2 へ配線 → DRC")


run()
