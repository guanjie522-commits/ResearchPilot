# ResearchPilot Lite UI 验收报告

- 任务：13-B
- 日期：2026-11-10
- Streamlit：`1.67.0`
- 启动地址：`http://127.0.0.1:8501`
- 运行模式：仅本机

## 页面验收

| 页面 | 打开 | 后端来源 |
|---|---|---|
| PDF 问答 | 通过 | `researchpilot_modes.run_fast_mode` |
| 真实论文检索 | 通过 | `paper_search.search_crossref_papers` |
| 跨论文比较 | 通过 | `cross_paper_qa.run_pipeline` |

Streamlit 服务已实际启动，`GET /` 返回 HTTP 200；AppTest 未发现
页面异常。

## PDF 问答

### q04

- 问题：PZO 相场研究中的三个变量
- 状态：成功
- PDF：`1-s2.0-S2352847824001278-main.pdf`
- 证据：4 条，全部来自所选 PDF
- 引用：`[S4]`，第 1 页
- 耗时：`173.187s`
- 回答正确列出 misfit strain、defect dipoles doping、film thickness

### q10

- 状态：成功
- 证据：0 条
- 回答：“证据不足。”
- 耗时：`10.792s`
- 引用结构检查允许无引用拒答

## Crossref

实际查询：`antiferroelectric energy storage`

- API 状态：成功
- 返回：1 篇
- 标题：`PbZrO3-based antiferroelectric films for energy storage applications`
- 年份：2026
- DOI：`10.70675/6c6b6ce5z31ccz449az88dbzde3d29588ec2`
- 链接：Crossref DOI URL
- 期刊：Crossref 本条记录未提供，页面显示
  `Journal/venue not provided`

该页面明确标注只展示 Crossref metadata，不代表已阅读全文。

## 跨论文比较

使用已有的真实轻量级运行结果验证展示逻辑：

- 状态：`completed_pending_human_review`
- 真实来源：2 篇
- Evidence：5 条正文 Chunk
- LLM 调用：2
- Token：5,493
- 耗时：`357.630s`
- 来源归属校验：通过
- 引用校验：通过

该历史结果只用于展示回归，不计作本次 UI 新一次实时执行。页面实际运行时
会调用 `cross_paper_qa.run_pipeline`，并通过 `source_files` 仅检索用户勾选
的 PDF。

## 交互与安全

- 高成本操作只在表单提交后运行。
- Streamlit rerun 只复用 `session_state` 结果，不自动重新调用模型。
- PDF 清单从索引 manifest 获取，不读取任意本地路径。
- 未发现 API Key、Token 或绝对个人路径暴露。
- 错误和超时使用真实异常/状态显示。
- 无证据时显示“证据不足”，不生成替代来源。
- 跨论文任务预算可设置，页面明确标为实验性。

## 自动化结果

- 44 项自动化测试通过。
- UI AppTest 验证三个 Tab 可渲染。
- q04 与 q10 真实结果可正常显示。
- q16 历史跨论文真实结果可正常显示两张来源表和运行指标。

## 限制

- 跨论文比较仍可能需要约 6 分钟。
- Crossref 元数据可能缺少期刊或摘要。
- 科研准确性和引用之外的科学支持仍需人工审核。
- 无流式 token 展示；只显示真实 spinner 和最终真实耗时。
