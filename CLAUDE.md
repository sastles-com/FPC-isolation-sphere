# Isolation Sphere V2 — Project Guide for Claude

このファイルは Claude Code が本プロジェクトで作業する際に参照する前提知識です。
This file is the working context Claude should load before assisting on this project.

- 一次資料 / Primary source: [`docs/10pieces-isolation-sphere-concept.md`](docs/10pieces-isolation-sphere-concept.md)
- ここに書かれているのは **概念ドキュメントの試行錯誤の末に採用が確定した仕様だけ** です。未確定の項目は `<open_questions>` セクションに分けています。
- Only the **finalised decisions** that emerged from the iterative discussion in the concept doc are captured here. Anything still under debate lives in `<open_questions>`.

### このファイルの守備範囲 / Scope of this file

<file_scope>
- **CLAUDE.md (このファイル)** = 全作業で必ず読むべき "前提知識" のみ。
  全体トポロジー、確定仕様サマリ、ハード規則 (NEVER/ALWAYS)、Claude との作業規約。
- **`docs/*.md`** = 個別の小プロジェクト (3D CAD, FPC, Firmware など) ごとの詳細。
  作業中に膨らみがちな手順・寸法・データフォーマット・スクリプト仕様などはこちらへ書く。
- **判断基準 (どっちに書くか)**:
  - 「全カセット/全小プロジェクトに共通する確定事項」「禁則」→ **CLAUDE.md**
  - 「ある小プロジェクトに閉じた手順・パラメータ・データ仕様」→ **`docs/<name>.md`**
- 個別ドキュメントを新規に作るときは **§8 Sub-Project Docs** の規約に従うこと。
- **CLAUDE.md は索引役** として、`docs/` 配下の小プロジェクトドキュメントを §8 のテーブルから 1 行ずつリンクする。
</file_scope>

---

## 1. Project Overview / プロジェクト概要

<project>
- **What / なに**: 直径 100 mm の球体 LED ディスプレイ「Isolation Sphere V2」。 **800 個**の WS2812-2020 を球面に並べた "デジタル地球儀" 風ピクセルディスプレイ。
- **A 100 mm spherical LED display ("Isolation Sphere V2") with 800 WS2812-2020 pixels covering a Goldberg polyhedron shell.**
- **Why this revision / 今回の改修動機**: 前作はスパイラル配線+接着剤固定でメンテ不可だった。LED 1 個の故障で全損する設計を、**カセット交換式 + 接着剤ゼロ** に作り直す。
- **The previous build was glued together and a single dead LED bricked the whole sphere. V2 makes every section a hot-swappable cassette with zero adhesive bonds.**
- **Repo state / 現状**: 概念設計フェーズ。コードはまだ無く、`docs/` の議論ログのみ。今後 Blender Python と KiCad で実装に入る。
</project>

---

## 2. Confirmed Hardware Topology / 確定したハードウェア構成

### 2.1 Sphere geometry / 球体ジオメトリ

<geometry>
- 多面体: **ゴールドバーグ多面体 T=81** (Goldberg polyhedron, class T=81)
- 外径 φ100 mm / 内径 φ90 mm / 殻厚 **5 mm** (radial)
- 総ピクセル数: **800** (= 全 hex。LED は **赤道 Z=0 上には配置しない**。赤道を挟んで北/南に逃がす千鳥配置)
- LEDs are deliberately offset from the equator so the equator slice is reserved for pogo-pin contacts only.
</geometry>

### 2.2 Cassette structure / カセット分割

<cassettes>
- 経度方向 **5 分割** × 南北半球で2分割 = **10 個のハーフゴア・カセット**
- 各カセット = 3D プリント外殻 + 骨組み FPC (**80 LED**)
- 外殻の色: 黒 (反射抑制のためのブラックマスク効果)
- **Each cassette is one half-gore: 1 of 5 longitudinal slices × north/south hemisphere = 10 cassettes total.**
</cassettes>

### 2.3 LED window — "ラッパ穴 (flared aperture)" / 円錐窓構造

<led_window>
- 外殻には **円錐状にテーパーした穴 (ラッパ穴)** が空いており、LED は穴の奥底に位置する。
- 視野角は約 **120°** を確保。穴の周囲が遮光マスクとなり高コントラスト化。
- 外殻厚 5 mm のうち約 1.5〜2 mm を斜面に充てる。
- LED 自身は外殻外面に露出させない (ポゴピン圧によって LED がもげないようにするためでもある)。
- **LEDs sit at the bottom of cone-shaped wells in the shell, giving a ~120° beam and acting as built-in black mask. The shell thickness shields the LED package from pogo-pin compression.**
</led_window>

### 2.4 FPC design — "骨組み (skeleton)" 形状 (全 hex 共通 FPC、極専用 PCB 廃止)

