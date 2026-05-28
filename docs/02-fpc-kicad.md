# FPC KiCad — 骨組み FPC アートワーク

<subproject>
- name: fpc-kicad
- parent: Isolation Sphere V2
- status: draft
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

## Open questions / 未確定事項

<open_questions>
- **Q22: 共通 FPC 極先端の形状** — 台形 (水平 truncate) か五角形 1/5 (ペンタゴン分割形) か。後者なら極 PCB との嵌合がタイト
- **Q23: カセット FPC ⇔ 極 PCB の接続方式** → **案 b 小型ポゴピン圧着で確定**
- **Q24: 極 PCB の南北共通化** → **案 ii 同 Gerber + 別 populate で確定**
- **Q25: 極 PCB の LED 5 個配置** — ペンタゴン頂点位置 (推奨、ヘキサゴンと整合) / 別レイアウト
- **Q26: ペンタゴン中央位置** → 南極=端子レイヤー / 北極=純粋 5 LED (案 K_new で中央ねじなし、確定)
- **Q15, Q17 (端子・磁石)** は [`03-power-charging.md`](03-power-charging.md) に集約
- **Q3: ポゴピンピッチ** (極 PCB 側も赤道側と統一すべきか)

**クローズ済み**
- ~~Q30 極 PCB ⇔ カセット FPC のデータチェーン接続トポロジー~~ → 5 × 158 + 1 × 10 の 6 ストリップで確定
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
