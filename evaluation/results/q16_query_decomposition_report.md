# q16 Query Decomposition 与自己验证报告

- 任务：12-G
- 日期：2026-11-10
- q16 实验原始结果：
  `evaluation/results/q16_query_experiments_20261110.json`
- q09 变体原始结果：
  `evaluation/results/benchmark_20261110T063228Z.json`
- 人工审核摘要：`evaluation/human_review_summary.md`

## 1. 检索分数定义

当前代码使用 LangChain Chroma 的：

```python
similarity_search_with_relevance_scores(..., k=top_k)
```

本项目将该分数解释为：

```text
relevance = 1 - cosine_distance
```

分数越高越相关，范围通常为 `0..1`。当前默认阈值为 `0.25`，即要求
`cosine_distance <= 0.75`。实现中观察到 Chroma 偶尔返回负 relevance，
因此项目没有把它当作严格的概率值，只作为同类查询排序和阈值过滤分数。

相关实现：

- `rag/qa.py`
- `rag/pdf_index.py`
- `rag/config.py`

本次没有修改分数定义、阈值或检索实现。

## 2. 实验设计

q16 原始问题：

```text
Using only the imported local PDFs, compare the main design approaches of the
entropy paper and the PZO domain-modulation paper.
```

所有普通实验保持：

- Embedding：`qwen3-embedding:0.6b`
- `top_k=4`
- threshold：`0.25`
- 原索引：145 个 Chunk

查询没有使用目标论文的完整标题或支持原文。

### A：原始查询

```text
entropy
```

没有 source filter。

### B：完整英文语义查询

```text
Compare the main design approaches of the entropy-based
antiferroelectric polarization paper and the PZO antiferroelectric
domain-modulation phase-field simulation paper.
```

没有 source filter。

### C：查询分解

查询 1：

```text
How is increasing entropy used to design the antiferroelectric
polarization configuration for capacitive energy storage?
```

查询 2：

```text
How is antiferroelectric domain modulation studied with phase-field
simulations to improve energy storage performance?
```

分别执行两种条件：

- C-global：两个查询均无 filter，全库检索；
- C-filtered：两个查询分别启用
  `filter={"source_file": ...}`，针对两个已知目标 PDF 检索。

source filter 是额外实验条件，不能与全库检索视为完全相同条件。

## 3. 实际结果

| 实验 | Query 数 | Top-K/查询 | source filter | 耗时（秒） | 通过阈值 Chunk | 目标来源覆盖率 |
|---|---:|---:|---|---:|---:|---:|
| A 原始 | 1 | 4 | 否 | 0.039041 | 0 | 0/2 |
| B 完整语义 | 1 | 4 | 否 | 0.040910 | 4 | 1/2 |
| C 全局分解 | 2 | 4 | 否 | 0.071389 | 最多 8，去重后 7 | 2/2 |
| C 来源过滤分解 | 2 | 4 | 是 | 0.071257 | 最多 8，去重后 8 | 2/2 |

“最多 8”表示两个查询各取 top-4，并非一个查询返回 8 条。

### A 原始查询

最高分：

| Score | PDF | Page |
|---:|---|---:|
| 0.093935 | `s41467-025-56194-1.pdf` | 3 |
| 0.055755 | `s41467-025-56194-1.pdf` | 3 |
| 0.025202 | `materials-4180042.pdf` | 3 |
| 0.010102 | `materials-4180042.pdf` | 6 |

全部低于 `0.25`，没有 Evidence。

### B 完整语义查询

通过阈值的 Chunk 包括：

- `1-s2.0-S2352847824001278-main.pdf` 第 1 页，score `0.514899`：
  PZO domain modulation + phase-field simulation 标题与摘要。
- 同一论文第 2 页，score `0.502592`：
  缺陷偶极子、misfit strain、畴结构与储能性能。
- `materials-4180042.pdf` 第 10、11 页：
  主要是参考文献和梯度能量背景。

该组命中 PZO 目标论文，但没有命中 entropy 目标论文，覆盖率 `1/2`。

### C 全局分解

通过阈值的目标 Chunk：

- Entropy 查询第 1 名：
  `s41467-025-56194-1.pdf` p.1，score `0.774132`；
- PZO 查询第 1 名：
  `1-s2.0-S2352847824001278-main.pdf` p.1，score `0.723243`；
