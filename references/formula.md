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

## Unicode 数学符号 → LaTeX 自动兜底（v1.1.5+）
**问题**：学生/老师在写公式时常直接粘贴 `∈ Δ ⇒ ≤ ≥ ≠ π θ ± × √` 等 Unicode 数学符号，KaTeX 不认这些，渲染时会报 `Unsupported` 并把后续内容截断。

**解法**：`generate.py` 的 `tex()` 现在在还原 `<bs>` 之后，会对**所有 `\(...\)` / `$$...$$` 公式块内**的 Unicode 数学符号自动转 LaTeX 命令。块外的中文 / 全角括号 / 中文标点**完全保留原样**不被污染。

当前覆盖的对照（块内生效，块外不替换）：

| Unicode | → LaTeX | 类别 |
|---------|---------|------|
| `∈ ∉` | `\in \notin` | 集合 |
| `⊂ ⊆ ⊃ ⊇ ∪ ∩ ∅` | `\subset \subseteq ... \emptyset` | 集合 |
| `⇒ ⇐ ⇔ → ← ↦` | `\Rightarrow \Leftarrow \Leftrightarrow \to \leftarrow \mapsto` | 箭头 |
| `≤ ≥ ≠ ≪ ≫` | `\leq \geq \neq \ll \gg` | 不等/序 |
| `Δ Σ Π Ω Θ Λ Φ Ψ` | `\Delta \Sigma \Pi \Omega ...` | 希腊大写 |
| `α β γ δ ... ω` | `\alpha \beta \gamma \delta ... \omega` | 希腊小写 |
| `∞ ∂ ± ∓ × ÷ · √` | `\infty \partial \pm \mp \times \div \cdot \sqrt{}` | 算子 |
| `∑ ∏ ∫ ∮ ≈ ≡ ≅ ∝ ⊥ ∠` | `\sum \prod \int \oint \approx \equiv \cong \propto \perp \angle` | 其他 |
| `（ ）` 在公式里 | `(` `)` | 中→ASCII 括号 |
| `， ； ：` 在公式里 | `, ` `; ` `: ` | 全角→半角标点 |

**仍然推荐**在数据里直接写 LaTeX 命令（更可控、避免歧义），但**写错也不会再让整条公式挂掉**——这是兜底层。
