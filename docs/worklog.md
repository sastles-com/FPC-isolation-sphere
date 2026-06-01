# 作業ログ / Work Log

設計・実装の経緯と判断を時系列で記録する。
詳細な設計仕様は各 `docs/NN-*.md` を参照すること。

---

## 2026-05-31

### リポジトリ初期化・Goldberg ジェネレータ

**作業内容**
- `uv` + Python 3.11 でプロジェクト環境を構築
- `shell-cad/scripts/goldberg.py` を実装
  - Goldberg G(m,0) 多面体を numpy のみで生成（Blender アドオン不使用）
  - 正二十面体 → 測地線細分 → 双対変換 の 3 ステップ構成
  - T=81 (m=9) で頂点 1620、面 812（五角形 12 + 六角形 800）を確認
- Blender Python スクリプトで T=81 メッシュを可視化・カセット着色確認
  - 赤道 (Z=0) をまたぐ面が 90 枚あることを確認 → 赤道カットの必要性を検証

**判断**
- Blender アドオン版と numpy 版を比較し、numpy 版に統一（再現性・CI 容易性）
- 赤道を面が横断しないよう多面体の向きを固定

---

### 案 K_new への設計変更

**作業内容**
- CLAUDE.md を更新：極ねじ方式（案 K1）を廃止し、非極ペンタゴン位置 × 10 の  
  M2.5 ねじ分散クランプ方式（案 K_new）を確定仕様として記載

**判断**
- 極ねじ廃止により応力集中がほぼ解消、極部は端子・装飾専用に降格
- TPU ガスケット・皿ばねは必須 → オプションに降格

---

### ヘキサゴン錐ジェネレータ (`hex_pyramids.py`)

**作業内容**
- `shell-cad/scripts/hex_pyramids.py` を実装
  - 各ヘキサゴン面から六角錐（頂点7・三角形10）を生成
  - `--base_r`：底面を任意半径にスケール（例: 52mm で球面より外に出す）
  - `--l_h`：錐の深さ（頂点を原点方向へ押し込む距離）
  - `--bevel`：単一セグメント頂点 bevel（面取り）
    - bevel あり: 頂点 24・三角形 44 に増加
    - Apex 頂点 → 六角形キャップ
    - 各 Base 頂点 → 三角形キャップ
    - 各 Side 面 → 六角形パネル
    - Base 面 → 12 角形
  - 出力: `.obj`（グループ付き）または `.stl`（ASCII）を拡張子で自動切替

**バグ修正（後日判明）**
- 初期実装では全面の法線が内向き（裏返し）だった
- `_pyramid_plain`：side / base のワインディングを反転
- `_pyramid_beveled`：side panels / base vertex caps / inset base の  
  3 グループのワインディングを反転（apex cap は正しかった）
- 検証: manifold3d で `volume > 0` になることを確認してから Boolean に使用

---

### Web 公開インフラ整備

**作業内容**
- `shell-cad/scripts/generate_stl_viewer.py`
  - Three.js r134 CDN + STLLoader + OrbitControls を使った  
    スタンドアロン HTML ビューアを生成
  - STL と HTML を同ディレクトリに出力し、相対 URL で参照
  - HUD にバウンディングボックス寸法（mm）とポリゴン数を表示
- `shell-cad/scripts/upload_to_lolipop.sh`
  - `.ftp_credentials`（gitignore 済）から認証情報を読み込み
  - `web/output/` 以下の `.html` `.stl` を curl で FTP アップロード
- `.ftp_credentials.example` をテンプレートとしてコミット
- CLAUDE.md §9 に Web 公開ワークフローを追記

**セキュリティ対応**
- FTP パスワードを CLAUDE.md に直書きしないようリファクタ
- `.ftp_credentials` と `web/output/` を `.gitignore` に追加

---

### アパーチャ Boolean デモ (`aperture_boolean_demo.py`)

**作業内容**
- `shell-cad/scripts/aperture_boolean_demo.py` を実装
  - **球殻**（icosphere R_OUTER − R_INNER）から  
    **六角錐 × 800 + 円柱ボア × 800** を Boolean 差分で除去
  - バックエンド: manifold3d（Blender "Exact" Boolean と同エンジン）
  - `Manifold.compose()` で 1600 カッターを高速マージ → 1 回の Boolean 差分
  - 全球 800 穴: **約 14 秒**（FTP アップロード込み）で完了
  - `--cassette 0〜9` で 1 カセット分のみ生成可能

- **Boolean の順序について（設計判断）**
  - 数学的にはどちらが先でも結果は同じ（Union of cutters）
  - 実用上は「大きい錐を先に引き、細い円柱を後」が安定
  - 最も安定: カッターを先に Union し、1 回の差分で切る → 採用

- **パラメータをスクリプト先頭に集約**（チューニング容易化）

```python
R_OUTER     = 52.0   # 外殻半径 mm
R_INNER     = 47.0   # 内殻半径 mm
L_H         =  8.0   # 錐深さ mm
BEVEL       =  0.0   # 面取り mm
CYL_R       =  1.2   # ボア半径 mm
CYL_ENABLE  = True
SPHERE_SUBS =  5
CYL_SECTS   = 16
```

**バグ発見と修正**
- 初回実装では穴が開かず、逆に球面が膨らんでいた
- 原因: `pyramid_manifold` の面ワインディングが内向き → `volume < 0`  
  → Boolean `-` が差分ではなく加算として動作
