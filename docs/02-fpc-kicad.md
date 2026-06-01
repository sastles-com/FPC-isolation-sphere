# FPC KiCad — 骨組み FPC アートワーク

<subproject>
- name: fpc-kicad
- parent: Isolation Sphere V2
- status: wip
- owner: sastle-com
- depends_on: [shell-cad]
</subproject>

## Scope / この doc が扱う範囲

- **共通骨組み FPC** (10 カセット共通の 1 種類 Gerber) の KiCad アートワーク作成
- **極専用ペンタゴン rigid PCB × 2** (北極・南極) の KiCad アートワーク作成
- LED 配置データ ([`../shared/led_positions.csv`](../shared/led_positions.csv)、shell-cad が producer) からの **自動 LED 配置スクリプト**
- 端子レイアウト (左右対称設計、極 PCB のポゴピン圧着パッド)
- ガーバー出力までの一連の手順

## Out of scope / 扱わない範囲

- 外殻 3D 形状 / 球体コア / pillar → [`01-shell-cad.md`](01-shell-cad.md)
- 磁気端子・LiPo・配線ルート → [`03-power-charging.md`](03-power-charging.md)
- ESP32 ファーム → 別プロジェクト管轄 (CLAUDE.md §1, §3 Q2)
- 赤道マザーリング基板 → 別 doc (`04-motherboard-kicad.md` 予定)

## Confirmed decisions / 確定事項

### アーキテクチャ: 案 S4 + 案 K_new (共通 FPC truncate + 極専用 PCB 分離 + 非極 pent ねじ穴)

- **共通骨組み FPC × 10 枚** (Gerber 1 種、左右対称端子)
  - 各カセット **79 LED** (= 1 ペンタゴン穴を除く hex のみ、極先端 1 LED は極 PCB へ移管)
  - 形状: 円形ランド (LED) + 帯 (ブリッジ) の骨組み (≠ ベタ三角ゴア)
  - **極先端は truncate** — 5 枚合わせると極にペンタゴン形の穴ができ、そこに極専用 PCB が嵌まる
  - **非極ペンタゴン位置に Φ2.7 ねじ通し穴 + M2.5 沈み込み座ぐり** — 案 K_new の M2.5 真鍮意匠ねじ用 (各 FPC に 1 個ずつ)
  - メリット: 球面追従性、熱抜け、テープ糊が外殻と直接シール

- **極専用 rigid PCB × 2** (北極/南極ペンタゴン PCB)
  - 素材: **FR4 (rigid)** — 球面追従不要、剛性重視
  - 各 5 LED (周辺ヘキサゴン位置に整合)
  - 底面に **小型ポゴピン × (4 ピン × 5 カセット = 20 ピン)** を装着 → 各カセット FPC 先端パッドを圧着
  - **南極のみ追加レイヤー**: 端子パッド (VBUS, GND) + マグネット保持穴 (Φ4) (中央ねじ廃止: 案 K_new)
  - **北極**: 純粋な 5 LED 基板
  - **pillar への固定**: スナップ留め (案 K_new で中央ねじ無しが可能)
  - **Gerber 共通化**: 南北で **同じ Gerber、populate だけ変える** (Q24 案 ii 推奨)

- **LED 総数: 800** = 共通 FPC 上 hex 790 (= 79 × 10) + 極 PCB 上 hex 10 (= 5 × 2)
  - **非極 pent 10 個** = ねじ穴 (LED 無し)、**極 pent 2 個** = 構造領域 (LED 無し)

### 配線・データチェーン (6 ストリップ構成)

- 共通 FPC 内のデータチェーンは左右対称端子で **回文構造** (例: `VCC-DIN-GND-DOUT-VCC`)
  - 上下反転問題は赤道マザーリング側のクロスルーティング (`DOUT→DIN`) で吸収
- 極 PCB ⇔ カセット FPC は **小型ポゴピン圧着** (Q23 案 b 確定)
- **6 並列ストリップ構成**:
  - Strip 1-5: 各 longitude slice (北 79 LED → 赤道経由クロス → 南 79 LED = **158 LED each**)
  - Strip 6: 北極 PCB 5 LED → コア内ワイヤ (AWG28-30) → 南極 PCB 5 LED = **10 LED**
  - 合計: 5 × 158 + 10 = **800 LED**