<fpc>
- 形状: **LED ごとの円形ランド (island) を細い帯 (bridge) で数珠繋ぎ** にしたスケルトン形状 (≠ ベタ三角ゴア)。
- **実装面**: **表面に WS2812C-2020 (LED)、裏面に 0603 チップコンデンサ (各 LED のバイパス)**。
  - 裏面に 0603 が出っ張るため、`back_gore` (裏当て) は **0603 を逃がす凹み/開口** が必要 (詳細 [`docs/01-shell-cad.md` §カセット裏面構造](docs/01-shell-cad.md#cassette-back-side-structures--カセット裏面構造-inner_deck--back_gore--ring_claw))。
- メリット: 3D 球面に追従しやすく反発力が小さい / 熱が中空内部へ抜ける / 肉抜き部分から外殻と直接シールできる。
- **Gerber は 2 種** = **北 (cassette 0) + 南 (cassette 5)**、各 5 枚発注 (計 10)。北↔南は鏡像 (enantiomorph) で proper 回転では一致しないため 1 種では不可 (2026-06-05 検証確定、[`docs/02-fpc-kicad.md`](docs/02-fpc-kicad.md))。北 5 枚は c0 を 72° 回転、南 5 枚は c5 を 72° 回転で共通化。
- **極専用 PCB は廃止** (2026-06-02)。10 カセット + ペンタゴンねじ留め構造の採用に伴い、極周辺への別基板配置をやめ、**全 800 hex を共通 FPC に集約**。
- 各カセット FPC は **80 LED** (= カセットに属する全 hex)。極先端 hex も truncate せず各カセットの一筆書きに含む。
  - 各カセットに **非極ペンタゴン 1 個** が含まれ、その位置は LED ではなく **M2.5 クランプねじの貫通穴** になる ([§2.8](#28-pole-assembly--球体コア--短-pillar--2--極-pcb--キャップ-案-s4--案-k_new) 参照)。
- **Two skeleton FPC Gerbers: north (c0) + south (c5) mirror, 5 each (no polar PCB). Per-cassette LED count: 80 (all hexes; 1 pentagon position becomes the M2.5 screw through-hole).**
- **LED 総数: 800** = 共通 FPC hex 80 × 10 (全 hex)
  - LED 非搭載のペンタゴン (12 個・全て LED 無し): 非極 pent 10 個 (M2.5 クランプねじ穴) + 極 pent 2 個 (南極=磁気端子 / 北極=装飾蓋)
- データチェーン: **5 ストリップ** = 5 縦縞 (各 **160 LED = 80 × 2**、北カセット → 赤道マザーリングでクロス → 南カセット)。極ストリップは無し。ESP32 は **5 並列出力**。
</fpc>

### 2.5 FPC fixation / FPC の固定方法

<fpc_fixation>
- **接着剤は使わない (zero adhesive)** — 前作の全損トラウマに直結するため絶対禁止。
- 固定法: **全面 `back_gore`(機械式・テープレス狙い)** (2026-06-04 方針更新、試作検証待ち)。
  - `back_gore` = **薄い (1mm) Goldberg ハーフゴア**を FPC 裏に当て、カセット側へ押し付けて FPC を挟持。アセテートテープは**予備/任意**に降格(接着剤ゼロは不変)
  - **0603 逃げ**: back_gore の **hex 穴を各 LED と一致**させ、FPC 裏の 0603 を穴に収める → 押し圧は島間 web/bridge にのみ掛かる
  - **保持**: hex ギャップに分散したスナップ/ネジで back_gore を引き、均一圧で FPC 浮きを防ぐ(必要なら gore 半径を僅かに大きくして予圧)。inner_deck/ペンタねじ/ダボ位置は開口
  - FPC を外向きに押す → LED がラッパ穴に座り位置決めも兼ねる。詳細は [`docs/01-shell-cad.md` §カセット裏面構造](docs/01-shell-cad.md#cassette-back-side-structures--カセット裏面構造-inner_deck--back_gore--ring_claw)
- 外殻裏面に **`anchor_post` (位置決めピン/突起)** を肉抜きギャップに生やし、FPC 基準穴で位置決め + 後付けパーツの固定先を兼ねる。
- **NEVER 3M両面テープ提案 / NEVER 瞬間接着剤・エポキシ.** これらは過去の失敗履歴。
- **Adhesive-free: a thin (1mm) Goldberg half-gore (`back_gore`) presses the FPC onto the shell mechanically; acetate tape is optional backup. Hex holes clear the back-side 0603 caps.**
</fpc_fixation>

### 2.6 Equator connection / 赤道接続

<equator>
- **外殻側にポゴピン (通常タイプ SMT)、マザーリング側はフラット金パッドのみ。**
  - 過去案 (両端ポゴピン/マザーリング側ポゴピン) は採用しない。
- 外殻内側の赤道エッジに **`inner_deck` (ポゴ台座)** を配置し、そこから垂直下向きにポゴピンが生える。
  - **FPC 後付けのため外殻と一体成形しない別パーツ**。FPC 装着後に **3 点止め = カセットのダボ穴 ×2(未貫通)+ ネジ ×1(Φ2.2 貫通)** で固定。固定点は hex 交点(島の隙間) (2026-06-04 実装確認)。
  - **パッド = 6 極/カセット = `5V-GND-DIN-DOUT-GND-5V`** (回文、データ隣=GND でシールド)。左3=チェーン始端(DIN/LED01)・右3=終端(DOUT/LED80)に接続 (2026-06-04 確定)。全 **60 ポゴ** (北30+南30)。ポゴは 2.54 DIP (RTLECS 1.5A/pin) を FR4 補強材で支持。全白禁止+輝度上限運用
  - **5V/GND は両端 2 枝給電**(左→始端バス / 右→終端バス)→ バス両端給電で IR ドロップ半減 + 容量2倍 + 接点冗長
  - **inner_deck = 小型 FR4 PCB**(上面=FPC 半田パッド6 / 下面=DIP ポゴ6、挿抜力を FPC から分離)。FPC は **1 結合 tab(6 パッド)** を rim から ~90° 曲げて半田。水平シェルフ(底面 Z=0)(2026-06-04 確定、案 A)
- マザーリングは **コンポーネント実装ゼロのフラットなドーナツ基板** (表裏に金メッキパッドのみ、球体コアにマウント)。
- 赤道面トポロジー: **外側はゴールドバーグの辺に沿ったジグザグ / 内側 (`inner_deck` 底面) は Z=0 水平フラット**。
  - 外側ジグザグが組み立て時の "インロー (位置決めガイド)" を兼ねる。
- **`ring_claw`**: 各カセット赤道エッジの爪がマザーリングを掴み、位置決め + 抜け止め + 圧着分担を担う (詳細・力学の未合意点は [`docs/01-shell-cad.md` §カセット裏面構造](docs/01-shell-cad.md#cassette-back-side-structures--カセット裏面構造-inner_deck--back_gore--ring_claw))。
- 配線: 各 longitude スライス内で **北 DOUT → 赤道マザーリング → 南 DIN** をクロスルーティング。各スライスが独立した **160-LED ストリップ** (80 × 2)。南カセットの DOUT は終端 (ESP32 へ戻さない)。
- 圧着メカ: **案 K_new (非極ペンタゴンねじ × 10)** によりカセットが個別に球体コアへ引き込まれる → 赤道ポゴピンが各カセットそれぞれで圧着される ([§2.8](#28-pole-assembly--球体コア--短-pillar--2--極-pcb--キャップ-案-s4--案-k_new) 参照)。
</equator>

### 2.7 Bill of materials (confirmed parts) / 確定 BOM

| 項目 / Item | 確定 / Decided | 備考 / Note |
| --- | --- | --- |
| LED | **WS2812-2020 系** (B/C 互換) | 高さ 0.65 mm。**総数 800 = 共通 FPC 80 × 10** (極専用 PCB 廃止) |
| Controller / マイコン | **ESP32 系** (S3 / C3 など) | 別プロジェクト管轄。Wi-Fi/BLE + LED 制御。**5 並列** PIO/RMT 出力 |
| 充電 IC | (型番未定) | **別プロジェクト管轄** ([§1, Q6](#3-open-questions--未確定事項) 参照) |
| バッテリ | **LiPo 2000 mAh × 2** | 球体コア内に格納。合計 ~14.8 Wh |
| FPC 固定テープ | アセテートテープ (片面) | 例: 一般電子工作向けアセテートクロステープ |
| 外殻 | 3D プリント (PETG)、黒 | レジン or 高精度 FDM |
| ~~極専用 PCB~~ | **廃止 (2026-06-02)** | 案 S4 廃止。極周辺 LED は無し。南極=磁気端子 / 北極=装飾蓋 |
| クランプねじ | **M2.5 真鍮意匠ねじ × 10** (黒もしくは無垢真鍮) | **各カセットの非極ペンタゴン位置 → コア表面のサテライト・ボスへ螺合**。沈み込み (recessed) で意匠ボタン演出 |
| 真鍮インサート | **M2.5 ヒートセット × 10** (深さ 4 mm) | 球体コアの 10 サテライト・ボスのねじ受け |
| Pillar (極スタブ) | **3D プリント PETG × 2 (北/南)** | 球体コアと一体造形。**南極=磁気端子の支持 + 配線通路 / 北極=装飾蓋の支持** (構造荷重は受けない) |
| TPU ガスケット | **TPU 95A 厚 0.5-1.0 mm** (オプション) | 案 K_new で応力分散されたため必須度低下。衝撃保険として残す |
| 磁気端子 (南極) | **市販 Φ4 mm マグネット、2 極接点** | 具体型番は [§3 Q17](#3-open-questions--未確定事項) |
| 端子配線 | **AWG26 × 2 本** | 南極キャップ → 南極 pillar 内通路 → コア内充電 IC |
| ポゴピン | **RTLECS 2.54 DIP × 6/カセット = 60** | 1.5A/pin, ストローク 2.0mm, ばね 75gf, 高 7mm。赤道 inner_deck のみ (極側廃止)、FR4 補強材で支持。順 `5V-GND-DIN-DOUT-GND-5V`(左3→始端/右3→終端、両端2枝給電) |

### 2.8 Pole assembly — 球体コア + 短 pillar × 2 + キャップ (案 K_new、極専用 PCB 廃止)

<pole_assembly>
**クランプ機構の根本方針 (案 K_new)**: 極ねじを廃止し、**10 個の非極ペンタゴン位置で M2.5 ねじ留め** に変更。
極部はクランプから解放され、純粋に磁気端子 (南) / 装飾蓋 (北) として機能する。

#### コア・マザーリング

- **球体コア** (central chassis): 球内中心に位置するシャーシ。**LiPo 2000×2 + ESP32 + 充電 IC を内蔵**。
  形状候補は球/円柱/直方体 ([§3 Q31](#3-open-questions--未確定事項))。
- **コア表面に 10 サテライト・ボス** (Φ5 mm × 高さ 数 mm) が放射状に突出。
  位置は **緯度 ±26.57° × 経度 5 等分 (北 5 + 南 5)** = T=81 G(9,0) の非極ペンタゴン中心と完全一致。
  各ボスには **M2.5 真鍮ヒートセットインサート** (深さ 4 mm) を埋め込み。
- **赤道マザーリング** = 球体コアに連結された **ドーナツ状フラット PCB** (表裏に金パッドのみ)。
  カセットを 1 枚も挿していなくても、コア + マザーリング単体で給電・点灯テスト可能。

#### クランプ力学 (案 K_new)

- 各カセットの **非極ペンタゴン位置 (緯度 ±26.57°、各カセット 1 個)** にΦ2.7 ねじ通し穴 + M2.5 沈み込み座ぐり
- 外側から **M2.5 真鍮ねじ (黒/真鍮無垢、recessed)** をカセット → サテライト・ボスへ螺合
- 締め込むと **各カセットがコア方向へ radial-inward に引き込まれる** → カセット剛性によって赤道エッジも内向きに動く → 赤道ポゴピンが圧着
- **10 ねじによる分散クランプ** = 応力集中ゼロ、衝撃に強い、カセット個別交換可
- ねじ頭処理: **意匠アクセント (案 C) として "見せる"**、外殻面より **わずかに窪み (recessed)** で 10 個の icosahedral 対称配置を強調

#### 極部 (pillar + キャップ) — **極専用 PCB は廃止 (2026-06-02)**

極周辺への LED 配置をやめ、全 hex を共通 FPC に集約したため、極専用 rigid PCB・極ストリップ・極チェーン配線はすべて廃止。極部は **南極=磁気端子 / 北極=装飾蓋** のみ。

- **短 pillar × 2** (北極/南極): 球体コアから極方向へ伸びる **~15-20 mm の PETG スタブ**。
  - **役割**: 南極=磁気端子モジュールの支持 + 配線通路 / 北極=装飾蓋の支持 (構造クランプ荷重は受けない)
  - 南極 pillar は **内部に Φ3 mm 配線通路** (AWG26 × 2 = 磁気端子用)
  - 北極 pillar は配線通路不要 (極 LED が無いため)
  - コアと一体 3D プリント想定 ([§3 Q33](#3-open-questions--未確定事項))
- **極キャップ × 2** (LED 無し):
  - **南極**: 磁気端子モジュール (Φ4 磁石保持 + 端子パッド窓)
  - **北極**: 純粋装飾蓋
  - **pillar への固定**: スナップ留め (中央ねじ無し)
- 極ペンタゴン (2 個) は LED 非搭載 — 非極ペンタゴン (ねじ穴) と同じく LED 無し領域

#### 応力対策 / Stress-relief (案 K_new で大幅簡素化)

案 K_new では **10 点分散クランプ** により応力集中がほぼ消失。前案 (案 K1) で必須だった対策は以下のとおり降格:

1. **TPU 95A ガスケット** — 必須 → **オプション** (衝撃保険、入れても良いが必須ではない)
2. **皿ばね** — **不要** (中央ねじが消えたため対象がない、ただし非極ねじにナイロンワッシャを使うことで緩み止めに置き換え可)
3. **pillar 根本フィレット** — pillar が構造荷重を受けないため重要度低下 (が、3D 出力時のクラック予防として残す)
</pole_assembly>

---

## 3. Open Questions / 未確定事項

CLAUDE が勝手に決めず、必ず確認すること。
**Do not silently pick a side; ask the user.**

<open_questions>
**機構・部品系 / Mechanical & parts**
- **Q1: ポゴピンボックスを外殻にどう固定するか.** 案 A スナップ / 案 B 極小皿ネジ / 案 C モノコック ([概念ドキュメント【ログ 13】](docs/10pieces-isolation-sphere-concept.md))
- **Q3: ポゴピンのピッチ (2.54 / 2.0 / 1.27 mm).** 赤道 inner_deck で要確定。候補 RTLECS 2.54 DIP の定格電流/ストロークも要確認
- **Q15: 南極マグネット個数とレイアウト** (orientation lock のため非対称配置候補)
- **Q17: 磁気端子の市販品具体型番** (Φ4mm 2 極、AliExpress 等)
- **Q31-Q35: 球体コア詳細** (形状 / マザーリング結合 / pillar 結合 / 電池配置 / 充電 IC 位置) — [`01-shell-cad.md`](docs/01-shell-cad.md)
- **Q54: 赤道圧着力の検証方法** (案 K_new でテコの腕が長くなったので試作で実測必要)
- **Q55 (NEW): ペンタゴン縮小 + ラッパ穴被せの実装** — 標準 Goldberg ではなく **非極ペンタゴンを縮小** し、周囲 hex のラッパ穴を斜めに pent 領域へ被せる意匠演出。`goldberg.py` のメッシュ修正が必要 — [`01-shell-cad.md`](docs/01-shell-cad.md)

**電気系 / Electrical**
- **Q2: ESP32 の具体型番 (S3 / C3 / その他).** 充電 IC 別プロジェクト経由で決まる。**5 並列 PIO/RMT 出力が要件** (5 ストリップ)
- **Q4: マザーリング基板の電源・データ供給方法.**
- **Q40-Q42: 充電 IC とのインターフェース** (コネクタ規格 / 充電電流 / 過放電保護位置) — [`03-power-charging.md`](docs/03-power-charging.md)

**クローズ済み (Resolved)**
- ~~Q22-Q26 極専用 PCB の詳細~~ → **極専用 PCB 廃止 (2026-06-02)**。全 hex を共通 FPC に集約 (80 LED/cassette、5 ストリップ)
- ~~Q27 pillar 素材~~ → PETG 確定
- ~~Q36-Q39 応力対策数値化~~ → 案 K_new で重要度低下 (オプション扱い)
- ~~Q43-Q48 極 PCB サイズ / WS2813 / 6 ストリップ~~ → **極 PCB 廃止により無効化**。**5 ストリップ (各 160) 確定**、WS2812 系維持
- ~~Q29 北極クランプ~~ → スナップ留め (極ねじなし)
- ~~Q49 LED 総数~~ → 800 確定
- ~~Q50 ペンタゴン穴の Gerber 表現~~ → 非極 pent はねじ穴に転用 (Φ2.7 + M2.5 座ぐり)
- ~~Q51-Q53 案 K_new 切替 + ねじ規格 + 頭処理~~ → 案 K_new 採用 / M2.5 真鍮 / 案 C 意匠アクセント (recessed)
</open_questions>

---

## 4. Development Workflow / 開発ワークフロー

<workflow>
### 4.1 3D CAD (Blender Python)
- 球体外殻は **Blender 上で Python スクリプトから生成** する想定 (手動モデリングではなく自動化)。
- 必須処理:
  1. T=81 ゴールドバーグ多面体 (φ100mm/φ95mm) のメッシュ生成 + Boolean Diff で中空化。
  2. **Z=0 を横切る面が存在しないよう** 多面体の向きを調整 (赤道に LED を載せないため)。
  3. 経度 36° × 5 + 赤道 Z=0 フラットカットで 10 カセットに分割 (赤道の切断面のみ完全平面にクリーンアップ)。
  4. 各 LED 位置にラッパ穴 (円錐, ~120°) を Boolean で掘る。
  5. 外殻裏面に「`anchor_post` (FPC 位置決めピン)」「南極ネジボス」を生やす (`inner_deck`/`back_gore` は別パーツとして後付け)。
- 出力: 各カセット用 STL ファイル × 10 (もしくは共通 1 種類を回転コピー)。

### 4.2 FPC 回路設計 (KiCad)
- ターゲット: 骨組み FPC **2 種類** (北 c0 + 南 c5 鏡像、各 5 枚)。`generate_fpc_chain.py -c 0` / `-c 5` で生成。
- 端子配置は **左右対称 (回文)** にして、上下反転問題をマザーリング側クロス配線で吸収。
- LED 配置データは Blender 側スクリプトと共有する (CSV か JSON で頂点座標をやり取り)。

### 4.3 Firmware (ESP32 系)

- WS2812 駆動 + Wi-Fi/BLE 経由のフレーム供給。具体型番は未確定 (Q2)。

### 4.4 Python 環境 / Python environment (uv)

- **パッケージマネージャ: [uv](https://docs.astral.sh/uv/)** (pip / poetry / conda は使わない)。
- Python バージョン: **3.11 pinned** (`.python-version`)。
- ルート単一プロジェクト構成 — `shell-cad/` と `fpc-kicad/scripts/` 両方が同じ `.venv` を共有。
- 主要コマンド:
  - 依存追加: `uv add <pkg>` (例: `uv add numpy bpy`)
  - 開発用追加: `uv add --dev <pkg>` (例: `uv add --dev pytest`)
  - スクリプト実行: `uv run python shell-cad/scripts/foo.py`
  - 環境再構築: `uv sync`
- 追跡対象: `pyproject.toml`, `uv.lock`, `.python-version`
- 無視: `.venv/` (gitignore 済)
- **例外**: KiCad の `pcbnew` モジュールは KiCad 同梱 Python に紐づくため uv 環境外。KiCad 内部から呼ぶスクリプトは KiCad の Python で実行する。

### 4.5 リポジトリ規約 / Repository conventions

- プロジェクトルート: `/Users/katano/work/FPC-isolation-sphere/`
- リモート: `https://github.com/sastles-com/FPC-isolation-sphere` (private)
- 編集ごとに commit & push する運用。重いファイル (動画 / 大容量バイナリ) は push 前に必ず確認。

#### フォルダ構成 / Folder layout

```text
/
├── CLAUDE.md                    索引 + ハード規則 (このファイル)
├── README.md                    GitHub ランディング (TODO)
├── docs/                        設計 spec (WHAT / WHY) — §8 索引参照
│   ├── 10pieces-isolation-sphere-concept.md   一次資料
│   ├── 01-shell-cad.md          (予定)
│   └── 02-fpc-kicad.md          (予定)
├── shell-cad/                   Project 1: Blender Python
│   ├── scripts/                 .py スクリプト
│   ├── blend/                   .blend ファイル
│   └── output/                  生成 STL (gitignore)
├── fpc-kicad/                   Project 2: KiCad
│   ├── lib/                     シンボル / フットプリント
│   ├── scripts/                 KiCad Python API ヘルパー
│   └── fab/                     生成 Gerber (gitignore)
├── shared/                      ★ プロジェクト間インターフェース
│   └── led_positions.csv        Blender が producer、KiCad が consumer (手編集の設計データはここ)
└── output/                      ★ トップレベル成果物 (gitignore)
    └── fpc_*.{csv,png,svg}       generate_fpc_chain.py 等の再生成可能な出力
```

- **設計知識は `docs/NN-<slug>.md` に集約**。各サブプロジェクトフォルダに CLAUDE.md は置かない (§8.2 重複禁止)。
- `shared/` のファイル仕様 (列定義 / 座標系 / ID 規約) は **producer 側の doc** に書く。
- build artifact (`shell-cad/output/`, `fpc-kicad/fab/`, **トップレベル `output/`**) は中身を gitignore、フォルダ自体は `.gitignore` ファイルで保持。
  - 複数プロジェクト共通/横断の再生成成果物 (例: FPC チェーン展開図) は **トップレベル `output/`** へ。シェル専用 STL/blend は `shell-cad/output/`。**手編集する設計データ**(legend の確定版など) は `shared/` へ昇格。
</workflow>

---

## 5. Working with Claude — Prompt & Collaboration Conventions

動画 (Christian Ryan & Hannah Moran, Anthropic Applied AI, "Prompt Engineering 101" — 2025) から抽出した規約を、本プロジェクトでの Claude 利用ルールに昇華する。
**Conventions distilled from the Anthropic Applied AI talk on prompt engineering, applied to how Claude should operate inside this repo.**

<collaboration_rules>
### 5.1 Structure prompts with XML / プロンプトは XML タグで構造化
- ユーザーへの回答や設計提案を返すときも、長文では **`<context>` `<constraints>` `<proposal>` `<open_questions>` のような XML タグ** で章立てする。
- 境界が明確 + トークン効率が良い + Claude 自身も後で読み返しやすい。

### 5.2 Follow the 10-part prompt structure when authoring prompts for sub-agents
1. Task context (役割・高レベルタスク)
2. Tone context (口調・スタイル)
3. Background data, documents, and images (本ファイルや概念ドキュメント等)
4. Detailed task description & rules
5. Examples (3〜5 個、関連性・多様性・量)
6. Conversation history (必要なら)
7. Immediate task / request
8. Step-by-step thinking ("take a deep breath / think step by step")
9. Output formatting (XML タグや見出しを指定)
10. Prefilled response (必要なら `<response>` 等で書き出しを誘導)

### 5.3 Examples beat descriptions / 例示優先
- ハーフゴアの座標フォーマット、KiCad ネット名規約など **形式を伴う指示は必ず 3 例以上** 添えてから依頼する。
- "Examples act as concrete templates" — 文章で説明するより例を 1 つ見せた方が一貫性が高い。

### 5.4 Don't infer when uncertain — ask / 不明点は推論せず質問する
- これは **ユーザーから明示的に付与された規約** でもある (本プロジェクトの根本ルール)。
- 動画でも `Base your analysis solely on the information visible in the images. Do not make assumptions` という規律が繰り返し強調されている。
- 該当時の挙動: 確信が持てない仕様 / 寸法 / 部品型番は **必ず質問** すること。`<open_questions>` セクションへの追記も並行して行う。

### 5.5 Iterate v1 → v5 / 反復改善を前提とする
- 動画では事故報告書解析プロンプトを **v1 → v5 まで段階的に改善** していた。
- 本プロジェクトの設計・スクリプトも **「一発で正解を出さない」前提** で進め、版を分けて差分で議論する。

### 5.6 Wrap critical outputs / 重要出力はタグで囲む
- "Wrap your final verdict in `<final_verdict>` XML tags" の流儀に倣い、
  - 設計判断の最終結論は `<decision>...</decision>`
  - BOM 候補は `<bom_candidate>...</bom_candidate>`
  - 寸法変更提案は `<dimension_change>...</dimension_change>` で囲む。
</collaboration_rules>

---

## 6. Hard Rules / 厳守事項

<hard_rules>
- **NEVER** 接着剤・瞬間接着剤・エポキシで FPC や外殻を固定する提案をしてはいけない (過去の全損事故)。
- **NEVER** 赤道 Z=0 のライン上に LED を配置する設計を出してはいけない (ポゴピン領域と衝突)。
- **NEVER** Goldberg 多面体の **六角形/五角形の面の中央を分割線が貫く** ような赤道カットを採用してはいけない (案 A: 接合面のみ平面化が確定方針)。
- **NEVER** ポゴピンをマザーリング側に植える設計に戻してはいけない (外観劣化のため外殻側固定で確定)。
- **NEVER** 極ねじ (中央クランプねじ) を復活させる提案をしてはいけない (案 K1 → 案 K_new で廃止確定。極部は端子/装飾のみ)。
- **NEVER** 非極ペンタゴン位置に LED を載せる提案をしてはいけない (M2.5 クランプねじの貫通穴に使うため LED 不可)。
- **ALWAYS** 未確定の寸法・型番・トポロジーが必要な場合は質問する。推論で埋めない。
- **ALWAYS** 概念ドキュメント `docs/10pieces-isolation-sphere-concept.md` を一次資料として参照する (本ファイルはダイジェスト)。
- **ALWAYS** カセットクランプは **10 非極ペンタゴン M2.5 ねじ分散方式 (案 K_new)** を前提に設計する。
</hard_rules>

---

## 7. References / 参考資料

- `docs/10pieces-isolation-sphere-concept.md` — 全議論ログ (14 セクション)。背景や却下案の理由はこちらに残してある。
- Anthropic Applied AI talk "Prompt Engineering 101" by Christian Ryan & Hannah Moran (2025) — `Ve1T-xWixeVSnM0x.mp4` (本リポジトリ同梱)
- 過去試作の note 記事 (概念ドキュメント【ログ 6】に URL あり)

---

## 8. Sub-Project Docs / 小プロジェクト個別ドキュメント

本プロジェクトは複数の小プロジェクト (3D CAD / FPC / Firmware / 治具 など) で構成される。
**各小プロジェクトの詳細は CLAUDE.md には書かず、`docs/` 配下に独立した markdown を作る**。
CLAUDE.md は索引役として下表だけを維持する。

### 8.1 Index / 現状の小プロジェクト一覧

| # | Slug | Doc | Status | Summary |
| --- | --- | --- | --- | --- |
| 00 | concept | [`docs/10pieces-isolation-sphere-concept.md`](docs/10pieces-isolation-sphere-concept.md) | reference | 全議論ログ (一次資料、編集不可) |
| 01 | shell-cad | [`docs/01-shell-cad.md`](docs/01-shell-cad.md) | wip | 外殻 (T=81 ゴールドバーグ) + 球体コア + 短 pillar × 2 + キャップ + クランプ機構 |
| 02 | fpc-kicad | [`docs/02-fpc-kicad.md`](docs/02-fpc-kicad.md) | draft | 共通骨組み FPC × 10 (全 hex 80 LED、一筆書き + polyhedral 展開、極専用 PCB 廃止) |
| 03 | power-charging | [`docs/03-power-charging.md`](docs/03-power-charging.md) | draft | 南極磁気端子 (Φ4 mm 2 極) + LiPo 2000×2 + AWG26 配線。充電 IC は別プロジェクト |
| — | — | — | — | _(未作成。下記 §8.2 のルールで増やしていく)_ |

予定している小プロジェクト (まだファイル未作成):
- `04-motherboard-kicad.md` — 赤道フラットドーナツ基板 (球体コアにマウント)
- `05-firmware-esp32.md` — ESP32 系ファーム (WS2812 駆動 + Wi-Fi/BLE) ※別プロジェクト管轄
- `06-assembly-jig.md` — 組立治具 / カセット交換手順 (該当時)

### 8.2 Rules for sub-project docs / 個別ドキュメントの規約

<subdoc_rules>
- **置き場所**: `docs/NN-<slug>.md` (NN は 2 桁連番、slug は kebab-case)。
- **新規作成時は `/new-subdoc <slug>` skill を使う** (本リポジトリの `.claude/skills/new-subdoc/` で定義)。
  - 手動で作る場合も同 skill のテンプレに合わせる。
- **ファイル冒頭で必須**:
  - H1 タイトル
  - フロントマター的に `<subproject>` タグで `name / parent / status / owner / depends_on` を宣言
  - "Scope (この doc が扱う範囲)" "Out of scope (扱わない範囲)" を明記
- **CLAUDE.md との重複禁止**: 確定したハード仕様 (LED 型番、外径、ピン極性など) は CLAUDE.md にだけ書き、サブ doc からは参照する形にする。
- **未確定事項は両方に書かない**。サブ doc 側の `<open_questions>` に集約し、CLAUDE.md からはリンクのみ。
- **索引更新**: 新規 doc を作ったら **CLAUDE.md §8.1 のテーブルに行を追加** (Status: draft / wip / stable / reference)。
- **削除/リネーム**: 旧パスへの参照が CLAUDE.md / 他サブ doc に無いかを確認してから行う。
</subdoc_rules>

### 8.3 Sub-project doc template / テンプレート

新規 doc は最低限以下の骨格を持つ (skill `/new-subdoc` が自動生成):

```markdown
# <Sub-project Title>

<subproject>
- name: <slug>
- parent: Isolation Sphere V2
- status: draft | wip | stable | reference
- owner: <name>
- depends_on: [<other slug>, ...]
</subproject>

## Scope / この doc が扱う範囲
- ...

## Out of scope / 扱わない範囲
- ...

## Confirmed decisions / 確定事項
- ...

## Open questions / 未確定事項
- Q1: ...

## References
- CLAUDE.md §N
- docs/10pieces-isolation-sphere-concept.md ログ X
```

### 8.4 Claude への指示 / Behavior

<behavior>
- ユーザーが新しい小プロジェクト (新しい関心領域) について作業し始めたら、**まず該当する `docs/NN-<slug>.md` の有無を確認**。
  無ければ「個別 doc を作りますか? (`/new-subdoc <slug>`)」と提案する。勝手には作らない。
- 既存サブ doc がある作業では、**最初にその doc を読み込んでから** 作業に入る。
- サブ doc 範囲の詳細仕様を **CLAUDE.md に追記しようとしない** (索引と確定要約だけがここに来る)。
- 議論の結果サブ doc 同士の整合性が崩れた場合は、影響範囲を `<impact>` として報告してから修正する。
</behavior>

---

## 9. Web Publishing / 成果物の Web 公開

<web_publishing>

### 9.1 Lolipop FTP アップロード

**STL / HTML ビューアなどの成果物は Lolipop サーバーへ FTP アップロードして公開する。**

#### FTP 接続情報

認証情報は **`.ftp_credentials`** (gitignore 済) に格納する。
**NEVER パスワードを CLAUDE.md や任意の追跡ファイルに直書きしない。**

```bash
# .ftp_credentials (gitignore済・コミット禁止)
FTP_HOST=ftp.tajmahal.mond.jp
FTP_USER=mond.jp-tajmahal
FTP_PASS=<実際のパスワード>      # ← ここだけ非公開
FTP_PROJECT_ROOT=isolation-sphere
FTP_BASE_URL=http://tajmahal.mond.jp/isolation-sphere
```

テンプレート: `.ftp_credentials.example` (パスワード空欄でコミット済)

#### アップロード手順

```bash
# 全ファイル一括
bash shell-cad/scripts/upload_to_lolipop.sh

# 1ファイル指定
bash shell-cad/scripts/upload_to_lolipop.sh web/output/foo_viewer.html
```

#### フォルダ構成

```text
web/
└── output/              ← gitignore
    ├── *.html           ← STL ビューア HTML
    └── *.stl            ← STL (HTML と同ディレクトリに置く)
```

#### 公開 URL

- トップ: `http://tajmahal.mond.jp/isolation-sphere/`
- STL ビューア: `http://tajmahal.mond.jp/isolation-sphere/web/output/<name>_viewer.html`

### 9.2 STL ビューア HTML 生成

Three.js (CDN) を使った対話型 STL ビューア HTML を自動生成できる。

```bash
# 単一 STL → HTML
uv run python shell-cad/scripts/generate_stl_viewer.py shell-cad/output/foo.stl

# バッチ
uv run python shell-cad/scripts/generate_stl_viewer.py shell-cad/output/*.stl
```

- STL と HTML は同じフォルダに出力される (相対 URL で読み込む)
- Drag: 回転 / Scroll: ズーム / Right-drag: パン
- ポリゴン数・バウンディングボックス寸法を HUD 表示

### 9.3 新しい成果物を追加する場合

1. STL または OBJ を生成する
2. `generate_stl_viewer.py` でビューア HTML を生成
3. `upload_to_lolipop.sh` でアップロード

</web_publishing>
