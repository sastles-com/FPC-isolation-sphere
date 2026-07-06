# 公開チェックリスト（案A: noteポータル + Zenn Book + Zenn小話）

## ⚠ Zennの公開数制限（新規アカウントは要ペース配信）

Zennはスパム対策で **ユーザーごとに動的な投稿上限**を持つ（2024 LLMスパム検出 / 2026-03 AIコンテンツ方針で明文化）。
**新規アカウントは上限が低く**、時間・実績で緩和される。GitHub連携でも一定時間内の投稿数上限あり。

- 実績: 2026-06 時点で新規アカウント `sastle` は **2本公開した時点で上限**（goldberg / cassette）
- 対策: **数日かけて1〜2本ずつ追加**（アカウントが育つと上限UP）／まとめたいなら**上限緩和を申請**
- 公開順（枠が空き次第）: ③ 01シェル本編 → ④ 球面点配置 → ⑤〜 以降の小話・本編
- note序章ポータルは既に2本へリンク済み＝回遊ループは成立。焦らず順次でOK

## Zenn未経験者の最初の一歩（まずWeb editorで1本）

Zennは未経験なので、いきなりGitHub連携せず、**Web editorで小話を1本公開して慣れる**のが安全。

1. **アカウント**: [zenn.dev](https://zenn.dev) → Google/GitHubでサインアップ。ユーザー名を決める（URLになる）
2. **記事を作成**（Web editor）: ダッシュボード →「記事を作成」
   - **本文だけ**貼る（`tips/*.md` の `---` frontmatter は貼らない）
   - 右の欄に手入力 → frontmatterの値がそのまま対応:
     - `title` → タイトル欄 / `emoji` → 絵文字 / `type` → tech|idea / `topics` → トピック（最大5）
   - プレビューでコードブロックの見え方を確認 →「公開」
3. 最初の1本の推奨 = `goldberg-polyhedron-numpy`（単体で完結・コードが映える）
4. 慣れたら下記の **GitHub連携** に移行（Book運用。`articles/`+`books/` をpushするだけ）

> Web editor = 準備ゼロ・単発向き。GitHub連携 = Book/連載・バージョン管理向き（我々の下書き構成がそのまま活きる）。

## 公開の順序（重要：Zenn → note）

noteポータルの §6 目次に Zenn の実URLを差し込むため、**先に Zenn を公開**して URL を確定させる。

1. **Zenn 小話を公開**（いま出せる）: `goldberg-polyhedron-numpy` / `cassette-watertight-no-boolean`
2. **Zenn Book を公開**（章が揃い次第）: 01〜06。最初は 01 だけ free 公開でもよい
3. 取得した Zenn URL を **note版00 の §6 と関連リンク**に差し込む
4. **note ポータル(00) を公開**
5. note↔Zenn の相互リンクを最終確認（各Zenn記事末の「ポータルへ戻る」も実URLに）

## 公開済み / 公開待ち

Zenn ユーザー: **sastle**（https://zenn.dev/sastle）

| 記事 | 媒体 | ファイル | 状態 / URL |
| --- | --- | --- | --- |
| ゴールドバーグ多面体をnumpyで生成 | Zenn記事 | `tips/goldberg-polyhedron-numpy.md` | ✅公開 https://zenn.dev/sastle/articles/4156ddb961e4da |
| Booleanなしで球殻をwatertightに分割 | Zenn記事 | `tips/cassette-watertight-no-boolean.md` | ✅公開 https://zenn.dev/sastle/articles/d5dfab18aa2500 |
| 序章ポータル | note | `00-overview.note.md` | ✅公開 https://note.com/taj_mahal/n/n34240e8664a7 |

> Zenn 2本は公開後に**相互リンク（記事末「関連」）を追記**したので、Web editor側も更新するとリンクが繋がる。

## Zenn GitHub連携のリポジトリ構成（公式仕様）

Zennは**別途Zenn連携リポジトリ**が要る（この設計リポジトリとは別）。構成:

```text
（Zenn連携リポジトリのルート）
├── articles/
│   ├── goldberg-polyhedron-numpy.md   ← tips/ の小話をコピー
│   └── cassette-watertight-no-boolean.md
└── books/
    └── isolation-sphere-v2/
        ├── config.yaml                 ← 雛形: blog/zenn/books/isolation-sphere-v2/config.yaml
        ├── cover.png                   ← 1200×630 程度
        ├── shell-cad-design.md         ← 01（frontmatter は title/free のみ）
        ├── fpc-design.md               ← 02
        ├── assembly-mechanism.md       ← 03
        ├── power-charging.md           ← 04
        ├── firmware-esp32.md           ← 05
        └── server-webui.md             ← 06
```

### frontmatter ルール

- **articles（小話）**: `title` / `emoji`(絵文字1字) / `type`(tech|idea) / `topics`(最大5) / `published`(bool)
  - → `tips/*.md` は既にこの形。`published: true` に変えてコピーすればよい
- **book/config.yaml**: `title` / `summary` / `topics`(最大5) / `published` / `price`(0=無料) / `chapters`(章スラッグを表示順に)
- **章ファイル**: frontmatter は `title` のみ（有料本で無料公開する章は `free: true`）。本文先頭の `# 見出し` は不要

## 画像の扱い

記事の図は matplotlib で生成（再生成可）:

```bash
uv run python shell-cad/scripts/render_goldberg_figures.py
# → output/goldberg_t81.png（ヒーロー）, output/goldberg_pipeline.png（3ステップ）
```

媒体ごとの貼り方:

- **Web editor**: 本文の画像ボタン（🖼）or ドラッグ&ドロップで `output/*.png` をアップロード → Zennホストの画像URLが自動挿入される（下書きの `/images/...` 記法は使わず、挿入されたURLに置き換わる）
- **GitHub連携**: PNG をリポジトリの `images/` に置き、本文から `/images/goldberg_t81.png` で参照（下書きの記法そのまま）。ファイル名はアンダースコア版に統一済み

> 図中ラベルは日本語フォント無し環境でも崩れないよう**英語**。日本語の説明は画像下のキャプション（Markdown）で付けている。

## URL差し替えメモ（公開後に置換する箇所）

- `00-overview.note.md` §6 の本編6章 → Zenn Book 各章URL
- `00-overview.note.md` §6 の小話6本 → Zenn記事URL
- 各 `tips/*.md` 末尾「序章（ポータル）」→ note ポータルの実URL
- `tips/fpc-unfold-howto.md` の note FPC記事参照 → note 既存記事の実URL（要収集）

## まだ書けていない章（Book完成に必要）

- 02〜06 は `blog/0X-*.md` がアウトライン段階 → 本文化が必要
- 01 は本文草稿あり → 仕上げれば最初の公開章にできる
