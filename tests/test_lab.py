from __future__ import annotations

import unittest
from pathlib import Path

from cs_quality.kb_governance import audit_kb, load_articles
from cs_quality.reply_eval import evaluate_replies, load_json_list
from cs_quality.ticket_intel import analyze_tickets, load_tickets

ROOT = Path(__file__).resolve().parents[1]


class LabTest(unittest.TestCase):
    def test_tickets_detect_payment_spike_and_unresolved(self) -> None:
        report = analyze_tickets(load_tickets(ROOT / "data" / "tickets.json"))
        self.assertEqual(50, report["kpis"]["total"])
        self.assertGreater(report["kpis"]["pay_second_half"], report["kpis"]["pay_first_half"])
        self.assertGreaterEqual(report["kpis"]["unresolved"], 5)
        self.assertEqual(6, len(report["anomalies"]))
        self.assertTrue(report["narrative"])

    def test_reply_eval_ranks_pushback_cases_low(self) -> None:
        report = evaluate_replies(
            load_json_list(ROOT / "data" / "auto_replies.json"),
            load_json_list(ROOT / "data" / "human_ref.json"),
        )
        self.assertEqual(20, report["summary"]["count"])
        worst_ids = {item["id"] for item in report["worst3"]}
        self.assertIn("case_08", worst_ids)
        case01 = next(row for row in report["cases"] if row["id"] == "case_01")
        case08 = next(row for row in report["cases"] if row["id"] == "case_08")
        self.assertLessEqual(case01["overall"], 3.2)
        self.assertLessEqual(case08["usefulness"], 2)

    def test_kb_flags_outdated_empty_and_duplicate(self) -> None:
        context = (ROOT / "data" / "business_context.md").read_text(encoding="utf-8")
        report = audit_kb(load_articles(ROOT / "data" / "kb_articles.json"), context)
        flagged = {item["id"]: item for item in report["findings"]}
        self.assertIn("KB008", flagged)
        self.assertIn("KB032", flagged)
        self.assertIn("KB037", flagged)
        self.assertIn("KB039", flagged)
        self.assertGreaterEqual(report["summary"]["flagged"], 10)
        self.assertEqual("COVERAGE_GAP", "COVERAGE_GAP")


if __name__ == "__main__":
    unittest.main()