- 修正: `hex_pyramids.py` の `_pyramid_plain` / `_pyramid_beveled` のワインディングを修正
- 検証コマンド:
  ```python
  pyr = Manifold(Mesh(...))
  assert pyr.volume() > 0   # 正なら外向き法線
  ```

---

### 生成成果物（公開 URL）

| STL | HTML ビューア |
|---|---|
| 全球 800 穴 | http://tajmahal.mond.jp/isolation-sphere/web/output/aperture_demo_fullsphere_viewer.html |
| カセット 0 のみ | http://tajmahal.mond.jp/isolation-sphere/web/output/aperture_demo_cassette0_viewer.html |
| ヘキサゴン錐（面取り 0.5mm） | http://tajmahal.mond.jp/isolation-sphere/web/output/hex_pyramids_l5_b0.5_viewer.html |

---

## 2026-06-01

### カセット生成パイプライン拡張 (`blender_make_cassettes.py`)

**作業内容**
- 10 カセットを `Cassettes` コレクションに集約
- 800 六角錐(ラッパ穴ウェル)を `HexPyramids` オブジェクトとして追加
- 全 12 ペンタゴンを別オブジェクト化し `Pentagons` コレクションへ(非極10 + 極2、カセットは無変更で重ねる)
- **スクリプト自己埋め込み規約**: `.blend` の Scripting タブに CORE + `script_*.py` を自動 glob 埋め込み(`script_<名前>.py` を置くだけで自動収録)

### 新規スクリプト

- `blender_face_cylinder.py` — 指定 pent/hex 面へ原点から放射する円柱(object origin = (0,0,0))
- `script_pent_cylinders.py` — 全ペンタゴン位置に個別円柱(h=1, Φ2.5, 16分割)
- `script_place_on_pentagons.py` — 北極のアクティブオブジェクトを最短弧回転で全12ペンタゴンへ複製配置

### マザーリング + カセット裏面構造の設計確定

**作業内容**
- `blender_make_cassettes.py` に **MotherRing**(赤道ドーナツ PCB、z=0、t=2.0mm、Φ88)を追加
- 裏面構造の用語・方針を doc 化(`inner_deck` / `back_gore` / `ring_claw` / `anchor_post`)

**判断**
- FPC 固定 = **ハイブリッド**(赤道近傍 back_gore 機械面圧 + 残りアセテートテープ)
- inner_deck / back_gore は **FPC 後付けのため別パーツ**(anchor_post にスナップ + 反力点ネジ)
- マザーリング厚 = **2.0mm**(1.6mm 比 剛性 ~1.95倍、ポゴ荷重でたわまない)
- FPC 実装面: **表 WS2812C-2020 / 裏 0603 チップコンデンサ** → back_gore は 0603 逃がし必須

---

## 2026-06-02

### FPC データチェーン + 展開図 (`generate_fpc_chain.py`)

**作業内容**
- 上流から取り込んだチェーン生成器を **polyhedral unfold(多面体展開)** に刷新
  - **一筆書き**: Warnsdorff 順 + バックトラック DFS で start/end 指定の Hamiltonian path を確実探索
  - 既定端点: **DIN = 赤道中央 hex / DOUT = その面隣接**(中央・隣接でポゴ引き出しを集約)
  - **展開**: カセット内側は多面体(平らな hex 面)なので、チェーンに沿って共有辺をヒンジに 180° 展開 → **歪みゼロ**(実測 max 0.27%)
  - **2段ワークフロー**: Warnsdorff 素案 → `legend` CSV 手修正 →`--legend` で再展開(Phase 2 で Blender モーダル・クリック順エディタを予定)
  - **骨組み FPC 外形**: island 円(r=2.25mm)+ チェーン連結帯(w=3.0mm)→ PNG + KiCad 用 SVG 出力

**判断**
- 投影法(equirect/sinusoidal)は**不採用** — 滑らかな球前提。多面体なら投影せず**完全展開(歪みゼロ)**が可能(ユーザー指摘)
- 曲率は除外された pentagon に集中するため、hex のみの半ゴアはほぼ完全平面に展開できる
- inner_deck パッド数 = **4 (GND/5V/DIN/DOUT)** に確定(DIN/DOUT 両方が赤道側に出るため)

### リポジトリ整理

- 再生成成果物の出力先を **トップレベル `output/`(gitignore)** に新設・移設(`shell-cad/output` はシェル専用、`shared/` は手編集設計データ)
- 設計画像を `docs/images/` に追加(マザーリング想定形状 / V1 骨組み FPC 試作実物)
- Q 番号衝突を解消(fpc チェーン系を Q62〜)、CLAUDE.md §2.4/2.5/2.6 と各 doc を整合

---

## 今後の作業 / Next Steps

- [ ] アパーチャパラメータのファインチューニング（穴径・深さ・面取り）
- [ ] 赤道カット + カセット分割の Boolean 実装
- [ ] 外殻裏面の FPC 位置決めピン・ポゴピンボックス形状の追加
- [ ] サテライトボス（M2.5 クランプねじ座）の追加
- [ ] FPC 骨組み設計（KiCad）
- [ ] `shared/led_positions.csv` の出力（Blender → KiCad インターフェース）
