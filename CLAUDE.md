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
- **What / なに**: 直径 100 mm の球体 LED ディスプレイ「Isolation Sphere V2」。 約 810 個の WS2812-2020 を球面に並べた "デジタル地球儀" 風ピクセルディスプレイ。
- **A 100 mm spherical LED display ("Isolation Sphere V2") with ~810 WS2812-2020 pixels covering a Goldberg polyhedron shell.**
- **Why this revision / 今回の改修動機**: 前作はスパイラル配線+接着剤固定でメンテ不可だった。LED 1 個の故障で全損する設計を、**カセット交換式 + 接着剤ゼロ** に作り直す。
- **The previous build was glued together and a single dead LED bricked the whole sphere. V2 makes every section a hot-swappable cassette with zero adhesive bonds.**
- **Repo state / 現状**: 概念設計フェーズ。コードはまだ無く、`docs/` の議論ログのみ。今後 Blender Python と KiCad で実装に入る。
</project>

---

## 2. Confirmed Hardware Topology / 確定したハードウェア構成

### 2.1 Sphere geometry / 球体ジオメトリ

<geometry>
- 多面体: **ゴールドバーグ多面体 T=81** (Goldberg polyhedron, class T=81)
- 外径 φ100 mm / 内径 φ95 mm / 殻厚 **5 mm**
- 総ピクセル数: ~810 (LED は **赤道 Z=0 上には配置しない**。赤道を挟んで北/南に逃がす千鳥配置)
- LEDs are deliberately offset from the equator so the equator slice is reserved for pogo-pin contacts only.
</geometry>

### 2.2 Cassette structure / カセット分割

<cassettes>
- 経度方向 **5 分割** × 南北半球で2分割 = **10 個のハーフゴア・カセット**
- 各カセット = 3D プリント外殻 + 骨組み FPC (81 LED 相当)
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

### 2.4 FPC design — "骨組み (skeleton)" 形状

<fpc>
- 形状: **LED ごとの円形ランド (island) を細い帯 (bridge) で数珠繋ぎ** にしたスケルトン形状 (≠ ベタ三角ゴア)。
- メリット: 3D 球面に追従しやすく反発力が小さい / 熱が中空内部へ抜ける / 肉抜き部分から外殻と直接シールできる。
- 1 種類の Gerber データを 10 枚発注して全カセットに使い回す前提 (端子は左右対称配置)。
- **Single Gerber design reused for all 10 cassettes. Routing crosses (DOUT→DIN) on the equator motherboard to absorb the mirror flip.**
</fpc>

### 2.5 FPC fixation / FPC の固定方法

<fpc_fixation>
- **接着剤は使わない (zero adhesive)** — 前作の全損トラウマに直結するため絶対禁止。
- 固定法: **アセテートテープ (片面) で FPC ごと外殻裏面を目張り** (両面テープは不要)。
  - 骨組み形状の肉抜き部から、テープの糊が外殻プラスチックに直接接触してロックする。
  - アセテートテープの厚み (~0.2 mm) は球体内部に逃げるため LED 高さに影響しない。
- 必要に応じて外殻裏面に **位置決めピン (突起)** を生やし、FPC の基準穴で位置決め。
- **NEVER 3M両面テープ提案 / NEVER 瞬間接着剤・エポキシ.** これらは過去の失敗履歴。
- **Adhesive-free design. Acetate single-sided tape applied across the FPC back covers both the FPC and the surrounding shell, locking them together through the FPC cutouts.**
</fpc_fixation>

### 2.6 Equator connection / 赤道接続

<equator>
- **外殻側にポゴピン (通常タイプ SMT)、マザーリング側はフラット金パッドのみ。**
  - 過去案 (両端ポゴピン/マザーリング側ポゴピン) は採用しない。
- 外殻内側に **3Dプリント一体成形のポゴピンハウジング (ボックス)** を配置し、そこから垂直下向きにピンが生える。
- マザーリングは **コンポーネント実装ゼロのフラットなドーナツ基板** (表裏に金メッキパッドのみ)。
- 赤道面トポロジー: **外側はゴールドバーグの辺に沿ったジグザグ / 内側 (ボックス底面) は Z=0 水平フラット**。
  - 外側ジグザグが組み立て時の "インロー (位置決めガイド)" を兼ねる。
