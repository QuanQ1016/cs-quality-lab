from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path
from typing import Any

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
    cards = "".join(
        f'<article class="metric"><span>{label}</span><strong>{value:.1%}</strong></article>'
        for label, value in (
            ("准确率", metrics["accuracy"]),
            ("精确率", metrics["precision"]),
            ("召回率", metrics["recall"]),
            ("F1", metrics["f1"]),
        )
    )
    categories = report["category_distribution"]
    maximum = max(categories.values(), default=1)
    bars = "".join(
        '<div class="bar-row">'
        f"<span>{html.escape(name)}</span>"
        f'<div class="track"><i style="width:{count / maximum * 100:.1f}%"></i></div>'
        f"<b>{count}</b></div>"
        for name, count in sorted(categories.items(), key=lambda item: -item[1])
    )
    rows = "".join(
        "<tr>"
        f"<td><code>{row['id']}</code></td>"
        f"<td>{html.escape(row['question'])}</td>"
        f"<td><span class=\"pill {row['severity']}\">{html.escape(row['category'] or '通过')}</span></td>"
        f"<td>{row['confidence']:.0%}</td>"
        f"<td class=\"{row['outcome'].lower()}\">{row['outcome']}</td>"
        "</tr>"
        for row in report["cases"]
    )
    payload = html.escape(json.dumps(report, ensure_ascii=False))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hallucination Guard · 检测报告</title>
<style>
:root{{--ink:#172033;--muted:#667085;--paper:#f4f6f9;--card:#fff;--navy:#14213d;
--blue:#356ae6;--cyan:#2bb5a8;--red:#d64550;--amber:#d98e04}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);
font:14px/1.5 Inter,"Segoe UI","Microsoft YaHei",sans-serif}}
.top{{background:var(--navy);color:white;padding:42px max(6vw,24px) 78px}}
.eyebrow{{color:#89a9f5;letter-spacing:.14em;font-size:12px;font-weight:700}}
h1{{font-size:34px;margin:8px 0}} .top p{{color:#bdc7dc;margin:0}}
main{{max-width:1180px;margin:-48px auto 56px;padding:0 24px}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}}
.metric,.panel{{background:var(--card);border:1px solid #e7eaf0;border-radius:14px;
box-shadow:0 8px 24px #14213d0d}} .metric{{padding:22px}}
.metric span{{display:block;color:var(--muted)}} .metric strong{{font-size:30px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}}
.panel{{padding:24px}} h2{{font-size:18px;margin:0 0 18px}}
.matrix{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
.matrix div{{padding:16px;border-radius:10px;background:#f7f9fc}}
.matrix b{{display:block;font-size:24px}} .bar-row{{display:grid;
grid-template-columns:150px 1fr 24px;gap:10px;align-items:center;margin:11px 0}}
.track{{height:9px;background:#edf0f5;border-radius:9px;overflow:hidden}}
.track i{{display:block;height:100%;background:linear-gradient(90deg,var(--blue),var(--cyan));
border-radius:9px}} .table-wrap{{overflow:auto}} table{{width:100%;border-collapse:collapse}}
th,td{{padding:12px 10px;text-align:left;border-bottom:1px solid #edf0f5}}
th{{color:var(--muted);font-size:12px}} code{{color:var(--blue)}}
.pill{{display:inline-block;padding:3px 8px;border-radius:99px;background:#edf2ff;color:#2857bf}}
.pill.critical{{background:#ffe8ea;color:#a72530}} .pill.high{{background:#fff1d6;color:#935f00}}
.pill.none{{background:#dcf7ed;color:#08765d}} .tp,.tn{{color:#08765d;font-weight:700}}
.fp,.fn{{color:var(--red);font-weight:700}} .wide{{margin-top:18px}}
.foot{{color:var(--muted);font-size:12px;margin-top:18px}}
@media(max-width:760px){{.metrics,.grid{{grid-template-columns:1fr 1fr}}}}
@media(max-width:500px){{.metrics,.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header class="top"><div class="eyebrow">EVIDENCE-GROUNDED QA</div>
<h1>客服回复幻觉检测</h1><p>Mock LLM · 证据约束 · 全链路可复现</p></header>
<main><section class="metrics">{cards}</section>
<section class="grid"><article class="panel"><h2>混淆矩阵</h2><div class="matrix">
<div><span>真阳性 TP</span><b>{metrics['tp']}</b></div>
<div><span>误报 FP</span><b>{metrics['fp']}</b></div>
<div><span>漏检 FN</span><b>{metrics['fn']}</b></div>
<div><span>真阴性 TN</span><b>{metrics['tn']}</b></div></div></article>
<article class="panel"><h2>风险类型分布</h2>{bars}</article></section>
<section class="panel wide"><h2>20 条回复审计明细</h2><div class="table-wrap"><table>
<thead><tr><th>ID</th><th>用户问题</th><th>检测结论</th><th>置信度</th><th>验证</th></tr></thead>
<tbody>{rows}</tbody></table></div></section>
<p class="foot">报告由 Hallucination Guard 生成。嵌入数据校验值：{len(payload)} chars。</p>
</main></body></html>"""
