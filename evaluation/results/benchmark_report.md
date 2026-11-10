# ResearchPilot 正式 Benchmark 第一轮报告

- 报告日期：2026-11-10
- 数据集版本：`0.2`
- 模型：`qwen3:4b`
- Embedding：`qwen3-embedding:0.6b`
- Temperature：`0`
- Top-K：`4`
- 合并后的试运行原始结果：`evaluation/results/formal_benchmark_pilot_20261110.json`
- 人工审核表：`evaluation/review_table.md`

## 结论摘要

本轮建立了 20 道候选题，并对 5 道代表性问题执行了
Baseline、Direct PDF RAG、ResearchPilot Fast 和 ResearchPilot Deep
四种配置，共 20 次运行。20 次运行均完成且没有超时，但这不等于 20
个回答都正确。质量门禁发现 Deep Mode 的一次明确工具选择错误和一次
跨论文检索漏召回，因此没有在未修正的情况下继续运行其余 15 题。

当前 20 道题的参考答案全部为 `pending_human_review`，已审核数量为
0。本报告不提供正式 Answer Correctness 或 Evidence Support 准确率。

## 数据集与真实 PDF

实际使用项目内已经导入的 3 篇 PDF：

- `1-s2.0-S2352847824001278-main.pdf`
- `materials-4180042.pdf`
- `s41467-025-56194-1.pdf`

候选题目共 20 道：

| 类型 | 数量 |
|---|---:|
| 事实提取 | 5 |
| 机制解释 | 4 |
| 跨语言 | 3 |
| 跨段落或跨论文综合 | 4 |
| 证据不足 | 4 |

题集的机械核验结果：

- 20/20 题包含任务要求的顶层字段。
- 所有 answerable 题目的 `supporting_excerpt` 均能在真实 PDF 的标注页找到。
- 跨论文题逐条核对了 `supporting_sources`，各来源摘录均在对应文件和页码出现。
- 这只能证明摘录来自真实 PDF，不能代替对参考答案科学含义的人工审核。

## 本轮实际评测范围

试运行题目：

- `q01`：事实提取
- `q04`：事实提取
- `q09`：跨语言
- `q16`：跨论文综合
- `q10`：证据不足

共评估 5/20 道题。剩余 15 道题没有运行，原因是小规模试运行的质量
门禁已经暴露出需要先分析的工具选择和检索漏召回问题。

## 四个版本的定义

| 版本 | 执行路径 |
|---|---|
| A Baseline | 仅向 `qwen3:4b` 提供问题，不提供 PDF、检索或 MCP Tool |
| B Direct PDF RAG | Chroma 检索 → Qwen 回答 → 程序附加检索来源 |
| C ResearchPilot Fast | 复用 PDF RAG，并执行 Evidence Registry、`[S#]` 引用和来源校验 |
| D ResearchPilot Deep | Context Loader → Planner → Executor/MCP → Replanner → Writer |

Baseline 没有检索证据，因此其引用校验和 PDF Evidence Support 指标应标记
为 `not_applicable`，不能简单记为答错。

## 运行成功情况

| 版本 | 尝试 | 完成运行 | 超时/错误 | 说明 |
|---|---:|---:|---:|---|
| A Baseline | 5 | 5 | 0 | 所有运行结束；无 PDF 引用能力 |
| B Direct RAG | 5 | 5 | 0 | q10、q16 在无检索 Chunk 时未调用 LLM，直接拒答 |
| C Fast | 5 | 5 | 0 | 引用与 Evidence Registry 路径正常 |
| D Deep | 5 | 5 | 0 | 所有任务均产生最终答案，但 q09、q16 回答任务失败 |

“完成运行”只表示程序正常返回，不表示回答正确。

## 自动指标

### 完成、延迟和调用量

| 版本 | 平均耗时（秒） | LLM 调用 | LLM 元数据覆盖 | Token 总量 | Tool 调用 | Chroma 检索耗时（秒） |
|---|---:|---:|---:|---:|---:|---:|
| A Baseline | 38.06 | 5 | 5/5 | 5,915 | 0 | 0 |
| B Direct RAG | 48.73 | 3 | 5/5 | 10,354 | 0 | 4.220 |
| C Fast | 62.95 | 3 | 5/5 | 12,451 | 0 | 0.544 |
| D Deep | 450.44 | 15（不完整） | 3/5 | 43,192（不完整） | 5 | 6.874（不完整） |

Deep Mode 的 q09 和 q16 结果来自 profiler 传播修复之前的运行，因此
这两个记录的详细 LLM 调用、Token 和工具耗时字段为空。表中 D 组的
LLM/Token/Chroma 数字只覆盖 q01、q04、q10，不能视为五题完整总量。
Tool Call 记录本身仍保存在每次运行的 `tool_calls` 中。

Deep 组中性能字段完整的 3 题，其 LLM 生成时间分别约占总耗时：

- q01：524.17 / 526.11 秒
- q04：542.53 / 548.94 秒
- q10：302.35 / 304.36 秒

现有证据显示，这些 Deep 运行的耗时主要来自多节点 LLM 推理；MCP 和
Chroma 不是主要慢点。Cold/warm start 条件并未完全统一，不能据此给出
严谨的跨模式速度因果结论。

### 引用结构校验

