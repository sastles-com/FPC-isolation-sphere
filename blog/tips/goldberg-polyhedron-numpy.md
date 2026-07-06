---
title: "ゴールドバーグ多面体をnumpyで生成する —— 球面に点を均等配置する"
emoji: "⚽"
type: "tech"
topics: ["Python", "numpy", "幾何学", "3DCAD", "Blender"]
published: false
---

> 球面に点をできるだけ均等に並べたい——そんなときに使える**ゴールドバーグ多面体**を、外部ライブラリなし（numpyのみ）で生成する方法をまとめます。サッカーボールを一般化したような多面体で、球体LEDディスプレイの「800個のLED配置」を決めるのに使いました。

<!-- 画像はZenn連携リポジトリの /images/ に置く。元PNG: output/goldberg_t81.png（render_goldberg_figures.pyで生成） -->
![Goldberg G(9,0) T=81 の多面体。六角形800個が灰色、五角形12個がオレンジ](/images/goldberg_t81.png)
*▲ ゴールドバーグ G(9,0)・T=81。六角形800個（灰）の中心にLEDを置く。五角形は12個（オレンジ）だけ。*

## 球面に点を均等配置するのは難しい

緯度経度のグリッド（地球儀の方眼）で球面に点を並べると、極に近づくほど点が密集します。「球面に N 個の点を均等に」という問題に**完璧な答えはない**のですが、実用的な近似のひとつが多面体の面の中心を使う方法です。

なかでも**ゴールドバーグ多面体（Goldberg polyhedron）**は、

- ほぼすべて**六角形**、わずかに**五角形が12個**だけ
- 六角形の数を増やせば、いくらでも細かく（点を増やせる）

という性質を持ち、サッカーボール（切頂二十面体）を一般化したものです。各面の中心に点を置けば、球面に気持ちよく分散した配置が得られます。

## クラスと面数

ゴールドバーグ多面体は `G(m, n)` という2つの整数でクラスが決まります。今回は最も扱いやすい**クラスI `G(m, 0)`**を使います。`T = m²` として：

| 要素 | 個数 |
| --- | --- |
| 面（合計） | 10·T + 2 |
| ┗ 六角形 | 10·T − 10 |
| ┗ 五角形 | **常に12** |
| 頂点 | 20·T |

五角形が必ず12個になるのは**オイラーの多面体定理**の帰結です。六角形だけでは球面を閉じられず、どうしても12個の五角形が要る。これはサッカーボールが12枚の黒五角形を持つのと同じ理由です。

`m=9` なら `T=81`、六角形は **800個**。これがそのまま「LED 800個」になりました。

## 生成は3ステップ

実装は教科書的な「測地線ドーム → 双対」の手順です。

```text
正二十面体(icosahedron)
   ↓  各三角形をm²個に細分し、球面に投影
測地線ドーム(geodesic dome)
   ↓  各面の重心を新頂点に、頂点まわりに面を集めて新面に
双対(dual)
   ↓
ゴールドバーグ多面体 G(m,0)
```

<!-- 元PNG: output/goldberg_pipeline.png（render_goldberg_figures.pyで生成、図示はm=3） -->
![正二十面体→測地線ドーム→双対（Goldberg）の3ステップ](/images/goldberg_pipeline.png)
*▲ 生成パイプライン（見やすさのため m=3 で図示／実際は m=9）。① 正二十面体 → ② 各三角形を細分して球面投影＝測地線ドーム → ③ 双対をとるとゴールドバーグ多面体。五角形（オレンジ）は元の二十面体の頂点位置に現れる。*

### ステップ1: 正二十面体

ここで**対称軸の向き**を決めておくのが重要です。今回は5回対称軸をZ軸に置きました（北極・南極に五角形が来るようにするため）。

```python
import math
import numpy as np

def icosahedron():
    """5回対称軸をZ軸に置いた単位球の正二十面体 (V:12点, F:20面)"""
    z = 1.0 / math.sqrt(5.0)
    r = 2.0 / math.sqrt(5.0)
    V = np.zeros((12, 3))
    V[0]  = (0.0, 0.0,  1.0)        # 北極
    V[11] = (0.0, 0.0, -1.0)        # 南極
    for i in range(5):              # 上下リング各5点、72°刻み
        th = 2.0 * math.pi * i / 5.0
        V[1 + i] = (r*math.cos(th),              r*math.sin(th),              z)
        V[6 + i] = (r*math.cos(th + math.pi/5),  r*math.sin(th + math.pi/5), -z)
    # F は20枚の三角形（省略）。各面が外向きCCWになるよう winding を揃えておく
    return V, F
```

