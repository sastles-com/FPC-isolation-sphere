# FPC KiCad — 骨組み FPC アートワーク

<subproject>
- name: fpc-kicad
- parent: Isolation Sphere V2
- status: wip
- owner: sastle-com
- depends_on: [shell-cad]
</subproject>

## Scope / この doc が扱う範囲

- **共通骨組み FPC** (10 カセット共通の 1 種類 Gerber、各 80 LED) の KiCad アートワーク作成
- 一筆書きチェーン + polyhedral 展開図の生成 (`generate_fpc_chain.py`)
- LED 配置データ ([`../shared/led_positions.csv`](../shared/led_positions.csv)、shell-cad が producer) からの **自動 LED 配置スクリプト**
- 端子レイアウト (赤道 inner_deck の 6 パッド: `5V-GND-DIN-DOUT-GND-5V`)
- ガーバー出力までの一連の手順

> **2026-06-02 設計変更**: 極専用 PCB (案 S4) は**廃止**。全 800 hex を共通 FPC に集約 (80 LED/cassette、5 ストリップ)。極部は南極=磁気端子 / 北極=装飾蓋で LED 無し。

## Out of scope / 扱わない範囲

- 外殻 3D 形状 / 球体コア / pillar → [`01-shell-cad.md`](01-shell-cad.md)
- 磁気端子・LiPo・配線ルート → [`03-power-charging.md`](03-power-charging.md)
- ESP32 ファーム → 別プロジェクト管轄 (CLAUDE.md §1, §3 Q2)
- 赤道マザーリング基板 → 別 doc (`04-motherboard-kicad.md` 予定)

## Confirmed decisions / 確定事項

### アーキテクチャ: 全 hex 共通 FPC × 10 + 案 K_new (非極 pent ねじ穴)

- **共通骨組み FPC × 10 枚** (Gerber 1 種)
  - 各カセット **80 LED** (= カセットに属する全 hex。極先端 hex も truncate せず含む)
  - 形状: 円形ランド (LED, r≈2.25mm) + 帯 (ブリッジ, 3mm) の骨組み (≠ ベタ三角ゴア)
  - 実装: **表 WS2812C-2020 / 裏 0603 バイパスコンデンサ**
  - **非極ペンタゴン位置に Φ2.7 ねじ通し穴 + M2.5 沈み込み座ぐり** — 案 K_new の M2.5 真鍮意匠ねじ用 (各 FPC に 1 個ずつ)
  - メリット: 球面追従性、熱抜け、テープ糊が外殻と直接シール

- **LED 総数: 800** = 共通 FPC hex 80 × 10 (全 hex)
  - LED 非搭載のペンタゴン (12 個全て): 非極 pent 10 個 (M2.5 ねじ穴) + 極 pent 2 個 (南極=磁気端子 / 北極=装飾蓋)

### 配線・データチェーン (5 ストリップ構成)

