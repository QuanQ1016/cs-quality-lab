from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hallucination_guard.core import HallucinationDetector, MockLLMClient, ReplyCase
from hallucination_guard.evaluation import (
    evaluate,
    load_cases,
    load_ground_truth,
    write_reports,
)


ROOT = Path(__file__).resolve().parents[1]


class DetectorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.detector = HallucinationDetector()

    def test_capability_fabrication_is_critical_or_high(self) -> None:
        case = ReplyCase(
            id="capability",
            user_question="退款到哪了？",
            system_reply="我帮您查了，明天到账。",
            knowledge_base="客服系统未接入退款进度查询接口。",
        )
        result = self.detector.detect(case)
        self.assertTrue(result.is_hallucination)
        self.assertEqual("TOOL_USE_FABRICATION", result.category)
        self.assertIn(result.severity, {"high", "critical"})

    def test_grounded_answer_passes(self) -> None:
        case = ReplyCase(
            id="grounded",
            user_question="支持货到付款吗？",
            system_reply="不支持货到付款，支持微信和支付宝。",
            knowledge_base="支持微信和支付宝，不支持货到付款。",
        )
        result = self.detector.detect(case)
        self.assertFalse(result.is_hallucination)
        self.assertIsNone(result.category)

    def test_mock_rejects_prompt_without_evidence_constraint(self) -> None:
        with self.assertRaises(ValueError):
            MockLLMClient().complete(
                system_prompt="随便判断",
                payload={
                    "id": "x",
                    "user_question": "问题",
                    "system_reply": "回答",
                    "knowledge_base": "证据",
                },
            )

    def test_full_dataset_and_reports(self) -> None:
        cases = load_cases(ROOT / "data" / "replies.json")
        truth = load_ground_truth(ROOT / "data" / "ground_truth.json")
        report = evaluate(cases, self.detector.detect_many(cases), truth)
        self.assertEqual(20, report["metrics"]["total"])
        self.assertGreaterEqual(report["metrics"]["recall"], 0.9)
        self.assertGreaterEqual(report["metrics"]["precision"], 0.9)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            write_reports(report, output)
            self.assertTrue((output / "dashboard.html").exists())
            saved = json.loads((output / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["metrics"], saved["metrics"])


if __name__ == "__main__":
    unittest.main()