| 版本 | 有效结构校验 | 通过 | 失败 | 结论 |
|---|---:|---:|---:|---|
| A Baseline | 0 | 0 | 0 | `not_applicable` |
| B Direct RAG | 5 | 5 | 0 | 程序附加的检索来源存在 |
| C Fast | 5 | 5 | 0 | 引用 ID、有效来源映射通过 |
| D Deep | 5 | 5 | 0 | 结构校验通过，但不保证结论正确 |

Deep q09 是重要反例：Crossref DOI 和 `[S5]` 都真实存在并通过结构校验，
但该证据来自地震学论文，不是题目要求的本地材料学 PDF 证据。因此
Citation Validity 不能替代 Evidence Support。

### 人工审核指标状态

| 指标 | 状态 |
|---|---|
| Answer Correctness | `pending_human_review` |
| Evidence Support | `pending_human_review` |
| Unsupported Claim | `pending_human_review` |
| Incorrect Abstention | `pending_human_review` |
| Task Completion | `pending_human_review` |

## 典型成功案例

### q04：三项研究变量的提取

Direct RAG、Fast 和 Deep 都正确给出：

1. thin film 与 substrate 之间的 misfit strain；
2. defect dipoles doping；
3. film thickness。

证据来自 `1-s2.0-S2352847824001278-main.pdf` 第 1 页。Fast 和 Deep
引用了 `[S4]`，引用可追溯到真实 Chunk。

旧的关键词启发式检查把 Direct RAG 标为可疑，因为它只匹配连续的
`misfit`，而回答受 PDF 抽取文本影响写成 `mis fit`。这是自动评测器的
Unicode/空格归一化缺陷，不是 q04 回答失败。该启发式结果不纳入自动
正确率。

### q10：证据不足处理

四个版本均明确回答“证据不足”。Direct RAG 和 Fast 在检索不到满足阈值
的 Chunk 时没有调用 LLM，也没有编造超导临界温度。Baseline 没有本地
PDF 能力，因此其 PDF Evidence Support 指标为 `not_applicable`。

### q01：有可用证据时完成回答

Direct RAG、Fast 和 Deep 都识别出“通过增加熵设计反铁电极化构型”，
并追溯到 `s41467-025-56194-1.pdf` 第 1 页。Baseline 因未获得 PDF
上下文而回答证据不足，这体现的是配置差异。

## 典型失败案例

### q09 Deep：Tool Selection / Agent Planning 错误

题目要求解释 `materials-4180042.pdf` 中的梯度能量扰动模型。Deep
Executor 选择了：

```text
search_papers(query="perturbation model constant coefficients isotropic approximation", max_results=5)
```

随后它基于 `10.1190/geo2021-0695.1` 的地球物理论文回答 P/S 波和地震
成像问题，与本地材料学 PDF 的主题不符。该 DOI 真实存在，引用结构也
有效，但科学证据支持失败。

分类：Tool Selection 错误 / Agent Planning 错误。

### q16 Direct RAG、Fast、Deep：跨论文检索漏召回

题目要求比较熵论文与 PZO 域调制论文。Direct RAG 和 Fast 均因没有
Chunk 通过相似度阈值而拒答。Deep 将检索查询收缩为单字

```text
retrieve_paper_evidence(query="entropy", top_k=4)
```

没有返回证据，随后提前结束。三组都正确避免编造答案，但没有完成任务。

分类：跨语言/跨论文检索漏召回、错误拒答；Deep 还包含过早结束。

## 错误分类汇总

| 分类 | 实际案例 |
|---|---|
| PDF 解析错误 | 本轮未确认 |
| 检索漏召回 | q16 B/C/D |
| 跨语言检索问题 | q09 D 选择了错误的 Crossref 方向 |
| Tool Selection 错误 | q09 D |
| 模型无依据生成 | 本轮未确认；q16 的拒答避免了此类问题 |
| 错误引用 | q09 D 的结构引用有效，但证据主题不支持题目 |
| 错误拒答 | q16 B/C/D |
| 模型超时 | 无 |
| Agent 规划错误 | q09 D；q16 D 过早结束 |

## 当前不能确定的结论

- 20 道候选题的参考答案尚未人工审核，不能据此计算正式准确率。
- 5 道题不足以代表全部题型和全部论文的总体表现。
- Deep 的平均耗时长，但 q09/q16 缺少完整 profiler 字段，且 cold/warm
  start 未完全平衡，不能把 450.44 秒直接解释为架构的稳定性能上限。
- q16 失败可能同时涉及查询生成、Embedding 跨语言匹配和阈值策略；
  当前证据不足以把责任单独归给其中某一项。

## 后续最值得优化的三个问题

1. 改进跨论文和跨语言检索：对复合问题生成可核查的多个检索查询，
   提高召回，再以真实 Chunk 判断证据是否充分。
2. 增加工具选择与完成条件检查：本地 PDF 问题不应被无关 Crossref
   结果替代；空证据时 Replanner 应继续调整查询而不是立即结束。
3. 修复评测与证据校验自动化：统一 Unicode/PDF 空格归一化，区分
   来源结构有效和主题支持，并确保每次运行都写入完整 profiler 字段。

在这些问题得到处理并对参考答案完成人工审核之前，本轮只能视为
Benchmark 基础设施与首轮试运行，不能视为正式准确率验收。
