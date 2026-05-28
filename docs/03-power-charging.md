# Power & Charging — 南極磁気端子 + LiPo + 配線

<subproject>
- name: power-charging
- parent: Isolation Sphere V2
- status: draft
- owner: sastles-com
- depends_on: [shell-cad, fpc-kicad]
</subproject>

## Scope / この doc が扱う範囲

- **南極磁気端子** (Φ4 mm 市販マグネット、2 極接点) の選定・実装
- **LiPo バッテリ** (2000 mAh × 2、合計 ~14.8 Wh) の球体コア内格納仕様
- **AWG26 配線ルート** (南極 PCB → 南極 pillar 内 Φ3 mm 通路 → コア内充電 IC)
- 充電 IC ボード との **インターフェース定義** (コネクタ規格、ピンアサイン)
- 任意姿勢でのマグネットプラグ接続を想定 (クレードルは next step)

## Out of scope / 扱わない範囲

- **充電 IC / バッテリ保護回路 / MCU の回路設計** — 別プロジェクト管轄 (CLAUDE.md §1, §3 Q6)
- 球体コアの 3D 形状・pillar 機構 → [`01-shell-cad.md`](01-shell-cad.md)
- 共通 FPC / 極 PCB の Gerber 設計 → [`02-fpc-kicad.md`](02-fpc-kicad.md)
- USB-C / Wi-Fi / BLE 経由の通信 → 別プロジェクト管轄
- クレードル (充電台) — 任意姿勢手付け方式で進める。クレードルは next step

## Confirmed decisions / 確定事項

### 充電方式

- **任意姿勢** で **手付けマグネットプラグ** を接続する方式
- クレードル (置くだけ充電台) は **作らない** (将来検討は別途)
- 充電中の球は手で持つ / 任意の置き場所に置いた状態 (姿勢不問)

### 磁気端子仕様 (案 K_new で大幅シンプル化)

- **接点数**: **2 ピン (VBUS, GND)** のみ
- データ通信は通さない (USB DM/DP は不要、Wi-Fi/BLE で代替)
- **市販マグネット**: Φ4 mm × 2 極 (具体型番は Open Q17)
- **配置**: 南極キャップ外面に **自由に配置可能** (案 K_new で中央ねじが廃止されたため、極キャップの中央領域がフルに使える)
  - 推奨: **中央付近に Φ4 マグネット 2 個 + 並列接点 2 個** (orientation lock を効かせる非対称配置)
  - キャップ自体はスナップ留め (極ねじなし)
- **北極側**: 端子なし、装飾蓋スナップのみ (機械クランプは 10 個の非極ペンタゴンねじが担当、極ねじ無し)

### バッテリ

- **LiPo 2000 mAh × 2 = 合計 4000 mAh** (~14.8 Wh @ 3.7 V nominal)
- 配置: **球体コア内部** (Q34 で物理配置詳細化)
- 想定セル寸法: 50 × 35 × 10 mm 程度 (角型) を 2 個並列 or 直列 (要確定)

### 配線

- **AWG26 × 2 本** (VBUS, GND)
- ルート: 南極キャップ端子パッド → 南極 PCB → 南極 pillar 内 **Φ3 mm 配線通路** → 球体コア → 充電 IC ボード入力
- 引き抜き式コネクタ (例: JST PH 2pin) でコア内側で接続
- **キャップはスナップ式**: メンテで外した時、配線が突っ張らないよう **長さ余裕 + コネクタによる脱着** を確保

### 充電 IC との境界 (インターフェース定義)

- 本 doc は **「南極端子パッド ⇔ コア入口の AWG26 リード」** までを扱う
- それ以降 (充電 IC、保護 IC、過充電/過放電制御、ESP32 への給電) は別プロジェクト管轄
- インターフェース仕様 (コネクタ規格、最大電流、極性) は要すり合わせ → Q40 で追って詰める

## Open questions / 未確定事項

<open_questions>
**マグネット端子**
- **Q15**: 磁石個数とレイアウト — orientation lock を効かせる非対称 2 個配置 推奨だが要確定
- **Q17**: **具体型番** (AliExpress 等で売っている `2pin Φ4 マグネット端子`)。物理サンプル入手後に寸法引当
- **Q21**: 案 S1 大型キャップ外形は Φ20 程度の見積もりだが、Q15/Q17 確定で逆算

**バッテリ・配線**
- **Q34**: LiPo 2000 mAh × 2 の **物理配置** (コア内、pillar 根本と干渉しないか)
- 配線通路 Φ3 mm の妥当性 (AWG26 × 2 + 余裕で OK だが、シールド要否は未検討)

**充電 IC 境界**
- **Q40 (NEW)**: 充電 IC ボードとのコネクタ規格 — JST PH 2pin / Molex / その他
- **Q41 (NEW)**: 最大充電電流 (LiPo 4000 mAh、0.5C = 2A) を AWG26 × 2 で持つかチェック (AWG26 の安全電流は 2A 程度、ギリギリ)
- **Q42 (NEW)**: 過放電保護のスイッチング位置 (球内 IC 側か、端子直前か)
</open_questions>

## References

- [`../CLAUDE.md`](../CLAUDE.md) — プロジェクト共通の前提、§2.7 BOM と §2.8 Pole assembly
- [`10pieces-isolation-sphere-concept.md`](10pieces-isolation-sphere-concept.md) — 一次資料
- [`01-shell-cad.md`](01-shell-cad.md) — 球体コア / pillar / キャップ機構 (上流)
- [`02-fpc-kicad.md`](02-fpc-kicad.md) — 南極 PCB の端子パッド設計 (関連)
