from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hallucination_guard.cli import main as run_hallucination
from .kb_governance import audit_kb, load_articles, write_kb_reports
from .reply_eval import evaluate_replies, load_json_list, write_reply_reports
from .ticket_intel import analyze_tickets, load_tickets, write_ticket_reports


ROOT = Path.cwd()


def _index_html() -> str:
    return """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>客服 AI 质量实验室</title>
<style>
body{margin:0;font:16px/1.5 Inter,"Segoe UI","Microsoft YaHei",sans-serif;background:#f4f6f9;color:#172033}
main{max-width:880px;margin:48px auto;padding:0 24px}
a.card{display:block;background:#fff;border:1px solid #e7eaf0;border-radius:16px;padding:22px;margin:14px 0;text-decoration:none;color:inherit}
a.card:hover{border-color:#356ae6}
h1{font-size:32px} p{color:#667085}
</style></head>
<body><main>
<h1>客服 AI 质量实验室</h1>
<p>四题共用 Mock LLM。点进各报告查看指标、异常和逐条结果。</p>
<a class="card" href="0110-hallucination/dashboard.html"><b>0110 幻觉检测</b><br>20 条回复 vs 知识库，精确率/召回率</a>
<a class="card" href="0109-reply-eval/dashboard.html"><b>0109 自动回复质量</b><br>准确 / 有用 / 语气 / 不瞎编</a>
<a class="card" href="0111-tickets/dashboard.html"><b>0111 工单趋势</b><br>50 条工单的趋势、异常、未关闭清单</a>
<a class="card" href="0112-kb/dashboard.html"><b>0112 知识库治理</b><br>过时、重复、空答案与覆盖缺口</a>
</main></body></html>
"""


def run_0110() -> int:
    return run_hallucination([
        "--input", str(ROOT / "data" / "replies.json"),
        "--ground-truth", str(ROOT / "data" / "ground_truth.json"),
        "--output", str(ROOT / "reports" / "0110-hallucination"),
    ])


def run_0109() -> None:
    report = evaluate_replies(
        load_json_list(ROOT / "data" / "auto_replies.json"),
        load_json_list(ROOT / "data" / "human_ref.json"),
    )
    write_reply_reports(report, ROOT / "reports" / "0109-reply-eval")
    print(f"0109 整体得分 {report['summary']['overall']}/5，"
          f"最差：{', '.join(item['id'] for item in report['worst3'])}")


def run_0111() -> None:
    report = analyze_tickets(load_tickets(ROOT / "data" / "tickets.json"))
    write_ticket_reports(report, ROOT / "reports" / "0111-tickets")
    print(f"0111 工单 {report['kpis']['total']}，未关闭 {report['kpis']['unresolved']}，"
          f"异常 {len(report['anomalies'])} 条")


def run_0112() -> None:
    context = (ROOT / "data" / "business_context.md").read_text(encoding="utf-8")
    report = audit_kb(load_articles(ROOT / "data" / "kb_articles.json"), context)
    write_kb_reports(report, ROOT / "reports" / "0112-kb")
    print(f"0112 扫描 {report['summary']['total']}，问题条目 {report['summary']['flagged']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运行客服 AI 质量实验室（Mock LLM）。")
    parser.add_argument("--task", choices=["all", "0109", "0110", "0111", "0112"], default="all")
    args = parser.parse_args(argv)
    try:
        tasks = [args.task] if args.task != "all" else ["0110", "0109", "0111", "0112"]
        runners = {"0110": run_0110, "0109": run_0109, "0111": run_0111, "0112": run_0112}
        for task in tasks:
            result = runners[task]()
            if result not in (None, 0):
                return int(result)
        index = ROOT / "reports" / "index.html"
        index.write_text(_index_html(), encoding="utf-8")
        print(f"总览: {index.resolve()}")
        return 0
    except (OSError, ValueError) as error:
        print(f"运行失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