- 另有 entropy 论文第 6 页机制内容和 PZO 论文第 2 页方法内容；
- 也混入 materials 论文第 10 页和 entropy 论文第 8 页的参考文献型 Chunk。

因此两篇目标论文均命中，但全库结果仍包含辅助或弱相关片段。

### C 来源过滤分解

两篇目标论文的第一名分别为 `0.774132` 和 `0.723243`，与全局分解相同。
过滤后结果更集中：

- entropy 查询返回 4 个 entropy PDF Chunk；
- PZO 查询返回 4 个 PZO PDF Chunk；
- 仍然包含少量参考文献/补充背景 Chunk，但不再混入第三篇论文。

来源覆盖率同为 `2/2`。

## 4. 证据相关性

不能只看分数，实际检查内容后：

- A 没有任何通过阈值的证据；低阈值下的 entropy Chunk 与主题相关，
  但仍不覆盖第二篇目标论文。
- B 的 PZO 目标是真实相关的标题/摘要和方法片段；materials 文献列表
  不是理想的跨论文比较证据。
- C 两个第一名分别直接对应两篇目标论文，能够支持“熵设计策略”和
  “PZO domain modulation + phase-field”的核心比较。
- C 的额外 Chunk 包含真实相关内容，也有参考文献条目；进入 Writer 前
  仍应做来源选择和证据压缩。

## 5. 阈值敏感性

对 A 的原始 top-4 做离线敏感性检查：

| Threshold | 通过数 | 结果 |
|---:|---:|---|
| 0.25 | 0 | 无证据 |
| 0.20 | 0 | 无证据 |
| 0.15 | 0 | 无证据 |
| 0.10 | 0 | 无证据 |
| 0.05 | 2 | 两条 entropy 论文第 3 页 Chunk |
| 0.00 | 4 | 增加两条 materials 论文弱相关 Chunk |

降低阈值可以让 entropy 论文内容通过，但仍不能覆盖 PZO 论文。因此
降低默认阈值不能解决 q16 的根本来源覆盖问题，反而增加弱相关证据。
本次不建议修改 `0.25`。

## 6. q09 明确来源变体

运行结果：

```text
question_id: q09_local_pdf
tool: retrieve_paper_evidence
query: perturbation model definition, constant coefficient approximation,
       isotropic approximation
top_k: 4
```

真实返回 4 个本地 Evidence：

- `materials-4180042.pdf` p.5，score `0.363094`
- `materials-4180042.pdf` p.8，score `0.288221`
- `materials-4180042.pdf` p.4，score `0.275627`
- `materials-4180042.pdf` p.1，score `0.258066`

对比：

| 题目 | Tool Selection | Evidence | 运行耗时 |
|---|---|---|---:|
| 原始 q09 | `search_papers` | Crossref DOI `10.1190/geo2021-0695.1` | 548.324 秒 |
| q09_local_pdf | `retrieve_paper_evidence` | 4 个本地 materials PDF Chunk | 309.489 秒 |

明确来源后，模型真实选择了本地检索工具并获得了相关原文证据。最终回答
的结构引用校验通过，但仍为 `pending_human_review`。

Replanner 在完成 1 个执行 Step 后选择 `finish`，Writer 接替完成总结。
其 reason 中提到“动态响应、多尺度耦合”等示例，但当前 Chunk 没有明确
这些表述；该理由的科学支持性仍应人工检查。最终答案没有直接复述这两个
示例。

## 7. Agent 建议

建议在下一次 Agent 版本中实验 Query Decomposition，但不要直接替换稳定
版本：

1. 对 cross-paper synthesis 问题生成多个面向子目标的查询；
2. 每个查询独立执行 `retrieve_paper_evidence`；
3. 合并时按 source_file/chunk_id 去重并检查目标来源覆盖；
4. 只有目标来源覆盖不足时才触发一次额外分解；
5. 保留现有 `0.25` 阈值。

本实验证明 query decomposition 有效，但并不证明 Agent 自动生成查询的
质量。该能力尚未接入主 Agent。

## 8. 人工审核摘要

精简人工审核文件：

```text
evaluation/human_review_summary.md
```

其中首轮五题全部保持 `pending_human_review`，并附 q09_local_pdf 的
真实 Tool Call 与回答。
