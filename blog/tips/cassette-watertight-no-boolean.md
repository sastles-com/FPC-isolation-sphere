---
title: "Booleanを使わずに球殻をwatertightに分割する —— 面集合から直接ソリッドを組む"
emoji: "🧩"
type: "tech"
topics: ["Blender", "Python", "3DCAD", "メッシュ", "3Dプリンタ"]
published: false
---

> 多面体の球殻を複数のパーツに分割したい。素直にやるならBoolean（ブーリアン演算）ですが、分割数が増えるとメッシュが破綻しがちです。今回は**Booleanを一切使わず**、面集合から直接watertight（水密）なソリッドを組む方法を紹介します。隣り合うパーツが頂点を完全共有するので、ぴったり噛み合うのも利点です。

## やりたいこと

直径100mmの球体LEDディスプレイの外殻を、**10個の交換式カセット**に分割したい。

- 殻厚5mm（外径φ100 / 内径φ90）の中空球
- 分割線はゴールドバーグ多面体の辺に沿った**ジグザグ**（面の中央を割らない）
- 各カセットは3Dプリントするので**watertight**でなければならない

<!-- 元PNG: output/goldberg_cassettes.png（render_goldberg_figures.pyで生成） -->
![10個のハーフゴア・カセットに色分けした球。経度5×南北2＝10色＋極の五角形2個（白）](/images/goldberg_cassettes.png)
*▲ 10カセットへの分割（経度5スライス × 南北2半球）。境界はゴールドバーグの辺に沿ったジグザグで、面の中央を割らない。極の五角形2個（白）はカセットから除外。*

## Booleanの何が問題か

最初に考えるのは「中空球を作って、カッターで切る」です。が、これは罠があります。

- 中空化（Solidify）＋分割カット（Boolean Diff）を重ねるほど、**メッシュが汚れていく**（自己交差・ゼロ面積面・非多様体エッジ）
- 10分割ぶんBooleanを繰り返すと**破綻リスクが累積**
- 隣接カセットの切断面が微妙にズレ、**組んだとき隙間**ができる

## 発想の転換: 面集合から直接組む

ゴールドバーグ多面体は最初から「面のリスト」を持っています。ならば各面を「どのカセットに属するか」分類し、**割り当てられた面集合から閉じたソリッドを直接組み立てれば**、Booleanは要りません。

ひとつのカセット = 次の3要素でできた閉じたメッシュです。

```text
外殻面 (r=50)  ──┐
                 ├─ rim quad（側壁）でつなぐ
内殻面 (r=45)  ──┘
```

1. **外側**: 割り当てられた面そのもの（r=50、元のCCW巻き）
2. **内側**: 同じ面の頂点を `× 0.9` で r=45 に縮めた面（巻きを反転して法線を内向きに）
3. **側壁（rim quad）**: カセット境界の辺ごとに、外側2点＋内側2点の四角形

### 1. 面をカセットに分類する

重心の緯度経度で振り分けます。Z軸近傍の2枚（極の五角形）は除外（極キャップになる）。

```python
def classify(centroid):
    cx, cy, cz = centroid
    r_axial = math.sqrt(cx*cx + cy*cy)
    hemi = 0 if cz >= 0.0 else 1                # 北 / 南
    if r_axial < POLAR_R_THRESHOLD:             # Z軸近傍 = 極の五角形
        return ("polar", hemi)
    az = math.degrees(math.atan2(cy, cx)) % 360.0
    slice_idx = int(((az + AZ_SHIFT_DEG) % 360.0) // (360.0/N_SLICES)) % N_SLICES
    return (slice_idx, hemi)                     # 経度スライス0..4 × 南北
```

### 2. 外殻・内殻・側壁を張る

肝は**側壁の作り方**です。カセット境界の辺とは「**そのカセット内で1枚の面にしか属さない辺**」のこと。各面の辺を有向で数え、1回しか出てこない辺が境界です。

```python
def build_cassette_solid(V_outer, V_inner, F, face_indices, name):
    # この面集合が使う頂点だけ集めてリマップ
    used = sorted({vi for fi in face_indices for vi in F[fi]})
    remap = {old: new for new, old in enumerate(used)}
    n = len(used)

    verts  = [tuple(V_outer[i]) for i in used]        # 0..n-1   外殻
    verts += [tuple(V_inner[i]) for i in used]        # n..2n-1  内殻

    faces = []
    for fi in face_indices:                            # 外殻面（元の巻き）
        faces.append([remap[vi] for vi in F[fi]])
    for fi in face_indices:                            # 内殻面（巻き反転）
        faces.append([remap[vi] + n for vi in reversed(F[fi])])

    # 境界辺 = この面集合で1回しか現れない辺
    edge_count = defaultdict(list)
    for fi in face_indices:
        f = F[fi]
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            edge_count[tuple(sorted((a, b)))].append((a, b))
    for ab_list in edge_count.values():
        if len(ab_list) == 1:                          # 境界辺だけ側壁を張る
            a, b = ab_list[0]
            faces.append([remap[a], remap[b], remap[b] + n, remap[a] + n])

    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.validate(verbose=False)                       # クリーンを確認
    ...
```

`reversed(F[fi])` で内殻面の巻きを反転し、法線を球の中心向き（＝カセット材料から見て外向き）に揃えているのがポイント。これで外殻・内殻・側壁の法線が全部「材料の外」を向き、watertightなソリッドになります。

## なぜこれで噛み合うのか

この方式の効きどころは、**隣接カセットが境界の頂点を完全に共有する**ことです。両者とも元のゴールドバーグ頂点（同じ座標）から作っているので、切断面が一致し、組んだとき**隙間ゼロ**になります。Booleanで別々に切ると、まずこうはいきません。

さらに副産物として：

- **Solidify / Boolean 不要** → `mesh.validate()` がクリーン、出力は数秒
- 外周のジグザグが、組み立て時の**位置決めガイド（インロー）**を兼ねる
- 全カセットが同じ頂点数・面数（対称配置なので合同）

## まとめ

「中空を作って切る」のではなく「**面集合から閉じたソリッドを直接組む**」。多面体ベースの殻をパーツ分割するなら、Booleanより速く・壊れず・ぴったり合います。境界辺＝1回しか現れない辺、という判定さえ押さえれば実装は素直です。

---

*球体LEDディスプレイ「Isolation Sphere V2」制作シリーズの小記事です。プロジェクト全体像と「なぜ作り直すのか（全損トラウマ）」は [**序章（ポータル）**](https://note.com/taj_mahal/n/n34240e8664a7) を参照。*
*関連: 元になった多面体の作り方[ゴールドバーグ多面体をnumpyで生成する](https://zenn.dev/sastle/articles/4156ddb961e4da)／殻の中身「01 シェル設計」（準備中）。*
