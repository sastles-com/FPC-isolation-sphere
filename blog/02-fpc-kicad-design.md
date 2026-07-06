---
title: "骨組みFPC: 800個のLEDを1種類のGerberで配線する"
emoji: "🔌"
type: "tech"
topics: ["KiCad", "FPC", "プリント基板", "Python", "電子工作"]
published: false
---

> **アウトライン（詳細）** — ハード2本目。外殻の中に収まる柔軟基板(FPC)の設計。
> 元ネタ: `docs/02-fpc-kicad.md` / `shell-cad/scripts/generate_fpc_chain.py` / `fpc-kicad/scripts/place_fpc.py`

## 1. 課題: 球面に800個のLEDをどう配線するか
- ベタな三角ゴアFPCだと球面追従の反発力が大きい/熱がこもる
- 解: **「島(island)を細い帯(bridge)で数珠繋ぎ」した骨組み(skeleton)形状**
- メリット: 球面追従、低反発、放熱、肉抜き部から外殻と直接シール
- 実装面: 表面=WS2812C-2020、裏面=0603バイパスコンデンサ

## 2. 一筆書き（Hamiltonian path）でデータチェーンを通す
- WS2812はDIN→DOUTの一方向チェーン → 80 hexを一筆書きで巡る必要
- アルゴリズム: Warnsdorff順 + バックトラッキング + 連結性プルーニング
- 両端(DIN/DOUT)を赤道接触hexに固定する制約（後の赤道接続のため）
- コード断片: `solve_chain()` の考え方（degree-2ノードも高速に解ける理由）

## 3. 「Gerber 1種を10枚」を成立させる対称性
- 10カセットは全てproper回転で合同（北=Z軸72°、北↔南=赤道軸180°）
- 端子配置を左右対称(回文)に → 180°回転時のDIN/DOUT入替をマザーリング側クロスで吸収
- `generate_fpc_chain.py -c 0` で基準1枚を生成、残りは回転コピー

## 4. 5ストリップ構成（160 LED × 5）
- 北カセット(80) →赤道マザーリングでクロス→ 南カセット(80) = 1ストリップ160 LED
- ESP32は5並列出力。`N_DOUT→S_DIN` クロスの意味
- §記事03(赤道接続)・記事05(ファーム5並列駆動)への伏線

## 5. 展開図(flat pattern)をどう作るか —— MDS平面化
- ハーフゴアは非可展面（ガウス曲率を内包）→ 単純な蝶番展開は端で破綻
- 古典的MDS(多次元尺度構成法)で歪みを全体に分散（平均~0.5mm/最大~3.6mm）
- 外向き接平面ビューに剛体整列して鏡像反転を防ぐ（LEDが正しい面に来る）
- コード断片: `mds_flatten()` の固有値分解 + Procrustes整列

## 6. inner_deckタブ = 撓みリード（赤道への引き出し）
- DIN/DOUT端から各1本の柔軟リード(~15mm) + 3パッドヘッド
- 組立時に赤道で~90°折り、6パッド `5V-GND-DIN-DOUT-GND-5V` に集約
- 矩形ヘッド=スティフナー(補強)ゾーン

## 7. LED座標CSVをエクスポート（次の記事への橋渡し）
- `shared/led_positions.csv` = `FaceID, strip, strip_num, x, y, z`（800行=5×160）
- Rz(72°·s)回転コピーで全800個をmaterialize、Goldbergの72°対称で面IDも厳密一致
- このCSVがファーム側 `core/data/led_layout.csv` になる（記事05へ）
