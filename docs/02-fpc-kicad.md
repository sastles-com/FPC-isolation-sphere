# FPC KiCad — 骨組み FPC アートワーク

<subproject>
- name: fpc-kicad
- parent: Isolation Sphere V2
- status: draft
- owner: sastle-com
- depends_on: [shell-cad]
</subproject>

## Scope / この doc が扱う範囲

- TODO: 何をこの doc で決め切るかを書く

## Out of scope / 扱わない範囲

- TODO: 他 doc に任せる範囲を書く

## Confirmed decisions / 確定事項

- TODO: 1 つも無ければ空でよい

## Open questions / 未確定事項

- Q1: TODO

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
