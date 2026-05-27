---
name: new-subdoc
description: Scaffold a new docs/NN-<slug>.md sub-project file for Isolation Sphere V2 and register it in CLAUDE.md §8.1 index. Use when the user wants to start a new sub-project (3D CAD, FPC, firmware, jig, etc.) or types /new-subdoc <slug>.
---

# new-subdoc — Sub-Project Doc Scaffolder

Isolation Sphere V2 プロジェクトで新しい小プロジェクト用 markdown を `docs/` に追加し、`CLAUDE.md §8.1` の索引テーブルにも 1 行登録する。

This skill is the canonical way to start a new sub-project doc in this repo. Do not hand-create `docs/NN-*.md`; always use this skill so the index stays in sync.

## Invocation

```
/new-subdoc <slug>
/new-subdoc <slug> "<short title>"
```

- `<slug>` … kebab-case (lowercase letters / digits / hyphens). 例: `3d-cad`, `fpc-kicad`, `firmware-esp32`
- `<short title>` … optional. 指定なければ slug を humanize して H1 にする。

## Instructions

### Step 1: Validate inputs / 入力検証

<rules>
- slug が `^[a-z0-9]+(-[a-z0-9]+)*$` にマッチするか確認。
- マッチしなければ **停止して** ユーザーに再入力を求める。**推論で勝手に変換しない**。
- `<short title>` 未指定なら slug の `-` をスペースに置き換えて title case にしたものを採用。
</rules>

### Step 2: Pick next NN / 連番採番

<numbering>
- `docs/` 配下を `ls` し、`^[0-9]{2}-.*\.md$` にマッチするファイルから最大の `NN` を抽出。
- 次の番号 = `max(NN) + 1`、ゼロ詰め 2 桁。
- 例外: `10pieces-isolation-sphere-concept.md` は `00` 扱いだが NN スロットを消費しないため無視。
- 初回 (該当無し) は `01` を採用。
</numbering>

### Step 3: Collision check / 衝突確認

<rules>
- `docs/NN-<slug>.md` が既に存在する場合は **絶対に上書きしない**。
- 同名 slug を持つ既存 doc がある場合は停止し、別 slug を提案するかリネームするかをユーザーに確認。
</rules>

### Step 4: Ask for metadata / メタデータ確認

ユーザーに以下を必ず聞く (推論禁止):

1. **owner** … 担当者名 (デフォルト無し、必須)。
2. **depends_on** … 他サブ doc の slug 配列 (空でも可)。
3. **one-line summary** … `CLAUDE.md §8.1` テーブルに入れる 1 行説明 (日本語可)。

### Step 5: Create docs/NN-<slug>.md

`Write` ツールで以下のテンプレを書き出す。テンプレは `CLAUDE.md §8.3` と一致させること。

```markdown
# <Title>

<subproject>
- name: <slug>
- parent: Isolation Sphere V2
- status: draft
- owner: <OWNER>
- depends_on: [<DEPENDS_ON or empty>]
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
```

### Step 6: Update CLAUDE.md §8.1 index

1. `Read` で `CLAUDE.md` を読む。
2. `## 8.1 Index` の直下にあるテーブルを探す。
3. プレースホルダー行 `| — | — | — | — | _(未作成。…)_ |` があれば、その **直前** に新規行を `Edit` で挿入。プレースホルダー自体は残す。
4. プレースホルダーが既に無ければ、テーブルの最後のデータ行の **直後** に挿入。
5. 挿入する行:

   ```
   | NN | <slug> | [docs/NN-<slug>.md](docs/NN-<slug>.md) | draft | <one-line summary> |
   ```

<rules>
- NEVER `CLAUDE.md` の §8.1 以外を編集する。
- NEVER 既存行を書き換える (追加のみ)。
- 同じ slug の行が既に存在する場合は停止 (Step 3 で防ぐが二重チェック)。
</rules>

### Step 7: Report to user / 完了報告

XML タグで構造化して報告 (`CLAUDE.md §5.1` 準拠):

```
<result>
- Created: docs/NN-<slug>.md
- CLAUDE.md §8.1 に行を追加:
  | NN | <slug> | ... | draft | <summary> |
</result>

<next_steps>
1. docs/NN-<slug>.md の Scope / Out of scope を埋める
2. 確定事項が出たら status を draft → wip → stable に更新する
3. 終わったら `/code-review` で差分レビュー
</next_steps>
```

## Hard rules / 厳守事項

<hard_rules>
- NEVER 既存ファイルを上書きする。
- NEVER owner を推論で埋める。必ずユーザーに聞く。
- NEVER `CLAUDE.md` §8.1 以外を触る。サブ doc の詳細は CLAUDE.md には書かない (§8.2)。
- ALWAYS 日英併記 (英語見出し + 日本語本文) のトーンを保つ。
- ALWAYS 長い応答は `<plan>` `<result>` `<next_steps>` などの XML タグで章立てする。
- ALWAYS 入力検証と衝突チェックは Step 5 (ファイル作成) より前に完了させる。
</hard_rules>

## Notes

- このスキルは **CLAUDE.md §8 のルールをコードレベルに落とした実装** である。CLAUDE.md §8 が変わったらこの SKILL.md も合わせて更新すること。
- ただし実行時には **CLAUDE.md §8.1 のテーブルを必ず再読み込み** してから行を挿入する (このファイルの内容に依存して索引を再構築しない)。