- 配線: 上下のカセットを **DOUT → DIN** クロス接続し、北1→南1→北2→南2→… の一筆書きで全 ~810 ドットを駆動。
- 圧着メカ: **南極ネジ** を締めるとカセット全体が垂直に押されピンがパッドを押し潰す。
</equator>

### 2.7 Bill of materials (confirmed parts) / 確定 BOM

| 項目 / Item | 確定 / Decided | 備考 / Note |
| --- | --- | --- |
| LED | **WS2812-2020** | 高さ 0.65 mm |
| Controller / マイコン | **ESP32 系** (S3 / C3 など) | Wi-Fi/BLE と LED 制御を兼ねる。具体変種は `<open_questions>` 参照 |
| FPC 固定テープ | アセテートテープ (片面) | 例: 一般電子工作向けアセテートクロステープ |
| 外殻 | 3D プリント、黒 | レジン or 高精度 FDM |
| ポゴピン | 通常 SMT 型 (両端型ではない) | ピッチは未確定 |

---

## 3. Open Questions / 未確定事項

CLAUDE が勝手に決めず、必ず確認すること。
**Do not silently pick a side; ask the user.**

<open_questions>
- **Q1: ポゴピンボックスを外殻にどう固定するか / How to attach the pogo-pin box to the shell.**
  概念ドキュメント【ログ 13】で 3 案併記のまま確定していない。
  - 案 A: インサート・スナップロック (爪 + 溝、ネジレス)
  - 案 B: 極小皿ネジ (M1.4 / M2) を内側から裏留め (推奨候補)
  - 案 C: 外殻+ボックス一体造形 (モノコック)
- **Q2: ESP32 の具体型番 (S3 / C3 / その他)。** Wi-Fi/BLE 要件と PIO/RMT どちらで WS2812 を駆動するかが決まれば自動的に絞れる。
- **Q3: ポゴピンのピッチ (2.54 / 2.0 / 1.27 mm)。** マザーリング基板の設計開始時に確定が必要。
- **Q4: マザーリング基板の電源・データ供給方法。** 概念ドキュメントに明示無し。
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
  5. 外殻裏面に「FPC 位置決めピン」「ポゴピンボックス」「南極ネジボス」を生やす。
- 出力: 各カセット用 STL ファイル × 10 (もしくは共通 1 種類を回転コピー)。

### 4.2 FPC 回路設計 (KiCad)
- ターゲット: 骨組み FPC 1 種類 (Gerber 1 セットを 10 枚発注)。
- 端子配置は **左右対称 (回文)** にして、上下反転問題をマザーリング側クロス配線で吸収。
- LED 配置データは Blender 側スクリプトと共有する (CSV か JSON で頂点座標をやり取り)。

### 4.3 Firmware (ESP32 系)
- WS2812 駆動 + Wi-Fi/BLE 経由のフレーム供給。具体型番は未確定 (Q2)。

### 4.4 リポジトリ規約 / Repository conventions

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
└── shared/                      ★ プロジェクト間インターフェース
    └── led_positions.csv        Blender が producer、KiCad が consumer
```

- **設計知識は `docs/NN-<slug>.md` に集約**。各サブプロジェクトフォルダに CLAUDE.md は置かない (§8.2 重複禁止)。
- `shared/` のファイル仕様 (列定義 / 座標系 / ID 規約) は **producer 側の doc** に書く。
- build artifact (`shell-cad/output/`, `fpc-kicad/fab/`) は中身を gitignore、フォルダ自体は `.gitignore` ファイルで保持。
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
- **ALWAYS** 未確定の寸法・型番・トポロジーが必要な場合は質問する。推論で埋めない。
- **ALWAYS** 概念ドキュメント `docs/10pieces-isolation-sphere-concept.md` を一次資料として参照する (本ファイルはダイジェスト)。
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
| — | — | — | — | _(未作成。下記 §8.2 のルールで増やしていく)_ |

予定している小プロジェクト (まだファイル未作成):
- `01-shell-cad.md` — Blender Python による外殻 (T=81 ゴールドバーグ) モデリング
- `02-fpc-kicad.md` — 骨組み FPC の KiCad アートワーク (1 種共通)
- `03-motherboard-kicad.md` — 赤道フラットドーナツ基板
- `04-firmware-esp32.md` — ESP32 系ファーム (WS2812 駆動 + Wi-Fi/BLE)
- `05-assembly-jig.md` — 組立治具 / カセット交換手順 (該当時)

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
