# Isolation Sphere V2

直径 100 mm の球体 LED ディスプレイ。約 800 個の WS2812-2020 を  
**ゴールドバーグ多面体 T=81** の球面に配置した "デジタル地球儀" 風ピクセルディスプレイ。

**A 100 mm spherical LED display with ~800 WS2812-2020 pixels  
arranged on a Goldberg polyhedron (T=81) shell.**

---

## コンセプト / Concept

前作はスパイラル配線＋接着剤固定で LED 1 個の故障が全損につながる設計だった。  
V2 では **カセット交換式・接着剤ゼロ** に全面刷新する。

> V1 was glued together — a single dead LED bricked the sphere.  
> V2 makes every section a **hot-swappable cassette with zero adhesive**.

| 項目 | 仕様 |
|---|---|
| 外径 | φ100 mm |
| 多面体 | Goldberg G(9,0)、T=81 |
| LED | WS2812-2020 × **800 個** |
| 分割 | 経度 5 × 南北 2 = **10 カセット** |
| コントローラ | ESP32 系（6 並列 RMT/PIO 出力） |
| バッテリ | LiPo 2000 mAh × 2 |

---

## 現在のフェーズ / Current Phase

**概念設計 + 3D CAD スクリプト開発中**

- [x] Goldberg T=81 メッシュ生成（`goldberg.py`）
- [x] カセット分割・可視化（Blender Python）
- [x] ヘキサゴン錐 + 円柱アパーチャの Boolean 生成（`aperture_boolean_demo.py`）
- [ ] カセット外殻 STL 完成
- [ ] FPC（骨組み基板）KiCad 設計
- [ ] 極専用 Rigid PCB × 2
- [ ] 赤道マザーリング基板
- [ ] ファームウェア（ESP32）

---

## 3D ビューア / 3D Viewer

生成した STL を Lolipop サーバーで公開中：

| モデル | URL |
|---|---|
| 全球アパーチャ | http://tajmahal.mond.jp/isolation-sphere/web/output/aperture_demo_fullsphere_viewer.html |
| カセット 0 のみ | http://tajmahal.mond.jp/isolation-sphere/web/output/aperture_demo_cassette0_viewer.html |
| ヘキサゴン錐（面取りあり） | http://tajmahal.mond.jp/isolation-sphere/web/output/hex_pyramids_l5_b0.5_viewer.html |

---

## セットアップ / Setup

```bash
# Python 3.11 + uv が必要
uv sync
```

---

## スクリプト一覧 / Scripts

### `shell-cad/scripts/goldberg.py`
Goldberg G(m,0) 多面体ジェネレータ。T=81 メッシュを OBJ で出力。

```bash
uv run python shell-cad/scripts/goldberg.py        # T=81, r=50mm
uv run python shell-cad/scripts/goldberg.py -m 3   # T=9
```

### `shell-cad/scripts/hex_pyramids.py`
各ヘキサゴン面から LED アパーチャ用の六角錐を生成。OBJ / STL 出力。

```bash
uv run python shell-cad/scripts/hex_pyramids.py --l_h 5 --bevel 0.5 --base_r 52
```

| パラメータ | 説明 |
|---|---|
| `--l_h` | 錐の深さ mm |
| `--bevel` | 辺の面取り mm（0=シャープ） |
| `--base_r` | 底面を配置する半径 mm |

### `shell-cad/scripts/aperture_boolean_demo.py`
球殻から六角錐 + 円柱ボアを Boolean 差分で除去した STL を生成。  
スクリプト先頭のパラメータブロックで形状をチューニングできる。

```bash
uv run python shell-cad/scripts/aperture_boolean_demo.py            # 全球
uv run python shell-cad/scripts/aperture_boolean_demo.py --cassette 0  # 1カセットのみ
```

**チューニングパラメータ（スクリプト先頭）:**

```python
R_OUTER     = 52.0   # 外殻半径 mm
R_INNER     = 47.0   # 内殻半径 mm  (差 = 壁厚)
L_H         =  8.0   # 錐の深さ mm
BEVEL       =  0.0   # 面取り mm
CYL_R       =  1.2   # ボア半径 mm
CYL_ENABLE  = True   # False で円柱を無効化
SPHERE_SUBS =  5     # 球メッシュ細分割数
CYL_SECTS   = 16     # 円柱多角形分割数
```

### `shell-cad/scripts/generate_stl_viewer.py`
STL → Three.js インタラクティブ HTML ビューアを生成。

```bash
uv run python shell-cad/scripts/generate_stl_viewer.py shell-cad/output/foo.stl
```

### `shell-cad/scripts/upload_to_lolipop.sh`
`web/output/` 以下を Lolipop FTP サーバーへアップロード。  
認証情報は `.ftp_credentials`（gitignore 済）に記載。

```bash
bash shell-cad/scripts/upload_to_lolipop.sh           # 一括
bash shell-cad/scripts/upload_to_lolipop.sh path/to/file.html  # 単ファイル
```

---

## フォルダ構成 / Repository Layout

```text
.
├── CLAUDE.md                    Claude Code 用プロジェクトガイド
├── docs/
│   ├── 10pieces-isolation-sphere-concept.md  設計議論ログ（一次資料）
│   ├── 01-shell-cad.md          外殻 CAD 仕様
│   ├── 02-fpc-kicad.md          FPC / Rigid PCB 仕様
│   └── 03-power-charging.md     電源・充電仕様
├── shell-cad/
│   └── scripts/                 Python 生成スクリプト群
├── fpc-kicad/
│   └── legacy/                  V1 KiCad スクリプト（参照用）
├── shared/                      Blender ↔ KiCad 共有データ（LED座標 CSV）
└── web/output/                  生成 HTML + STL（gitignore）
```

---

## ライセンス / License

Private repository — Yasuo Katano