- ESP32 側: **6 並列 PIO/RMT 出力** で各ストリップを独立駆動 (フレームレート 6 倍向上、fault isolation 効果)

### 非極ペンタゴン位置のクランプねじ穴 (案 K_new)

- **位置**: 各共通 FPC に 1 箇所、緯度 ±26.57° の非極 pent 中央
- **穴形状**: Φ2.7 貫通穴 (M2.5 ねじ通し用) + 上面に Φ4.7 × 深さ 1 mm の沈み込み座ぐり (M2.5 真鍮意匠ねじ頭収容)
- **FPC 上の銅配線禁止領域**: 穴周囲 Φ4 mm を keep-out (ねじ頭との短絡防止)
- 共通 FPC が **同じ Gerber × 10** であるため、北 5 + 南 5 の全カセットに同じねじ穴が刻まれる

### LED 配置データの利用

- producer: shell-cad (`shared/led_positions.csv`)
- consumer: KiCad 配置スクリプト (V1 の `place_from_csv.py` 思想を流用)
- 必要列: `board_kind` (fpc / polar_pcb_n / polar_pcb_s), `cassette_id`, `serial_index`, `x, y, z`, `normal_*`, `face_kind` (pent/hex), **`is_screw_hole` (非極 pent のみ true)**

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
  - **含意 (Q65 で確定)**: 1 カセットが赤道側に DIN・DOUT の**データ2端子** → inner_deck は **4 パッド (GND/5V/DIN/DOUT)**
- **Q63 (解決): 展開法 = polyhedral unfold(投影は不採用)** (2026-06-02)
  - カセット内側は**多面体**(平らな hex 面)なので、投影(equirect/sinusoidal)で近似する必要は無く、**チェーンに沿って共有辺をヒンジに 180° 展開**すれば **歪みゼロ**(実測 max 0.27%)
  - 曲率は除外された pentagon に集中 → hex のみの半ゴアはほぼ完全平面に展開
  - equirect/sinusoidal は不採用(滑らかな球前提だった)。測地的最適化は不要
- **Q64: チェーンパターンの規則性** — Warnsdorff vs 列スネーク
  - **Warnsdorff** (現状): 全ブリッジ面隣接 (距離 ≈ 5.3–6.5 mm)、経路は不規則
  - **列スネーク**: 経度列ごとにジグザグ。視覚上整然だが一部ブリッジが面非隣接の可能性
  - 端点を「中央スタート+隣接エンド」に固定する Q62 と整合する経路生成が必要
- **Q65 (NEW): inner_deck パッド数の再確定 (3 vs 4)** — Q62 の「DIN/DOUT 両方赤道」を受けて
  - **3 パッド案**: GND/5V/DATA (各カセット データ1本) — 片端が極側に出る前提でないと不成立
  - **4 パッド案** (★Q62 と整合): GND/5V/DIN/DOUT — 各カセット赤道側に2データ端子
  - 決定後 [shell-cad Q56](01-shell-cad.md) と CLAUDE.md §2.6 / §3 を同期更新
- **Q66 (NEW): KiCad 配置ワークフロー** — legend 手配置 vs CSV スクリプト配置
  - **legend 手配置** (V1 実績): 平面展開図を下絵 (legend) にして KiCad で footprint を手置き
  - **CSV スクリプト配置** (★scope に既存): `generate_fpc_chain.py` の `flat_x/flat_y` + 各 island の向き + チェーン順を pcbnew API で自動配置・自動ブリッジ配線

**既存 open questions**

- **Q22: 共通 FPC 極先端の形状** — 台形 (水平 truncate) か五角形 1/5 (ペンタゴン分割形) か
- **Q25: 極 PCB の LED 5 個配置** — ペンタゴン頂点位置 vs 別レイアウト
- **Q3: ポゴピンピッチ** (極 PCB 側も赤道側と統一すべきか)

**クローズ済み**
- ~~Q23~~ → 小型ポゴピン圧着確定
- ~~Q24~~ → 同 Gerber + 別 populate 確定
- ~~Q26~~ → 南極=端子/北極=5 LED 確定 (案 K_new)
- ~~Q30~~ → 5×158 + 1×10 の 6 ストリップ確定

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
