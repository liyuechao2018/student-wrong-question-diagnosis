# 公式约定与 LaTeX 坑

卡片 `one` / `mistake` / `action` 中的公式用 KaTeX 渲染。

## 反斜杠占位符 `<bs>`
- 数据源里**不要直接写反斜杠**（易被 Python 字符串转义吃掉），用 `<bs>` 表示 LaTeX 反斜杠（chr 92）。
- `generate.py` 的 `tex()` 在构建时把 `<bs>` 还原为 `\`。
- 物理 / 数学公式用 `<bs>(...<bs>)` 包裹整段公式：`area = <bs>(<bs>frac{1}{2} b h<bs>)`。

## 化学公式 `\ce{}`
- 裸 `\ce{...}` 会被 `generate.py` 的 `wrap_ce()` 自动包进 `\(...\)`，无需手写外层 `\(\)`。

## 常见 LaTeX 修正（node 校验会报错的写法）
| 错误写法 | 正确写法 |
|----------|----------|
| `\sqrt3` | `\sqrt{3}` |
| `\frac12` | `\frac{1}{2}` |
| `\cos30°` | `\cos 30^\circ` |
| `\sin37°` | `\sin 37^\circ` |
| `F_合` | `F_{\text{合}}` |
| `a/b` | `\frac{a}{b}` |
| `\bar v=(v1+v2)/2` | `\bar{v}=\frac{v_1+v_2}{2}` |

## 校验方法
生成后用 node katex `renderToString({throwOnError:true})` 抽验每条 `\(...\)`，FAIL 即回到卡片修正对应 LaTeX。
