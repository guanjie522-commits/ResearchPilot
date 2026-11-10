# 轻量级跨论文问答实验报告

- 任务：12-I
- 日期：2026-11-10
- 独立入口：`cross_paper_qa.py`
- q16 结果：
  `evaluation/results/cross_paper_qa_20261110T095522Z.json`
- 12-H 超时记录：
  `evaluation/results/benchmark_20261110T090436Z.json`

## 12-H 超时瓶颈

可靠记录：

- 完整 Deep 实验在 `1200.014` 秒后超时；
- 超时记录没有保存分节点 profiler 数据，因此 Planner、Executor、
  Replanner、Gate 的精确耗时均标为 `unavailable`；
- 实际终端轨迹显示实验已经进入第 3 个 Executor 步骤，但未进入 Writer；
- 阻塞发生在多轮顺序 LLM 控制流程，而不是 Chroma 或 MCP 调用；
- Chroma/MCP 单次检索通常仅约 0.05–3 秒，主要时间由 qwen3:4b
  的 Planner、Executor、Replanner 推理占用。

因此不能把 1200 秒全部归因于 Query Decomposition；它是额外的 Gate
开销，但原来的多节点 Deep 循环是主要结构性问题。

## 轻量执行结构

```text
Question
  -> Query Decomposition Gate（最多 2 条查询）
  -> 现有 Chroma Retriever
  -> 两次独立检索
  -> 按 source_file + chunk_id 去重
  -> 过滤明显 references-list Chunk
  -> Evidence Registry
  -> 一次 Qwen 结构化生成
  -> 程序验证 P# 与 S# 来源归属
  -> 程序渲染文件名、页码和引用索引
```

没有 Planner、Replanner、循环重试或新的 Agent 框架。

## q16 真实结果

子查询：

```text
1. How does the entropy paper describe the primary design methodology
   for optimizing energy storage in ferroelectric materials?
2. What is the main design approach for the PZO domain-modulation paper
   in enhancing storage performance through domain engineering?
```

检索执行：

- Chroma Retriever 调用：2
- source filter：均未启用
- 原始 Chunk：8
- 排除的 references-list Chunk：3
- Evidence Registry Chunk：5
- 覆盖论文：2
- 来源覆盖率：2/2

Retriever 已支持默认关闭的 `source_file` metadata filter。只有问题中明确
出现且只出现一个 PDF 文件名时才自动启用；q16 没有明确文件名，因此本次
结果不包含 source filter 带来的收益。

程序建立的来源映射：

| Paper code | Source file |
|---|---|
| P1 | `1-s2.0-S2352847824001278-main.pdf` |
| P2 | `s41467-025-56194-1.pdf` |

最终回答成功生成，核心内容为：

- P2 熵论文：通过增加熵同时打破长程反铁电序并局部调整四重调制结构；
- P1 PZO 论文：通过薄膜域工程调控基底应变、缺陷偶极浓度和薄膜厚度；
- 比较：熵论文侧重熵增加机制，PZO 论文侧重多参数域工程优化。

最终回答中的来源信息全部由程序根据 Evidence Registry 生成，没有使用模型
手写的文件名或页码。

## 来源错配修复

模型输出必须为每条 paper claim 提供：

- `paper_code`；
- `evidence_ids`。

程序验证：

- Evidence ID 必须真实存在；
- claim 的 `paper_code` 必须等于其 Evidence 的 source_file 映射；
- comparison point 引用的 paper code 必须包含真实来源；
- 模型输出中出现 PDF 文件名时直接判为无效；
- 最终文件名、页码和引用索引由程序生成。

测试明确覆盖了 entropy Chunk 被错误标成 PZO 的场景，验证器会拒绝。

## 性能与 Token

| 指标 | 实际值 |
|---|---:|
| 总耗时 | 357.630 秒 |
| LLM 调用 | 2 |
| QueryDecomposition Gate | 6.517 秒 / 490 tokens |
| 最终结构化生成 | 347.787 秒 / 5,003 tokens |
| 总 Token | 5,493 |
| 本地检索 | 约 3.283 秒 |

最终 Qwen 生成仍是主要耗时点，但流程从多轮 Deep 循环降为 2 次 LLM
调用，并在 420 秒实验预算内完成。

## 回答质量检查

- Entropy 与 PZO 来源区分正确；
- 两条 paper claim 分别绑定正确 PDF；
- 引用 ID 和来源映射校验通过；
- 未发现编造 DOI、页码或额外论文；
- 最终回答对 PZO 的 description 提到域工程，但没有在正文明确写出
  phase-field simulation，仍需人工检查是否构成方法描述遗漏；
- 科学正确性保持 `pending_human_review`。

## 回归检查

- q04 单论文答案归一化测试通过；
- q09_local_pdf 历史真实运行仍为 `retrieve_paper_evidence`，4 条本地证据；
- q10 历史 Deep 回答仍为“证据不足”；
- q09 的“常系数 vs 各向同性”术语检查案例已加入人工审核摘要；
- 所有五道题的审核状态仍为 `pending_human_review`；
- 41 项自动化测试通过。

## 建议

轻量跨论文流程值得作为可选模式保留，但暂不建议替换主 Deep Agent：

1. 它解决了 q16 的来源覆盖与来源错配；
2. 它把调用链缩减为最多 2 次检索和 2 次 LLM；
3. 但单次生成仍需约 348 秒，并存在方法描述遗漏风险；
4. 应先人工审核 q16 答案，再决定是否接入主架构。

稳定 ResearchPilot 默认行为、阈值、Embedding、Chunking 和原始
Benchmark 数据均未修改。
