import unittest
import json
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[2]


class ResearchPilotUITests(unittest.TestCase):
    def test_app_renders_all_three_tabs_without_running_tasks(self):
        app = AppTest.from_file(
            str(ROOT / "ui" / "app.py"),
            default_timeout=20,
        )
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.title[0].value, "ResearchPilot Lite")
        self.assertEqual(
            [tab.label for tab in app.tabs],
            ["PDF 问答", "真实论文检索", "跨论文比较"],
        )
        self.assertEqual(
            [button.label for button in app.button],
            [
                "运行 PDF 问答",
                "搜索 Crossref",
                "运行跨论文比较",
            ],
        )

    def test_real_q04_and_cross_paper_results_render_in_ui(self):
        pdf_results = json.loads(
            (ROOT / "evaluation" / "results" / "ui_smoke_fast_20261110.json")
            .read_text(encoding="utf-8")
        )
        cross_result = json.loads(
            (
                ROOT
                / "evaluation"
                / "results"
                / "cross_paper_qa_20261110T095522Z.json"
            ).read_text(encoding="utf-8")
        )
        app = AppTest.from_file(
            str(ROOT / "ui" / "app.py"),
            default_timeout=20,
        )
        app.session_state["pdf_qa_result"] = pdf_results[0]
        app.session_state["cross_paper_result"] = cross_result
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.dataframe), 2)
        metric_labels = [metric.label for metric in app.metric]
        self.assertIn("耗时", metric_labels)
        self.assertIn("来源数", metric_labels)

    def test_q10_insufficient_evidence_result_renders_without_sources(self):
        pdf_results = json.loads(
            (ROOT / "evaluation" / "results" / "ui_smoke_fast_20261110.json")
            .read_text(encoding="utf-8")
        )
        app = AppTest.from_file(
            str(ROOT / "ui" / "app.py"),
            default_timeout=20,
        )
        app.session_state["pdf_qa_result"] = pdf_results[1]
        app.run()

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(
            any("证据不足" in item.value for item in app.markdown)
        )
        self.assertEqual(len(app.dataframe), 0)

    def test_historical_demo_query_parameters_do_not_run_tasks(self):
        for kind, expected in (
            ("pdf", "历史演示数据"),
            ("paper", "Crossref 返回"),
            ("cross", "最终比较"),
        ):
            with self.subTest(kind=kind):
                app = AppTest.from_file(
                    str(ROOT / "ui" / "app.py"),
                    default_timeout=20,
                )
                app.query_params["demo"] = kind
                app.run()
                self.assertEqual(len(app.exception), 0)
                self.assertTrue(
                    any(
                        expected in item.value
                        for item in [
                            *app.markdown,
                            *app.caption,
                            *app.info,
                            *app.subheader,
                        ]
                    )
                )


if __name__ == "__main__":
    unittest.main()
