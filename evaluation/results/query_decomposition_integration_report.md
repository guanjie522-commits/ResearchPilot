# Query Decomposition 有限集成实验报告

- 任务：12-H
- 日期：2026-11-10
- 实验开关：`--query-decomposition`
- 默认状态：关闭，稳定 Agent 行为不变
- 检索证据复现：
  `evaluation/results/q16_integrated_retrieval_20261110.json`
- 超时运行记录：
  `evaluation/results/benchmark_20261110T090436Z.json`

## 实现位置

- `query_decomposition.py`
  - 最多两条子查询的 Pydantic schema；
  - 明确的跨论文/多来源 Gate；
  - 禁止宽泛单词和明显跨领域查询；
  - 首次查询不合格时最多修复一次；
  - 通过现有 MCP `retrieve_paper_evidence` 执行查询；
  - 按 outer Tool Call 缓存，避免后续 Step 重复检索。
- `researchpilot_rag.py`
  - `enable_query_decomposition=False` 可选参数；
  - 在 Planner 后生成 decomposition plan；
  - 仅在该模式中用包装后的同源 MCP Retriever 构建 Executor；
  - 保存 `query_decomposition` 和 `retrieval_trace`。
- `evaluation/run_benchmark.py`
  - 新增 `--query-decomposition`；
  - 实验变体名称为 `D_deep_decomposed`。

未修改 Embedding、Chunk、Chroma 索引、默认阈值或稳定默认 Graph。

## q16 对照

### A：稳定旧版

来自首轮原始结果：

- Query：`entropy`
- Top-K：4
- 通过阈值 Chunk：0
- 命中目标论文：0/2
- Tool：`retrieve_paper_evidence`
- 最终回答：证据不足
- 耗时：324.469 秒
- Token：历史记录缺失，不得补为 0

### B：Query Decomposition 实验版

Gate 生成并执行的查询：

```text
1. What specific design strategies does the entropy paper propose for
   optimizing energy storage in ferroelectric materials?
2. How does the PZO domain-modulation paper implement domain engineering
   techniques in fer. electrostatic energy storage systems?
```

两路均通过现有 MCP Tool 执行，`source_filter=false`：

| Query | Top-K | 通过阈值 Chunk | 来源文件 | 耗时 |
|---|---:|---:|---|---:|
| Entropy subquery | 4 | 4 | entropy、PZO、gradient-energy PDF | 2.039 秒 |
| PZO subquery | 4 | 4 | PZO PDF | 0.067 秒 |

合并结果：

- 8 条 Chunk；
- 去重后覆盖 3 篇 PDF；
- 目标来源覆盖 2/2；
- entropy 目标命中：`s41467-025-56194-1.pdf` p.1；
- PZO 目标命中：`1-s2.0-S2352847824001278-main.pdf` p.1、p.2、p.7、p.8。

来源覆盖率由稳定旧版的 `0/2` 提升到 `2/2`。

## 最终回答与耗时

完整实验版在 1200 秒预算内未完成 Writer：

- 已实际执行 Planner、Query Decomposition Gate/Repair、两步检索、
  Executor 和多次 Replanner；
- 第 3 步已经使用真实证据完成两篇论文的比较分析；
- Writer 未在超时前返回，因此没有可验证的 B 组最终回答；
- 超时运行不记录 Token 和完整 LLM 统计，不能把缺失值当成 0。

因此：

- 检索覆盖改善：已确认；
- 最终回答质量改善：未确认；
- 额外耗时：非常明显，至少超过 1200 秒；
- 额外 LLM 成本：Gate 和可能的 Query Repair 增加调用，但超时记录
  无法提供可靠完整总量。

## 其他回归

Gate-only 检查：

- q04：`eligible=false`，单论文问题不会被拆分；
- q09_local_pdf：`eligible=false`，单篇明确 PDF 问题不会被拆分；
- q10：模型曾误判为可拆分，但明确跨来源语义 guardrail 将其关闭；
- q16：明确 compare 两篇论文，`eligible=true`。

q09_local_pdf 的既有真实运行仍选择
`retrieve_paper_evidence`，返回 4 个本地 Chunk。

q10 的既有 Deep 回答仍为“证据不足”，没有产生无依据科学数值。

本次共有 33 项自动化测试通过。

## 结论

当前不建议把自动 Query Decomposition 作为正式默认路径：

1. 它对 q16 的检索来源覆盖确实有效；
2. 但本地 qwen3:4b 生成查询不稳定，需要 Gate 和修复；
3. 完整 Deep 链路出现 1200 秒超时；
4. 中间 Executor 仍可能误读来源，最终答案质量没有完成验收。

建议继续作为独立实验分支，先降低控制节点成本并改进来源映射，再考虑
正式接入。稳定版本继续保持 `--query-decomposition` 关闭。