### ステップ2: 測地線細分

各三角形を重心座標で `m×m` のグリッドに割り、各点を**単位球面へ投影**します（`p / |p|`）。これで二十面体が滑らかな測地線ドームになります。

```python
def geodesic_subdivide(V, F, m):
    new_V, new_F = [], []
    for face in F:
        A, B, C = V[face[0]], V[face[1]], V[face[2]]
        grid = {}
        for i in range(m + 1):
            for j in range(m - i + 1):
                k = m - i - j
                p = (i*A + j*B + k*C) / m
                p = p / np.linalg.norm(p)        # 球面へ投影
                grid[(i, j)] = add(p)            # 重複頂点はマージ
        # 上向き三角形 + （収まるなら）下向き三角形を張る
        ...
    return np.asarray(new_V), np.asarray(new_F)
```

頂点の重複マージは、座標を丸めた tuple をキーにした辞書で吸収します（隣接三角形が辺を共有するため）。

### ステップ3: 双対をとる

測地線ドームの**各面の重心**を新しい頂点とし、元の各頂点のまわりに集まる面の重心を**反時計回り**に並べて新しい面を作ります。これがゴールドバーグ多面体です。

```python
def dual(V, F):
    centroids = np.array([(V[f[0]] + V[f[1]] + V[f[2]]) / 3.0 for f in F])
    centroids /= np.linalg.norm(centroids, axis=1, keepdims=True)

    vert_to_faces = defaultdict(list)
    for fi, f in enumerate(F):
        for v in f:
            vert_to_faces[int(v)].append(fi)

    dual_faces = []
    for vi in range(len(V)):
        n = V[vi] / np.linalg.norm(V[vi])           # 外向き法線
        # 接平面に右手系 (u, v) を作り、まわりの面重心を角度順に並べる
        ref = (0,0,1) if abs(n[2]) < 0.9 else (1,0,0)
        u = np.cross(n, ref); u /= np.linalg.norm(u)
        w = np.cross(n, u)
        adj = vert_to_faces[vi]
        adj.sort(key=lambda fi: math.atan2((centroids[fi]-V[vi]) @ w,
                                           (centroids[fi]-V[vi]) @ u))
        dual_faces.append(adj)
    return centroids, dual_faces
```

元の二十面体の頂点は12個が5価（5枚の面が集まる）、残りは6価。**5価のところに五角形、6価のところに六角形**が現れる、というのが双対の効くポイントです。

## 検証

生成したら、必ず不変量で答え合わせをします。`m=9` の実行結果：

```text
Goldberg G(9, 0)  T = 81  radius = 50.0 mm
  Vertices :  1620   (expected 1620)
  Faces    :   812   (expected 812)
  Pentagons:    12   (expected 12)
  Hexagons :   800   (expected 800)
```

頂点1620・面812（五角形12＋六角形800）。理論値とぴったり一致しました。

## numpyだけで書く利点

最後に、なぜBlenderやCADのアドオンではなく**純Python（numpy）**で書いたか。

- **任意の `m` が作れる**: Blender標準のIcosphereは細分が `m = 2^(N-1)`（1,2,4,8,…）しか作れず、`m=9` は不可能。
- **対称軸を完全に制御できる**: 「5回対称軸をZ軸に」を最初から仕込める（アドオンは3回対称軸がZに来る等、後から回転補正が要る）。
- **bpy非依存**: ふつうのPython環境で動き、単体テスト・CIに乗る。出力はOBJにして後段でBlenderに読ませればよい。

球面に点を均等配置したい用途（LED、センサアレイ、測地線ドーム、惑星のタイル分割など）に広く使える小道具です。

---

*球体LEDディスプレイ「Isolation Sphere V2」制作シリーズの小記事です。プロジェクト全体像と「なぜ作り直すのか（全損トラウマ）」は [**序章（ポータル）**](https://note.com/taj_mahal/n/n34240e8664a7) を参照。*
*関連: この800面を殻にする[Booleanなしで球殻をwatertightに分割する](https://zenn.dev/sastle/articles/d5dfab18aa2500)／800個のLEDを配線する「02 FPC設計」（準備中）。*
