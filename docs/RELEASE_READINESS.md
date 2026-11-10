# GitHub Release Readiness

- 检查日期：2026-11-11
- 仓库：ResearchPilot Lite
- 当前分支：`main`
- 当前提交：`d1ea276`
- 远程仓库：未配置
- 状态：**暂缓远程发布**

## 结论

代码、文档、测试和本地演示材料已达到可复现状态，但当前存在两个发布前置问题：

1. 项目自身没有 `LICENSE`，无法确定第三方可以如何使用、修改或再分发。
2. 本机没有可用的 GitHub CLI 登录状态，因此无法确认目标 GitHub 账号。

按照发布门禁，本次没有创建 GitHub 仓库、没有添加 remote、没有 push。

## Git 检查

- 审计开始时工作区：clean
- 分支：`main`
- 本地提交数：19
- 远程：无
- 最近提交：

```text
d1ea276 Add PDF font parsing dependency
5ea035b Show cross-paper metrics without local index
62df669 Handle first-run UI without local PDF index
7717bdd Clarify Python runtime setup
719891e Finalize GitHub release documentation and demos
```

## 敏感内容审查

已检查当前文件和全部 Git 历史：

- 无 API Key、GitHub Token 或私钥模式命中；
- 无个人绝对路径模式命中；
- Git 未跟踪 PDF；
- Git 未跟踪 `.venv`；
- Git 未跟踪 Chroma 数据；
- Git 未跟踪 Ollama 模型；
- 未跟踪超过 500 KB 的 Git blob；
- 环境变量和 Streamlit secrets 已在 `.gitignore` 中排除。

`.gitignore` 当前覆盖：

- `.venv/`、`venv/`
- `__pycache__/`、`*.py[cod]`
- `.env`、`.env.*`、密钥、Token
- `rag/papers/*.pdf`
- `rag/storage/`
- `evaluation/results/*.json`
- `.streamlit/secrets.toml`
- 日志和常见缓存

## 可复现性检查

从最新 Git 归档创建独立临时目录，并使用 Python `3.14.7` 新虚拟环境验证：

- 根 `requirements.txt` 安装成功；
- `pip check` 无冲突；
- 52 项自动化测试通过；
- 在无 PDF、无 Chroma 的干净状态下可启动；
- 复制三篇授权 PDF 后成功生成 145 个 Chunk；
- 没有不可提取文本页面；
- `fonttools==4.68.0` 消除了 pypdf 的 CFF Type1 字体警告；
- Streamlit 从干净环境启动并返回 HTTP 200。

验证完成后临时目录已删除，没有修改项目原索引。

## 演示材料

- `docs/screenshots/pdf-qa.png`
- `docs/screenshots/paper-search.png`
- `docs/screenshots/cross-paper.png`

三张截图均来自真实本地页面，并明确标记为历史演示数据。

## 本地环境

- Python：`3.14.7`
- LangChain：`1.4.7`
- LangGraph：`1.2.17`
- FastMCP：`4.1.6`
- MCP SDK：`2.3.0`
- ChromaDB：`1.5.9`
- Streamlit：`1.67.0`
- pypdf：`7.0.0`
- fonttools：`4.68.0`
- Ollama 模型：`qwen3:4b`、`qwen3-embedding:0.6b`

## 许可证状态

`README.md` 和 `THIRD_PARTY_NOTICES.md` 已准确记录依赖及其许可证。

项目本身的许可证尚未确定，因此当前不能把仓库标为法律意义上的开源项目。
需要仓库所有者明确选择许可证，例如 MIT、Apache-2.0 或其他方案，并添加
根目录 `LICENSE`。

## 计划中的首次发布参数

- Repository name：`ResearchPilot`
- Description：
  `ResearchPilot: A research assistant powered by LangGraph, MCP, RAG and local LLMs.`
- Visibility：`Private`
- Branch：`main`
- Push：尚未执行

目标 GitHub 账号尚不能确认，因为本机没有可用的 `gh` CLI/登录会话。

## 解除阻断后的步骤

在用户明确确认项目许可证后：

```bash
brew install gh
gh auth login
```

认证应由用户在 GitHub 官方设备授权流程中完成，不应向对话提供密码或
Token 明文。

在首次 push 前，仍需再次展示并等待用户确认：

- 目标 GitHub 账号；
- 仓库名称 `ResearchPilot`；
- 可见性 `Private`；
- 将上传的文件列表；
- 当前分支 `main` 和提交 `d1ea276`。

确认后才允许执行：

```bash
gh repo create ResearchPilot \
  --private \
  --source=. \
  --remote=origin \
  --description="ResearchPilot: A research assistant powered by LangGraph, MCP, RAG and local LLMs."
git push -u origin main
```

这些命令本次均未执行。
