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

## 今後の作業 / Next Steps

- [ ] アパーチャパラメータのファインチューニング（穴径・深さ・面取り）
- [ ] 赤道カット + カセット分割の Boolean 実装
- [ ] 外殻裏面の FPC 位置決めピン・ポゴピンボックス形状の追加
- [ ] サテライトボス（M2.5 クランプねじ座）の追加
- [ ] FPC 骨組み設計（KiCad）
- [ ] `shared/led_positions.csv` の出力（Blender → KiCad インターフェース）
