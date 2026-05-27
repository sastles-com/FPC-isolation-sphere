# Shell CAD — 球体外殻 Blender モデリング

<subproject>
- name: shell-cad
- parent: Isolation Sphere V2
- status: wip
- owner: sastle-com
- depends_on: []
</subproject>

## Scope / この doc が扱う範囲

- T=81 ゴールドバーグ多面体 G(9, 0) の生成スクリプト ([`../shell-cad/scripts/goldberg.py`](../shell-cad/scripts/goldberg.py))
- 外殻 (φ100mm / 殻厚 5mm) のメッシュ化と 10 カセット分割
- 各 LED 位置への円錐窓 (ラッパ穴, ~120°) の Boolean 抜き
- 裏面の構造物 (FPC 位置決めピン / ポゴピンボックス / 南極ネジボス) の追加
- 各カセット用 STL 出力 × 10
- **LED 座標の producer** として `shared/led_positions.csv` を出力 (consumer は fpc-kicad)

## Out of scope / 扱わない範囲

- FPC の KiCad アートワーク → [`02-fpc-kicad.md`](02-fpc-kicad.md)
- ESP32 ファーム → 今回スコープ外 (CLAUDE.md §1, §3 Q2)

## Confirmed decisions / 確定事項

- **多面体**: クラス I Goldberg `G(9, 0)`, T = 81 → 812 面 (12 五角形 + 800 六角形), 1620 頂点, 2430 辺
- **向き**: 5 回対称軸を Z 軸に固定 (北極/南極に五角形 1 個ずつ + 5 longitudinal カセット分割と整合)
- **赤道**: m=9 (奇数) のため **どの面中央も Z=0 上に来ない** (最小 |z| ≈ 2.91 mm = 半径の 5.8%) ✓
  - 90 個の六角形は Z=0 をまたぐが、§4.1 の「赤道フラットカット → 切断面を平面クリーンアップ」で吸収する想定
- **生成手法**: 純 Python (`numpy` のみ) で頂点/面リストを構築 → OBJ 出力 → Blender 手動 import
  - bpy 依存にしないことで CI/単体テストが効く
  - 段階: icosahedron → geodesic subdivide (m=9) → dual
  - **Blender 標準 Icosphere は不可** — subdivisions=N は m=2^(N-1) のみ生成可 (1,2,4,8,16...)。m=9 は power-of-2 でない
  - **Blender 同梱 "Add Mesh: Geodesic Domes" addon は可** だが、デフォルトで **3 回対称軸を Z 軸**に置く → 赤道に face center が乗り §6 ハード規則違反。
    回転補正を入れるくらいなら自前 numpy 実装の方が制御しやすいので不採用
- **出力**: [`../shell-cad/output/goldberg_t81.obj`](../shell-cad/output/) (gitignore 対象)
- **LED 総数**: 810 = 10 五角形 + 800 六角形 (極の 2 五角形を除外)
  - 上 ring 5 + 下 ring 5 + 各カセット = 1 pentagon + 80 hexagon = 81 LED/cassette ✓ きれいに割れる
  - 極穴 (北/南) は南極ねじボス・配線スリットに転用予定
- **ラッパ穴形状の基本形**: 角錐台 (pyramidal frustum)
  - 底面 = hex/pent 面そのまま (中央 LED 軸 = 面の法線)
  - 深さ ≤ 1.5 mm (内接円半径 / tan(60°) から逆算)、残り殻厚 ~3.5 mm
  - Bevel/エッジ処理は step-by-step で後段 (Boolean → bevel modifier or post-edge bevel)
- **Boolean 手段**: Blender (Exact solver)。**812 個の錐を 1 メッシュに union してから 1 回の diff で殻に開ける** 戦略 (個別 Boolean は破綻リスクが累積)
  - 破綻時のフォールバック: CadQuery (OpenCASCADE)、`uv add cadquery` で導入

## Open questions / 未確定事項

- Q1: **赤道部の六角形 90 個の処理方式** — 4 案あり (A: 元中心固定でトリム / B: トリム後重心 / C: 90 個捨て / D: 上下 2 分割)。**Blender で目視してから決める** ([`../shell-cad/output/goldberg_t81.blend`](../shell-cad/output/) で赤強調済)
- Q2 細目: **ラッパ穴の bevel 量、角錐 → 円錐への滑らかな fillet を入れるか**
- Q4: **LED 座標 CSV のスキーマ** (`shared/led_positions.csv`):
  - 必須項目候補: `face_id`, `cassette_id (0..9)`, `serial_index (0..809)`, `x, y, z` (球面), `normal_x, normal_y, normal_z`, `hemisphere (N/S)`, `face_kind (pent/hex)`
  - V1 の `tri_hexagon_centroids.csv` 相当を拡張する形になる

## References

- [`../CLAUDE.md`](../CLAUDE.md) — プロジェクト共通の前提
- [`10pieces-isolation-sphere-concept.md`](10pieces-isolation-sphere-concept.md) — 一次資料
- [`02-fpc-kicad.md`](02-fpc-kicad.md) — 下流: LED 座標 consumer

### スクリプト

- [`../shell-cad/scripts/goldberg.py`](../shell-cad/scripts/goldberg.py) — **本採用** G(m, 0) generator (pure numpy)
  - 実行: `uv run python shell-cad/scripts/goldberg.py [-m 9] [-r 50]`
  - 出力 OBJ は Blender > File > Import > Wavefront (.obj) で開ける
  - もしくは CLI: `/Applications/Blender.app/Contents/MacOS/Blender shell-cad/output/goldberg_t81.obj`
- [`../shell-cad/scripts/blender_goldberg.py`](../shell-cad/scripts/blender_goldberg.py) — **参考用** Blender addon (Geodesic Domes) 版
  - 実行: `/Applications/Blender.app/Contents/MacOS/Blender --background --python shell-cad/scripts/blender_goldberg.py`
  - 3 回対称軸が Z にくる仕様で§6 違反するため非採用。Blender addon の挙動確認用に保持
- [`../shell-cad/scripts/compare_obj.py`](../shell-cad/scripts/compare_obj.py) — 2 つの OBJ を不変量 (頂点数 / エッジ長分布 / 面積 / 赤道クリアランス) で比較
  - 実行: `uv run python shell-cad/scripts/compare_obj.py A.obj B.obj`
- [`../shell-cad/scripts/blender_visualize_t81.py`](../shell-cad/scripts/blender_visualize_t81.py) — **Step 1a**: 面種別で色分け (青=12 pent / 灰=710 通常 hex / 赤=90 赤道またぎ hex) + Z=0 wireframe
  - 実行: `/Applications/Blender.app/Contents/MacOS/Blender --background --python shell-cad/scripts/blender_visualize_t81.py`
  - 出力: `shell-cad/output/goldberg_t81.blend` (gitignore)
- [`../shell-cad/scripts/blender_visualize_cassettes.py`](../shell-cad/scripts/blender_visualize_cassettes.py) — **Step 1b**: カセット (10 ハーフゴア) で色分け。色相=経度スライス×5, 明暗=N/S 半球。極の 2 pentagon は白で別カテゴリ
  - 実行: `/Applications/Blender.app/Contents/MacOS/Blender --background --python shell-cad/scripts/blender_visualize_cassettes.py`
  - 出力: `shell-cad/output/goldberg_t81_cassettes.blend` (gitignore)
  - 経度スライス境界: θ = 18°, 90°, 162°, 234°, 306° (pentagon 中心を避ける配置)
