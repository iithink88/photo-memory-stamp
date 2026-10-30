# 提示词母版

三段：**§A 槽位表** → 填槽 → **§B 印章本体提示词**（主用，配 `stampkit.py compose`）。需要一次成整版时用 **§C**。

---

## §A 槽位表（Step 1 的产物）

| 槽 | 填什么 | 反例 / 正例 |
|---|---|---|
| `{SUBJECT}` | 主体，名词堆叠，一句话 | ✗"一张很美的荷花照片" ✓"重檐六角亭 + 单拱石桥 + 满塘荷叶" |
| `{ANCHOR1..3}` | 3-5 个能认出地的结构 | ✗"绿色的叶子" ✓"六角攒尖顶的翘角轮廓" |
| `{DROP}` | 明确要删的元素 | "删掉背景里的白色居民楼和电线；荷叶只留前景 3-4 片大的" |
| `{少量元素数量}` | 简化后的具体数量 | "三片大叶、两支荷苞、四根柱子" |
| `{外形倾向}` | **只写"偏竖长/偏横长"，绝不写"方形/竖长方形"** | ✗"方形外廓"（会被画成边框） ✓"整体偏竖长" |
| `{INK1..3}` | 1-3 个 hex，来自 `palette`；浅色压深一档 | `#2C5813` 深荷叶绿 / `#C9748C` 荷粉 / `#8E9BA6` 石桥青灰（原图 `#D1D9EC` 太浅，必须压深） |
| `{INNER}` | 印章内部文字（可选） | 一行极小大写英文 `LOTUS POND`；不想要就写"不加任何文字"。模型写小字极易糊，默认不加 |
| `{TITLE}` | 2-4 个英文单词，全大写 | `LOTUS POND` / `ORANGE PYLON` / `SUNSET CROSSING` |
| `{KEYWORDS}` | 恰好 3 个，`a / b / c` | `pavilion / arch / lotus` |

---

## §B 印章本体提示词（主用）

把 `{}` 全部替换成实值再发。**中英混排是刻意的**：工艺词用英文（模型对 `linocut`、`letterpress` 的材质先验更准），约束用中文（模型对中文否定句更听话）。

```text
生成一枚孤立的复古手工印章图案。方形画布，背景纯白或透明，画面里只有这一枚印章，没有纸张、没有卡片、没有阴影、没有其他任何东西。

【母题】{SUBJECT}
严格只以上传照片为唯一视觉来源，不得改用其他地点或其他植物建筑。

【必须清楚可辨认的 3 个记忆锚点】
{ANCHOR1} / {ANCHOR2} / {ANCHOR3}
这三个结构必须画出来且位置关系正确，其余细节全部舍弃。

【必须删除】{DROP}

【极度简化 · 决定像不像印章】
只刻必要的：主体轮廓 + 两三层结构线 + {少量元素数量，例"三片大叶、两支荷苞"}。总笔画量要少，留白要多，绝不能把画面填满。

【提炼方式 · 最关键，不可省】
不要缩小照片，不要描照片轮廓，不要给照片加滤镜、加半调网点。
只做四件事：主体提炼 → 结构简化 → 色彩压缩 → 印刷语言转译。
判断标准：看得出这是哪儿，但看不出任何照片像素。

【工艺】hand-carved linocut + letterpress，橡皮图章压印在纸上的手感：刀痕明显，线条粗细有变化（主轮廓粗、内部细节细），边缘有手工刻痕、小缺口与飞白，局部轻微缺墨，压力略不均匀，套色层之间约 1 像素错位。整体干净、清晰、克制、高级；不要脏污，不要重度做旧，不要破损毛边。

【构图】
图案沿主体自身外缘自然结束，直接坐在透明（或纯白）背景上。
**绝对不要加任何外框线、边框、画框、矩形轮廓、四边包边**，也不需要凑成完整方形。
{外形倾向：若主体高就写"整体偏竖长"、若主体宽就写"整体偏横长"}。水面、天空、地面全部留白。

【套印配色】恰好 {N} 色，全部从原图提取：{INK1}、{INK2}、{INK3}
平涂专色，实心填色。禁止渐变，禁止明暗过渡，禁止照片级光影，禁止金属光泽。

【印章内部文字】{INNER}

【禁止】
1) 红色圆形公章：带五角星、弧形排列汉字、朱红印泥、工商注册章、日式角印风格——全部禁止，这不是公章；
2) 任何边框、外框线、矩形包边、画框、卡片、样机、胶带、贴纸、图钉、装饰花边；
3) 麻将牌质感、浮雕、3D 立体、投影、倒影；
4) 照片本体、照片拼贴、半调网点、油画水彩插画感；
5) 满版堆叠、矩形色块铺底、除印章本身以外的任何物体、风景、背景、水印、签名、多余文字。

【输出】平面二维图案，白底或透明底，印章居中，四周留出白边，无边框。
```

### 参数

| 参数 | 值 | 说明 |
|---|---|---|
| `image1` | `photo_clean.jpg` | 唯一视觉来源 |
| `input_fidelity` | `low` | 要重刻，不要复制；`high` 会得到"缩小的照片" |
| `size` | `1024x1024` | 方形最稳，印章本身就是方的 |
| `quality` | `high` | 边缘刻痕细节靠它 |
| `background` | `transparent` | 拿不到也没事，合成脚本按亮度反推墨量 |

### 出图后立刻看三件事

