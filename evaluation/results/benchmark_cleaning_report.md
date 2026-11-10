# ResearchPilot Benchmark 数据清洗与审核准备

- 任务：12-F
- 日期：2026-11-10
- 数据集版本：`0.3`
- 原始首轮结果：`evaluation/results/formal_benchmark_pilot_20261110.json`
- 原始结果 SHA-256：
  `0d02a575a9ef5cbf845c84179c0ec76e18b56ba74fe6d7ab3900f1e7b69eae54`
- 人工审核文件：`evaluation/human_review.md`
- q16 检索诊断：`evaluation/results/q16_retrieval_diagnosis_20261110.json`

## 数据集分类

题集现在包含 20 道原始题和 1 道 q09 来源明确化变体，共 21 条记录。

| 任务类型 | 题目数 | 说明 |
|---|---:|---|
| `local_pdf_qa` | 21 | 每条记录都要求使用当前导入的本地 PDF |
| `insufficient_evidence` | 4 | 同时属于本地 PDF 问答，但预期没有足够证据 |
| `cross_paper_synthesis` | 3 | q16、q17、q18 |
| `paper_discovery` | 0 | 当前核心数据集没有真实外部论文发现题 |

每条记录新增：

- `task_types`：可包含多个任务类型；
- `source_scope`：当前均为 `imported_local_pdfs`；
- `expected_tools`：当前均为 `retrieve_paper_evidence`。

`expected_tools` 只用于评测和人工审核，没有用于 Agent 的关键词或 if/else
路由。

## q09 原题与变体

### 原始 q09

```text
请用中文说明这个扰动模型为何能处理以前常系数或各向同性近似难以处理的问题。
```

- 保留原题和原始运行记录；
- 预期来源：`materials-4180042.pdf` 第 1 页；
- 预期工具：`retrieve_paper_evidence`；
- `source_scope_is_explicit: false`；
- 歧义：没有明确说明“这个扰动模型”来自当前导入的本地 PDF。

### 新增变体 q09_local_pdf

```text
请仅根据当前已经导入的本地 PDF，针对 materials-4180042.pdf，
用中文说明这个扰动模型为何能处理以前常系数或各向同性近似难以处理的问题。
```

- `derived_from: q09`；
- 预期来源和工具与原题相同；
- `source_scope_is_explicit: true`；
- 任务12-F准备时为 `execution_status: not_run`；任务12-G已完成运行；
- 参考答案仍为 `pending_human_review`。

本次任务12-G已另行运行该变体，但没有通过修改 Agent Prompt 让原题“通过”。

## q16 检索诊断

原始 Agent 调用：

```text
retrieve_paper_evidence(query="entropy", top_k=4)
```

配置阈值：`0.25`。分数方向为
`chroma_relevance_1_minus_cosine_distance_higher_is_better`。

实际 top-4 原始候选：

| Score | Source | Page | Chunk |
|---:|---|---:|---|
| 0.093935 | `s41467-025-56194-1.pdf` | 3 | `c01c9f511e2a100e:p0003:c0002` |
| 0.055755 | `s41467-025-56194-1.pdf` | 3 | `c01c9f511e2a100e:p0003:c0004` |
| 0.025202 | `materials-4180042.pdf` | 3 | `f831e3b0bc234f0b:p0003:c0001` |
| 0.010102 | `materials-4180042.pdf` | 6 | `f831e3b0bc234f0b:p0006:c0000` |

通过阈值的证据为 0 条，因此：

- 实际作为 Evidence 命中的 PDF：0 篇；
- 预期目标论文：2 篇；
- 命中的目标论文：0/2；
- 原始 top-4 只出现熵论文和 gradient-energy 论文的低分片段，没有命中
  PZO domain-modulation 论文；
- 不是“只命中一篇目标论文”，而是没有目标论文通过阈值。

诊断脚本还使用当前 `retrieve_paper_evidence("entropy", top_k=4)` 复现了
同一结果：返回 `Evidence insufficient`，没有 Evidence。

两篇目标片段实际存在于 Chroma：

| 目标论文 | Chunk |
|---|---|
| entropy paper | `c01c9f511e2a100e:p0001:c0000` |
| PZO domain-modulation paper | `d99a382568c429f7:p0001:c0000` |

因此 q16 的已确认问题是：单词语义查询召回失败和来源覆盖不足；
目标文本并没有从索引中缺失。

诊断脚本没有修改 Chroma、Chunk、Embedding、阈值或检索算法。

按新增的 `expected_tools` 只读评测，首轮 Deep Mode 的 Tool Selection
为 4/5：q01、q04、q16、q10 选择了 `retrieve_paper_evidence`；
q09 选择了 `search_papers`。该指标只用于评测，不参与 Agent 路由。

## 人工审核文件

`evaluation/human_review.md` 对 q01、q04、q09、q16、q10 分别列出：

1. Question ID；
2. 原始问题；
3. 候选参考答案；
4. 支持原文；
5. PDF 文件名；
6. 页码；
7. Baseline 回答；
8. Direct RAG 回答；
9. Fast Mode 回答；
10. Deep Mode 回答；
11. 真实引用来源；
12. 待审核问题。

所有回答直接来自原始结果 JSON。五个问题的参考回答和实际回答都保持
`pending_human_review`。

审核者可选择：

- `correct`
- `partially_correct`
- `incorrect`
- `insufficient_evidence`
- `needs_source_check`

并可在每题末尾填写备注。

## 完整性检查

- 原始 `formal_benchmark_pilot_20261110.json` 未修改，SHA-256 与提交版本一致。
- q04 的 `mis fit` / `misfit` 归一化回归仍通过。
- q09 原题保留，q09_local_pdf 独立存在并已在任务12-G运行。
- Deep q09/q16 的缺失 Token 仍为 `null` / `partial`，没有补成 0。
- `run_benchmark.py --help` 和可靠性分析脚本均可运行。
- 20 项评测器、指标和数据完整性测试全部通过。

## 当前待人工审核

| ID | 参考来源 |
|---|---|
| q01 | `s41467-025-56194-1.pdf` p.1 |
| q04 | `1-s2.0-S2352847824001278-main.pdf` p.1 |
| q09 | `materials-4180042.pdf` p.1 |
| q16 | `s41467-025-56194-1.pdf` p.1；`1-s2.0-S2352847824001278-main.pdf` p.1 |
| q10 | 预期三篇本地 PDF 均无证据 |

本次没有修改 Planner、Executor、Replanner、Writer 或 Tool Description。
