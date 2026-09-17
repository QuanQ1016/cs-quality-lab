from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path
from typing import Any

from cs_quality.report import bars as report_bars
from cs_quality.report import dashboard

from .core import Detection, ReplyCase


def load_cases(path: Path) -> list[ReplyCase]:
    with path.open(encoding="utf-8") as file:
        values = json.load(file)
    if not isinstance(values, list):
        raise ValueError("输入数据顶层必须是数组")
    cases = [ReplyCase.from_dict(value) for value in values]
    ids = [case.id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("输入数据包含重复 id")
    return cases


def load_ground_truth(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8") as file:
        values = json.load(file)
    if not isinstance(values, list):
        raise ValueError("ground truth 顶层必须是数组")
    return {value["id"]: value for value in values}


def evaluate(
    cases: list[ReplyCase],
    detections: list[Detection],
    ground_truth: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    case_by_id = {case.id: case for case in cases}
    predicted = {item.id: item for item in detections}
    if set(case_by_id) != set(predicted) or set(case_by_id) != set(ground_truth):
        raise ValueError("输入、检测结果与 ground truth 的 id 集合必须一致")

    tp = fp = tn = fn = 0
    rows: list[dict[str, Any]] = []
    for case_id in case_by_id:
        detection = predicted[case_id]
        expected = bool(ground_truth[case_id]["is_hallucination"])
        actual = detection.is_hallucination
        outcome = "TP" if actual and expected else "FP" if actual else "FN" if expected else "TN"
        tp += outcome == "TP"
        fp += outcome == "FP"
        tn += outcome == "TN"
        fn += outcome == "FN"
        rows.append(
            {
                **detection.to_dict(),
                "expected": expected,
                "outcome": outcome,
                "question": case_by_id[case_id].user_question,
                "reference_type": ground_truth[case_id].get("hallucination_type"),
            }
        )

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    metrics = {
        "total": len(rows),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": _safe_div(tp + tn, len(rows)),
        "precision": precision,
        "recall": recall,
        "f1": _safe_div(2 * precision * recall, precision + recall),
    }
    category_counts = Counter(row["category"] or "通过" for row in rows)
    severity_counts = Counter(row["severity"] for row in rows)
    return {
        "mode": "mock",
        "metrics": metrics,
        "category_distribution": dict(category_counts),
        "severity_distribution": dict(severity_counts),
        "false_positives": [row["id"] for row in rows if row["outcome"] == "FP"],
        "false_negatives": [row["id"] for row in rows if row["outcome"] == "FN"],
        "cases": rows,
    }


def write_reports(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(_markdown(report), encoding="utf-8")
    (output_dir / "dashboard.html").write_text(_html(report), encoding="utf-8")


def _safe_div(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# 客服回复幻觉检测报告",
        "",
        "> 运行模式：Mock LLM（离线、确定性、可复现）",
        "",
        "## 核心指标",
        "",
        f"- 样本数：{metrics['total']}",
        f"- Accuracy：{metrics['accuracy']:.2%}",
        f"- Precision：{metrics['precision']:.2%}",
        f"- Recall：{metrics['recall']:.2%}",
        f"- F1：{metrics['f1']:.2%}",
        f"- 混淆矩阵：TP={metrics['tp']} / FP={metrics['fp']} / "
        f"TN={metrics['tn']} / FN={metrics['fn']}",
        "",
        "## 逐条结果",
        "",
        "| ID | 预测 | 分类 | 严重度 | 置信度 | 验证 |",
        "|---|---|---|---|---:|---|",
    ]
    for row in report["cases"]:
        prediction = "幻觉" if row["is_hallucination"] else "通过"
        lines.append(
            f"| {row['id']} | {prediction} | {row['category'] or '-'} | "
            f"{row['severity']} | {row['confidence']:.0%} | {row['outcome']} |"
        )
    lines.extend(
        [
            "",
            "## 误判",
            "",
            f"- 误报：{', '.join(report['false_positives']) or '无'}",
            f"- 漏检：{', '.join(report['false_negatives']) or '无'}",
            "",
        ]
    )
    return "\n".join(lines)


def _html(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    matrix = (
        '<div class="matrix">'
        f"<div><span>真阳性 TP</span><b>{metrics['tp']}</b></div>"
        f"<div><span>误报 FP</span><b>{metrics['fp']}</b></div>"
        f"<div><span>漏检 FN</span><b>{metrics['fn']}</b></div>"
        f"<div><span>真阴性 TN</span><b>{metrics['tn']}</b></div>"
        "</div>"
    )
    payload = html.escape(json.dumps(report, ensure_ascii=False))
    return dashboard(
        title="客服回复幻觉检测",
        eyebrow="EVIDENCE-GROUNDED QA",
        subtitle="Mock LLM · 证据约束 · 全链路可复现",
        metrics=[
            ("准确率", f"{metrics['accuracy']:.1%}"),
            ("精确率", f"{metrics['precision']:.1%}"),
            ("召回率", f"{metrics['recall']:.1%}"),
            ("F1", f"{metrics['f1']:.1%}"),
        ],
        panels=[
            ("混淆矩阵", matrix),
            (
                "风险类型分布",
                report_bars(
                    dict(
                        sorted(
                            report["category_distribution"].items(),
                            key=lambda item: -item[1],
                        )
                    )
                ),
            ),
        ],
        table_title="20 条回复审计明细",
        headers=["ID", "用户问题", "检测结论", "置信度", "验证"],
        rows=[
            [
                f"<code>{row['id']}</code>",
                html.escape(row["question"]),
                (
                    f"<span class=\"pill {row['severity']}\">"
                    f"{html.escape(row['category'] or '通过')}</span>"
                ),
                f"{row['confidence']:.0%}",
                f"<span class=\"{row['outcome'].lower()}\">{row['outcome']}</span>",
            ]
            for row in report["cases"]
        ],
        footnote=f"报告由 Hallucination Guard 生成。嵌入数据校验值：{len(payload)} chars。",
    )