- 一筆書きの **DIN(start)・DOUT(end) は赤道中央で隣接** ([Q62](#open-questions--未確定事項))。inner_deck は **6 パッド = `5V-GND-DIN-DOUT-GND-5V`**(回文、データ隣=GND)。**左3→チェーン始端(DIN/LED01)/ 右3→終端(DOUT/LED80)**に接続 → 5V/GND を**バス両端から 2 枝給電** → IR ドロップ半減 + 容量2倍 + 接点冗長
- N/S 共通 FPC の上下反転は **赤道マザーリング側のクロスルーティング (`N_DOUT → S_DIN`) で吸収** ([Q62b])
- **5 並列ストリップ構成**:
  - Strip 1-5: 各 longitude slice (北 80 LED → 赤道マザーリングでクロス → 南 80 LED = **160 LED each**)
  - 南カセットの DOUT は終端 (ESP32 へ戻さない)
  - 合計: 5 × 160 = **800 LED**。極ストリップは無し
- ESP32 側: **5 並列 PIO/RMT 出力** で各ストリップを独立駆動 (fault isolation 効果)
- ポゴピン: 2.54 ピッチ **DIP (RTLECS, 1.5A/pin, ストローク 2.0mm, 75gf, 高 7mm)** を inner_deck の **FR4 補強材**で支持。**6 ピン**(電源 2 重化、スロット 12.7mm)。全 60 ポゴ ([Q67] 確定)

### 非極ペンタゴン位置のクランプねじ穴 (案 K_new)

- **位置**: 各共通 FPC に 1 箇所、緯度 ±26.57° の非極 pent 中央
- **穴形状**: Φ2.7 貫通穴 (M2.5 ねじ通し用) + 上面に Φ4.7 × 深さ 1 mm の沈み込み座ぐり (M2.5 真鍮意匠ねじ頭収容)
- **FPC 上の銅配線禁止領域**: 穴周囲 Φ4 mm を keep-out (ねじ頭との短絡防止)
- 共通 FPC が **同じ Gerber × 10** であるため、北 5 + 南 5 の全カセットに同じねじ穴が刻まれる

### LED 配置データの利用

- producer: shell-cad (`shared/led_positions.csv`)
- consumer: KiCad 配置スクリプト (V1 の `place_from_csv.py` 思想を流用)
- 必要列: `cassette_id` (0..9), `serial_index`, `x, y, z`, `normal_*`, `face_kind` (pent/hex), **`is_screw_hole` (非極 pent のみ true)**
  - 全 LED が共通 FPC 上なので `board_kind` 列は不要 (極専用 PCB 廃止)

### 参考画像 / Reference images

**V1 試作の骨組み FPC 実物** (hex island + bridge、表 WS2812C / 裏 0603、一筆書きチェーン):

![V1 骨組み FPC 試作](images/fpc_prototype_v1.jpg)

> **ゴール (2026-06-02)**: この骨組み FPC をカセット裏面に貼ったとき、**FPC 上の LED 位置がカセットの hex ラッパ穴と一致**するように展開する ([Q63](#open-questions--未確定事項) 投影法の核心)。

### チェーン + 展開図スクリプト `generate_fpc_chain.py` (2026-06-02 実装、polyhedral unfold へ刷新)

**スクリプト**: `shell-cad/scripts/generate_fpc_chain.py`(numpy + matplotlib、bpy 非依存)
**用途**: 1 ハーフゴアカセット分の一筆書き + **多面体展開図(歪みゼロ)** + 骨組み FPC 外形を生成。

#### アルゴリズム

- **一筆書き(確実化)**: Warnsdorff 順 + **バックトラック DFS** → start/end 指定の Hamiltonian path を確実に発見
  - 既定端点: **DIN = 赤道行で経度中央に最も近い hex / DOUT = その面隣接 hex**(中央・隣接、[Q62](#open-questions--未確定事項))
- **展開(展開図)= polyhedral unfold**: カセット内側は**多面体**(平らな hex 面)なので、チェーンに沿って共有辺をヒンジに**二面角 180° へ開く**ことで **歪みゼロ展開**。投影(equirect/sinusoidal)は不要に([Q63](#open-questions--未確定事項) 解決)
  - 各 hex は最良近似平面に planarize(Goldberg hex は僅かに非平面)
  - 曲率は除外された pentagon に集中 → hex のみの半ゴアはほぼ完全に平らに展開
- **骨組み FPC 外形**: 各 island に円(既定 r=`ISLAND_R`=2.25mm)+ チェーン連結に帯(既定 w=`BRIDGE_W`=3.0mm)

#### 2 段ワークフロー(Warnsdorff 素案 → legend 手修正)

```bash
# ① 素案生成 → legend CSV 書き出し
uv run python shell-cad/scripts/generate_fpc_chain.py -c 0
# ② legend を手修正後、それを使って再展開(Warnsdorff 再計算せず)
uv run python shell-cad/scripts/generate_fpc_chain.py -c 0 --legend output/fpc_legend_c0.csv
```

- legend = **編集可能な順序ファイル**(`order, face_idx`)。Phase 2 の Blender モーダル・エディタ(クリック順記録、note 記事方式)が上書き保存する単一の真実
- 展開は legend の順序にそのまま従う → 手修正がそのまま展開図/外形に反映

#### 出力(`output/` トップレベル、gitignore)

- `fpc_legend_c<N>.csv` — `order, face_idx`(編集可能な一筆書き順序)
- `fpc_unfold_c<N>.csv` — `order, face_idx, cassette_id, x3d/y3d/z3d, flat_x/flat_y, is_din, is_dout`
- `fpc_unfold_c<N>.png` — 展開図(hex 多角形 + 骨組み island/帯 + チェーン + DIN/DOUT)
- `fpc_skeleton_c<N>.svg` — 骨組み外形(KiCad/Inkscape で union 可、mm 単位)

#### 2026-06-02 実行結果 (cassette 0)

| 項目 | 値 |
|---|---|
| hex 面数 | 80 |
| 一筆書き | Warnsdorff+backtrack、DIN=fi626 / DOUT=fi628(隣接・赤道中央) |
| 全ブリッジ面隣接 | ✓ |
| **展開歪み (flat vs 3D弦)** | **平均 0.23% / 最大 0.27%** ← 実質ゼロ(多面体展開の正しさを実証) |
| 自己重なり | min gap 5.28mm / median 6.11mm → 重なり無し |
| 骨組み | island r=2.25mm(hex 内接円 2.42–3.28mm に収まる)+ 帯 3mm |

## Open questions / 未確定事項

<open_questions>

**チェーン経路関連 (2026-06-02 新規。Q56→Q62 等、shell-cad の Q56-Q61 との衝突回避でリナンバー)**

- **Q62 (実装済): DIN/DOUT 配置 = 赤道中央スタート + 隣接エンド** (2026-06-02)
  - **方針**: 赤道行の中央 hex を DIN (start)、その面隣接 hex を DOUT (end) とする一筆書き
  - **実装**: Warnsdorff 順 + バックトラックで確実探索(`generate_fpc_chain.py`)。cassette 0 で DIN=fi626 / DOUT=fi628 を確認
  - **含意 (Q65/Q67 で確定)**: 1 カセットが赤道側に DIN・DOUT の**データ2端子** → inner_deck は **6 パッド `5V-GND-DIN-DOUT-GND-5V`**
- **Q63 (解決): 展開法 = polyhedral unfold(投影は不採用)** (2026-06-02)
  - カセット内側は**多面体**(平らな hex 面)なので、投影(equirect/sinusoidal)で近似する必要は無く、**チェーンに沿って共有辺をヒンジに 180° 展開**すれば **歪みゼロ**(実測 max 0.27%)
  - 曲率は除外された pentagon に集中 → hex のみの半ゴアはほぼ完全平面に展開
  - equirect/sinusoidal は不採用(滑らかな球前提だった)。測地的最適化は不要
- **Q64: チェーンパターンの規則性** — Warnsdorff vs 列スネーク
  - **Warnsdorff** (現状): 全ブリッジ面隣接 (距離 ≈ 5.3–6.5 mm)、経路は不規則
  - **列スネーク**: 経度列ごとにジグザグ。視覚上整然だが一部ブリッジが面非隣接の可能性
  - 端点を「中央スタート+隣接エンド」に固定する Q62 と整合する経路生成が必要
- **Q65 (確定): inner_deck パッド数 = 6** — DIN/DOUT 両方赤道 + 電源 2 重化
  - **6 パッド = `5V-GND-DIN-DOUT-GND-5V`**(回文、データ隣=GND)。左3→始端/右3→終端で **5V/GND 両端 2 枝給電** → IR 半減・容量2倍・冗長 (2026-06-04 確定)
  - [shell-cad Q56](01-shell-cad.md) / CLAUDE.md §2.6 / §2.7 と同期済
- **Q66 (NEW): KiCad 配置ワークフロー** — legend 手配置 vs CSV スクリプト配置
  - **legend 手配置** (V1 実績): 平面展開図を下絵 (legend) にして KiCad で footprint を手置き
  - **CSV スクリプト配置** (★scope に既存): `generate_fpc_chain.py` の `flat_x/flat_y` + 各 island の向き + チェーン順を pcbnew API で自動配置・自動ブリッジ配線

- **Q62b: マザーリングの N/S クロス + ゾーン数** — `N_DOUT → S_DIN` のクロスはリング内配線で吸収(② 確定)。ポゴゾーンは 5 経度 × (上面=北/下面=南)。ユーザー提示図は 4 回対称だったので 5 ゾーンへ要修正
- **Q67 (確定): ポゴ実装基盤と電源 = 6 ピン DIP + FR4 補強材** (2026-06-02)
  - DIP ポゴ (RTLECS 1.5A/pin) を inner_deck の **FR4 補強材**で支持(DIP + 補強材)
  - **6 ピン `5V-GND-DIN-DOUT-GND-5V`**: 左3→始端/右3→終端で両端 2 枝給電 → 容量2倍・接点冗長・IR半減。スロット 12.7mm(5 zone × 周長で余裕)
  - **全白禁止 + 輝度上限**運用(5V 容量に整合)
  - **シリコン線+コネクタ案は不採用**(ホットスワップが崩れ組立煩雑)。電源補強は「広い GND/5V 銅ベタ + ポゴ 2 重化」で対応
  - 残: 圧着力 6×75gf=450gf/cassette ×10=4.5kgf は [Q54](01-shell-cad.md) のテコ検証と併せて確認。電圧降下の主因は FPC 5V トレース幅 → DIN/DOUT 中央注入で最遠距離を半減

**既存 open questions**

- **Q3: ポゴピンピッチ** — 2.54mm 候補確定的(RTLECS DIP)。定格電流/ストロークは [Q67] 参照

**クローズ済み (極専用 PCB 廃止に伴い無効化分を含む)**
- ~~Q22 共通 FPC 極先端形状~~ → **極専用 PCB 廃止**。極先端 hex も truncate せず共通 FPC に含む (80 LED/cassette)
- ~~Q25 極 PCB の LED 配置~~ → **極専用 PCB 廃止により無効**
- ~~Q23~~ → 小型ポゴピン圧着確定(極側は廃止、赤道のみ)
- ~~Q24~~ → 同 Gerber + 別 populate 確定(極 PCB 廃止により無効)
- ~~Q26~~ → 南極=磁気端子/北極=装飾蓋 (LED 無し、案 K_new)
- ~~Q30~~ → **5 ストリップ (各 160 = 80×2) 確定**(極ストリップ廃止)

</open_questions>

## References

- [`../CLAUDE.md`](../CLAUDE.md) — プロジェクト共通の前提
- [`10pieces-isolation-sphere-concept.md`](10pieces-isolation-sphere-concept.md) — 一次資料
- [`01-shell-cad.md`](01-shell-cad.md) — 上流: LED 座標 producer (`shared/led_positions.csv`)

### 旧版資料 (V1 試作) / Legacy reference

- **一次置き場 (iCloud)**: `/Users/katano/Library/Mobile Documents/com~apple~CloudDocs/work/isolation-sphere/`
  - 過去の FPC 設計試作 (`kiban/` 配下: `FPC-head-all`, `FPC-side-all`, `penta-WS2812`, `pentagon-remesh-*`, `Power_BQ24616*`, 他)
  - トップレベル: `flatten.py` (球面 → 平面展開), `generate_face_connection.py` (面接続生成), 関連 CSV (`head-*.csv`, `side-all.csv`, `tri_*.csv`, `pentagons.csv` 等)
- **バックアップ**: Python スクリプトのみ [`../fpc-kicad/legacy/`](../fpc-kicad/legacy/) にディレクトリ構造を保持してコピー済 (`*.py` だけ)。CSV / Gerber / 3D モデルは iCloud 側を都度参照。
- ⚠️ V2 では Goldberg T=81 単一形状なので、V1 の `FPC-head` (北極星形) と `FPC-side` (側面六角) を分けていた設計は採用しない。配置スクリプトの考え方 (`place_from_csv.py`, `kicad_tools.py`) は流用候補。
