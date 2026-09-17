from __future__ import annotations

import argparse
import sys
from pathlib import Path

from hallucination_guard.cli import main as run_hallucination
from .kb_governance import audit_kb, load_articles, write_kb_reports
from .reply_eval import evaluate_replies, load_json_list, write_reply_reports
from .ticket_intel import analyze_tickets, load_tickets, write_ticket_reports
from .theme import page_foot, page_head


ROOT = Path.cwd()


def _index_html() -> str:
    arrow = (
        '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">'
        '<path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )
    tasks = [
        ("0110", "幻觉检测", "20 条回复对照知识库，输出精确率与召回率", "0110-hallucination/dashboard.html"),
        ("0109", "自动回复质量", "准确 / 有用 / 语气 / 不瞎编，四维打分", "0109-reply-eval/dashboard.html"),
        ("0111", "工单趋势", "50 条工单的趋势、异常与未关闭清单", "0111-tickets/dashboard.html"),
        ("0112", "知识库治理", "过时、重复、空答案与覆盖缺口", "0112-kb/dashboard.html"),
    ]
    links = "".join(
        f'<a class="task reveal" style="--d:{index + 2}" href="{href}">'
        f'<div class="code">{code}</div>'
        f"<div><b>{title}</b><span>{desc}</span></div>{arrow}</a>"
        for index, (code, title, desc, href) in enumerate(tasks)
    )
    return (
        page_head("客服 AI 质量实验室")
        + f"""<div class="index-wrap">
<div class="eyebrow reveal">CS QUALITY LAB · MOCK LLM</div>
<h1 class="reveal" style="--d:1">客服 AI 质量实验室</h1>
<p class="reveal" style="--d:1">四题共用 Mock LLM。点进各报告查看指标、异常和逐条结果。</p>
{links}
</div>"""
        + page_foot()
    )


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
