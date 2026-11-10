import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class DocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cls.requirements = (ROOT / "requirements.txt").read_text(
            encoding="utf-8"
        )
        cls.gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    def test_readme_contains_required_sections(self):
        required = [
            "项目介绍",
            "核心功能",
            "技术栈",
            "系统架构",
            "目录结构",
            "本地安装",
            "Ollama 模型准备",
            "Streamlit 启动",
            "建立 PDF 知识库",
            "论文检索",
            "Fast / Deep 模式",
            "Benchmark 与真实性能记录",
            "已知限制",
            "开源依赖与许可证",
            "项目后续方向",
        ]
        for heading in required:
            self.assertIn(heading, self.readme)

    def test_readme_mermaid_covers_real_components(self):
        self.assertIn("```mermaid", self.readme)
        for component in (
            "Streamlit UI",
            "Fast Mode",
            "Lightweight Cross-Paper QA",
            "Deep Mode",
            "MCP Client",
            "FastMCP Server",
            "LangGraph",
            "Chroma",
            "Evidence Registry",
            "Citation Validation",
        ):
            self.assertIn(component, self.readme)

    def test_requirements_pin_direct_dependencies(self):
        for package in (
            "langchain==",
            "langchain-core==",
            "langchain-ollama==",
            "langgraph==",
            "fastmcp==",
            "mcp==",
            "chromadb==",
            "pypdf==",
            "requests==",
            "streamlit==",
            "pydantic==",
        ):
            self.assertIn(package, self.requirements)

    def test_sensitive_local_artifacts_are_ignored(self):
        for entry in (
            ".venv/",
            "__pycache__/",
            ".env",
            "rag/papers/*.pdf",
            "rag/storage/",
            "evaluation/results/*.json",
            ".streamlit/secrets.toml",
        ):
            self.assertIn(entry, self.gitignore)

    def test_public_docs_do_not_contain_absolute_user_paths(self):
        docs = [ROOT / "README.md"]
        docs.extend((ROOT / "docs").rglob("*.md"))
        docs.append(ROOT / "THIRD_PARTY_NOTICES.md")
        for path in docs:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("/Users/", text, msg=str(path))

    def test_readme_relative_markdown_links_exist(self):
        for target in re.findall(r"\]\(([^)]+)\)", self.readme):
            if target.startswith(("http://", "https://", "#")):
                continue
            self.assertTrue((ROOT / target).exists(), msg=target)


if __name__ == "__main__":
    unittest.main()
