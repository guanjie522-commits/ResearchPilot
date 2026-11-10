# ResearchPilot Benchmark 可靠性与 Tool Selection 诊断

- 任务：12-E
- 日期：2026-11-10
- 原始试运行结果：`evaluation/results/formal_benchmark_pilot_20261110.json`
- 派生分析结果：`evaluation/results/reliability_analysis_20261110.json`
- 5 题人工审核表：`evaluation/five_question_review.md`
- 原始试运行 JSON 未被修改

## 结论摘要

- q04 的 `mis fit` / `misfit` 误判已修复，回归测试通过。
- q09 的已确认错误发生在 Deep Executor 的 Tool Selection：它选择了
  `search_papers`，随后 Writer 使用了无关的 Crossref 证据。
- q16 存在已确认的本地证据检索漏召回和错误拒答；历史结果没有保存
  Plan 与 Replanner 决策，因此不能确认是否属于 premature termination。
- 参考答案仍为 0/5 人工审核，不能报告正式 Answer Correctness 或
  Evidence Support。

## q04 文本规范化

新增 `evaluation/text_matching.py`，只做以下保守规范化：

- Unicode NFKC，处理 `ﬁ` 等兼容字符；
- 大小写统一；
- 合并多余空白；
- 统一常见横线字符；
- 处理连字符换行；
- 允许连字符在词内作为短语词边界；
- 仅对 `mis fit` 显式建立到 `misfit` 的等价关系。

匹配使用 token boundary，不做编辑距离、模糊相似度或任意字符通配。
特别验证了：

- `misfit strain`、`mis fit strain`、`mis ﬁt strain`、
  `mis-fit strain` 可匹配同一术语；
- `tensile strain` 不会匹配 `misfit strain`；
- `misfitted strain` 不会匹配 `misfit strain`；
- `film thicknesses` 不会匹配 `film thickness`。

修复前后：

| 项目 | 修复前 | 修复后 |
|---|---|---|
| q04 B Direct RAG | 被标为 probable mismatch | 通过术语检查 |
| q04 C Fast | 通过 | 通过 |
| q04 D Deep | 通过 | 通过 |
| 适用运行通过数 | 2/3 | 3/3 |
| Baseline | `not_applicable` | `not_applicable` |

修复仅影响评测派生结果，原始回答没有被替换。术语存在也不等于答案在
科学含义上完全正确，最终状态仍为 `pending_human_review`。

## q09 Tool Selection 诊断

### 已确认事实

- Original Task：
  `请用中文说明这个扰动模型为何能处理以前常系数或各向同性近似难以处理的问题。`
- 数据集预期来源：`materials-4180042.pdf` 第 1 页。
- Executor step 1 调用了：

```text
search_papers(
  query="perturbation model constant coefficients isotropic approximation",
  max_results=5
)
```

- 该调用返回 5 条 Crossref 元数据，最后 Writer 使用
  `[S5]` DOI `10.1190/geo2021-0695.1` 回答。
- 该 DOI 属于地球物理学论文，回答讨论 P 波、S 波和地震成像。
- 没有 local PDF Evidence ID。
- Citation Structural Validity 为 `true`，但 Evidence Support 失败。

### 错误位置

已确认的错误动作发生在 **Executor 的 tool-selection step**。随后错误在
**Writer** 中被传播。Tool Call 本身执行并返回了数据，所以 Tool Call
Success 与 Tool Selection Correctness 是不同指标。

历史结果没有保存 Planner Plan、Executor 收到的 Step 文本、
Replanner decision/reason。因此：

- Planner 是否在上游生成了有歧义的步骤：无法确定；
- 模型选择 `search_papers` 的内部理由：无法确定；
- Replanner 是否发现并尝试修正：无法确定；
- 是否提前结束：无法确定。

另外，q09 原始题干只写“这个扰动模型”，没有明确说“根据本地已导入
PDF”。这使人工审核时应考虑题干指代歧义；不能只把责任归给模型。

## q16 诊断

### 已确认事实

- Original Task 明确要求 `Using only the imported local PDFs`。
- Deep Executor step 1 正确选择 `retrieve_paper_evidence`。
- Tool Args 为 `query="entropy", top_k=4`。
- 返回 0 条 Evidence ID。
- 最终回答明确拒答，并说明没有证据通过 0.25 阈值。
- q16 在候选集中标记为 answerable，且真实 PDF 第 1 页存在候选支持的
  设计方法摘录。

因此可以确认：

- Tool Selection Correctness：正确；
- Tool Call Success：调用完成并返回了可观察结果；
- Evidence Retrieval：漏召回；
- Incorrect Abstention：存在；
- Premature Termination：**无法确认**。

历史 Plan 和 Replanner 信息缺失，无法知道是否还有剩余检索步骤，也无法
判断 Replanner 是主动选择 finish 还是因计划已耗尽而结束。

## 当前 Tool Discovery

本次分析重新执行了安全的本地 MCP Discovery。当前发现：

| Tool | 用途 |
|---|---|
| `calculator` | 两个数字相乘 |
| `search_github` | GitHub 公共仓库搜索 |
| `search_papers` | Crossref 论文元数据搜索 |
| `retrieve_paper_evidence` | 本地 PDF Chroma 证据检索 |

该 Discovery 证明当前 Server 暴露的工具；历史 Deep 运行时模型实际
收到的完整 Tool schema 没有写入旧 JSON，因此不把当前 discovery 冒充成
历史上下文。

## 指标完善

评测输出现在分别保留：

- Tool Call Success；
- Tool Selection Correctness；
- Citation Structural Validity；
- Evidence Support；
- Answer Correctness；
- Premature Termination；
- Latency；
- LLM 调用与 Token 元数据可用性；
- Tool Call 和 Token 的 available sum、missing run count 与 status。

历史 Deep q09/q16 的 Token 元数据缺失，现在输出为：

- 完整聚合值：`null`；
- 可用记录部分和：`43,192`；
- metric status：`partial`；
- missing runs：`2`。

不会再把这些缺失字段填为 0。

## 后续运行轨迹持久化

`evaluation/run_benchmark.py` 已增加最小 instrumentation，但不改变 Agent
Graph 或 Prompt：

- 保存 MCP Tool catalog；
- 保存 Planner Plan；
- 保存 completed steps 和 Executor Step Results；
- 保存 Tool Call result summary；
- 保存 Replanner action/reason；
- 保存 replan_count 和 evidence IDs。

下一次 Deep Benchmark 运行将具备完整诊断资料。本次没有重跑 q09/q16，
因为新运行不能重建旧失败现场，也不能把新结果冒充为历史证据。

## 尚需人工审核

5 道题均为 `pending_human_review`。建议逐题确认：

- 参考答案是否忠实于 PDF；
- Baseline 的“证据不足”在无检索配置下是否是预期行为；
- q04 三个术语是否足以构成完整答案；
- q09 B/C 的机制解释是否超出支持原文；
- q16 的正确摘要是否足以构成跨论文比较；
- q10 的真实 PDF 是否确实没有相关证据。

## 后续最小修复建议

1. 下一版数据集明确改写 q09 为“根据已导入的本地 PDF”，消除指代歧义。
2. 对本地 PDF 查询增加执行阶段的来源一致性检查：若要求 local PDF，
   Tool Result 只有 Crossref metadata 时应标记来源不匹配并重试一次，
   而不是直接交给 Writer。
3. 对复合检索问题使用多个查询，而不是把冗长问题压缩成单个词；同时
   在 Replanner 输入中显式包含 remaining steps 和 retrieval miss 信号。

以上建议尚未实现，本次没有修改 Planner/Replanner Prompt 或 Graph。