- 是刻的，还是缩的？（有照片明暗 = 缩的）
- 是公章，还是图章？（圆的红的有五角星 = 公章）
- 三个锚点在不在？

---

## §C 全版一次成图（可选，慢且不稳）

只在用户明确要求"一张图直接出、不要后期合成"时用。代价：左侧照片会被重绘、文字可能拼错。对比 §B + 合成，这条路是**下策**，但它的版面语言更自然连贯。

```text
Fusion of Photography × Semantic Stamp × Archive Design. A collectible "photographic memory stamp" archive sheet. Photography records reality. Stamp preserves memory.

LOCKED PHOTOGRAPHIC ASSET
The uploaded photograph is the sole visual source and is treated as a locked photographic asset. It must retain its real photographic quality: exact subject, people, architecture, plants, spatial relationships, perspective, light and colour. Only slight cropping and edge optimisation are allowed. No stretching, no distortion, no subject replacement, no pose change, no invented elements, no scene change, no illustration, no cartoon, no 3D rendering.

ANALYSE FIRST, THEN DRAW
Identify the core subject, extract the 3-5 decisive visual memory anchors (silhouette, structure, tree form, road, light, colour, gesture), delete all meaningless detail.

STAMP CRAFT
The stamp is NOT a shrunken photo with a filter. It is built by subject reduction → structural simplification → colour compression → print-language translation. Style: vintage rubber stamp / letterpress / linocut / archival seal, hand-printed feel with slight grain and misregistration, yet clean, sharp and refined.

STAMP CONTENT
Keep only the core subject, supporting structure and minimal environment. The outline (square / vertical rectangle / rounded rectangle / oval) is chosen by the photo's own semantics.

STAMP COLOUR
1-3 spot colours, overprinted, extracted from the photograph's most memorable colours.

LAYOUT
Photograph + Archive Panel. Photograph occupies 50-60%, archive panel 40-50%.
Left photograph: full bleed from top edge to bottom edge, no margin, no border.
Archive panel: warm white or ivory paper, generous negative space, NO tape, NO stickers, NO decorative frame, NO unrelated decoration.

TEXT
Title: 2-4 English words. Keywords: exactly 3, formatted "keyword / keyword / keyword". Typography small, restrained, legible.

FORBIDDEN
Random people, animals, buildings, vehicles, logos, watermarks, social-platform marks, unrelated text. Red round Chinese official seal with star. Photo collage. Halftone.

Output one finished image, no commentary, no mockup.
```

> 补一句比例（`3:4` / `4:5` / `1:1`）再生成，出图会稳定很多。

---

## §D 三套填充示例

**A. 古建荷塘**（实测通过）
- SUBJECT：重檐六角亭 + 单拱石桥 + 荷叶与荷苞
- ANCHOR：六角攒尖顶向上翘起的檐角轮廓 / 石桥中央的单券拱洞 / 竖立的荷苞与圆形大荷叶
- DROP：背景白色居民楼、电线、远处游人
- 简化：荷叶只刻三片大的 + 两支荷苞
- 外形：不加外框，图案沿主体外缘自然结束（**不写"方形"**）
- INK：`#2C5813` `#C9748C` `#8E9BA6`
- TITLE：`LOTUS POND` ｜ KEYWORDS：`pavilion / arch / lotus`

**B. 仰视斜拉桥塔**
- SUBJECT：仰视的 A 形桥塔与放射状拉索
- ANCHOR：塔柱的倒三角轮廓 / 拉索的直线束 / 赭红塔身与天空灰的撞色
- 外形：整体偏竖长（贴合塔的高宽比），仍然不加任何外框线
- INK：`#B4472A` `#8E9BA6`
- TITLE：`ORANGE PYLON` ｜ KEYWORDS：`bridge / cable / sky`

**C. 日落跨海桥**
- SUBJECT：海平线上的双塔斜拉桥与落日
- ANCHOR：一条水平线 / 两座塔的剪影 / 落日那个圆
- 外形：整体偏横长（呼应水平线），仍然不加任何外框线
- INK：`#C4501F` `#2E2A33`
- TITLE：`SUNSET CROSSING` ｜ KEYWORDS：`sea / dusk / cable`

---

## §E 为什么这些条款有效

| 条款 | 机制 |
|---|---|
| `Locked Photographic Asset` | 把原图定义成"被锁定的资产"，一个词锁死"不许重绘"。这是整段的定海神针 |
| 先分析后生成 | 写成五步流水线，模型才会真的去"读"图；直接说"做个印章效果"只会得到一个模糊滤镜 |
| "不要缩小照片"这条否定句 | 缩小加滤镜得到的是"变小了的照片"；只有走提炼四步，才是"为这张照片单独刻的章" |
| 颜色从原图提取 | 决定印章会不会突兀。给固定红蓝会像贴上去的，从这张图捞色才有归属 |
| 数字定死文字量 | 不定数量，模型就给你写一大段；"恰好 3 个""2-4 个单词"它才收敛 |
| 两张分开的禁止清单 | 一张管照片、一张管版面。合在一起，模型会把"别动照片"理解成"整张图别加东西" |
| 反公章条款放第一句 | 中文"印章"的强先验是红色圆公章，不提前打死必然跑偏 |
| 不许出现"方形/外廓"字样 | 这是实测出来的：一写"方形外廓"，模型立刻画一圈边框，印章变画框 |
| "极度简化"要给数量 | 只说"简化"，模型仍会把荷叶铺满；给它"三片、两支"的具体数字才收得住 |
