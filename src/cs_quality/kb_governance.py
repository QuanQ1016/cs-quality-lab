from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .report import bars, bullets, dashboard, dump_json, dump_markdown

CURRENT_RULES = {
    "return_days": 7,
    "quality_days": 30,
    "buyer_pays_non_quality_shipping": True,
    "ship_hours": 24,
    "couriers": {"中通", "韵达", "圆通"},
    "eta_days": (3, 5),
    "cod": False,
    "paper_invoice": False,
    "invoice_channel": "订单详情页",
    "silver": (2000, "95折"),
    "gold": (8000, "9折"),
    "coupons": {"满200减20", "满500减60"},
    "coupon_stack": False,
    "online_hours": "9:00-22:00",
    "phone_hours": "9:00-18:00",
}


class KbAuditLLM:
    model = "mock-kb-auditor-v1"

    def complete(self, payload: dict[str, Any]) -> str:
        n = payload["issue_count"]
        pri = payload["priority"]
        return (
            f"知识库 {payload['total']} 条中有 {n} 条带问题。"
            f"优先处理会直接造成履约错误的条目：{', '.join(pri)}。"
            "当前业务规则以 2024-06 摘要为准，与之冲突的条目视为过时或错误，而不是‘另一种说法’。"
        )


def load_articles(path: Path) -> list[dict[str, Any]]:
    values = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(values, list) or len(values) != 40:
        raise ValueError("kb_articles.json 必须包含 40 条")
    return values


def _flags_for(article: dict[str, Any], all_articles: list[dict[str, Any]]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    answer = article["answer"].strip()
    q = article["question"]
    aid = article["id"]

    if not answer:
        issues.append({
            "type": "INCOMPLETE",
            "impact": "用户问到会得到空回复，自动回复会编或推诿。",
            "action": "补全答案或下线该条目",
            "detail": "答案为空",
        })
        return issues

    if "货到付款" in q and "支持" in answer and "不支持" not in answer:
        issues.append(_outdated("仍写支持货到付款", "改为不支持货到付款"))
    if "48小时内发货" in answer or "使用顺丰" in answer:
        issues.append(_outdated("发货时效/快递公司与现行 24 小时、中通/韵达/圆通不符", "按现行物流规则改写"))
    if "纸质发票" in answer:
        issues.append(_outdated("仍引导纸质发票/备注开票", "改为订单详情页申请电子发票"))
    if "满1000" in answer or "满5000" in answer or "85折" in answer or "享9折" in answer and "金卡" in answer:
        if "满2000" not in answer:
            issues.append(_outdated("会员门槛或折扣与现行银卡2000/95折、金卡8000/9折不符", "按现行会员规则改写"))
    if "满300减50" in answer or "满600减120" in answer:
        issues.append(_outdated("优惠券面额与现行满200减20、满500减60不符", "更新活动文案"))
    if "叠加3张" in answer or "最多叠加" in answer:
        issues.append(_outdated("现行优惠券不可叠加", "改为不可叠加"))
    if "7x24" in answer or "全天候" in answer:
        issues.append(_outdated("在线客服并非 7x24，现行 9:00-22:00", "改工作时间"))
    if "所有退货的运费都由商家承担" in answer:
        issues.append(_outdated("非质量问题运费应由买家承担", "按质量/非质量拆开写"))
    if "30天无理由" in answer:
        issues.append(_outdated("无理由退货是 7 天不是 30 天", "与 KB001 对齐后删除重复条目"))

    duplicates = [
        other["id"] for other in all_articles
        if other["id"] != aid and other["question"] == q
    ]
    if duplicates:
        issues.append({
            "type": "DUPLICATE",
            "impact": "同一问题多答案时，机器人会随机抓到错误政策。",
            "action": f"与 {', '.join(duplicates)} 合并，只保留现行规则",
            "detail": f"问题全文重复：{q}",
        })

    return issues


def _outdated(detail: str, action: str) -> dict[str, str]:
    return {
        "type": "OUTDATED",
        "impact": "自动回复会按过时规则承诺，造成拒单、投诉或资损。",
        "action": action,
        "detail": detail,
    }


def audit_kb(articles: list[dict[str, Any]], context: str) -> dict[str, Any]:
    if "7 天无理由" not in context:
        raise ValueError("business_context.md 与预期业务规则不符")

    findings = []
    for article in articles:
        issues = _flags_for(article, articles)
        if not issues:
            continue
        severity = "高" if any(item["type"] in {"OUTDATED", "DUPLICATE"} for item in issues) else "中"
        if any(item["type"] == "INCOMPLETE" for item in issues):
            severity = "高"
        findings.append({
            "id": article["id"],
            "question": article["question"],
            "answer": article["answer"],
            "category": article["category"],
            "severity": severity,
            "issues": issues,
            "primary_action": issues[0]["action"],
        })

    coverage_gaps = [
        {
            "id": "GAP-EMAIL",
            "question": "邮件客服多久回复？",
            "reason": "业务规则写明 24 小时内回复，知识库只有在线/电话。",
            "action": "新增条目",
        }
    ]

    type_counts: dict[str, int] = defaultdict(int)
    for item in findings:
        for issue in item["issues"]:
            type_counts[issue["type"]] += 1

    priority = [item["id"] for item in findings if item["severity"] == "高"][:8]
    narrative = KbAuditLLM().complete({
        "total": len(articles),
        "issue_count": len(findings),
        "priority": priority,
    })

    return {
        "mode": "mock",
        "taxonomy": {
            "OUTDATED": "与 2024-06 业务规则冲突，继续用会说错政策。",
            "DUPLICATE": "同一问题多条且答案打架，检索不稳定。",
            "INCOMPLETE": "有标题无答案，等于知识空洞。",
            "COVERAGE_GAP": "现行规则存在但 FAQ 未覆盖。",
        },
        "summary": {
            "total": len(articles),
            "flagged": len(findings),
            "gaps": len(coverage_gaps),
            "type_counts": dict(type_counts),
        },
        "narrative": narrative,
        "priority": priority,
        "findings": findings,
        "coverage_gaps": coverage_gaps,
    }


def write_kb_reports(report: dict[str, Any], output_dir: Path) -> None:
    summary = report["summary"]
    md = [
        "# 知识库条目质量治理",
        "",
        "> 运行模式：现行业务规则对照 + Mock LLM 综述",
        "",
        "## 问题分类",
        *[f"- **{key}**：{desc}" for key, desc in report["taxonomy"].items()],
        "",
        report["narrative"],
        "",
        f"条目 {summary['total']}，有问题 {summary['flagged']}，覆盖缺口 {summary['gaps']}。",
        "",
        "## 优先处理",
        *[f"- {item['id']} {item['question']} → {item['primary_action']}" for item in report["findings"] if item["id"] in report["priority"]],
        "",
        "## 覆盖缺口",
        *[f"- {item['id']}：{item['reason']} → {item['action']}" for item in report["coverage_gaps"]],
    ]
    dump_markdown(output_dir / "report.md", "\n".join(md))
    dump_json(output_dir / "report.json", report)
    page = dashboard(
        title="知识库条目质量治理",
        eyebrow="KNOWLEDGE GOVERNANCE",
        subtitle="过时 / 冲突 / 空答案 / 缺口 · 对照 2024-06 业务规则",
        metrics=[
            ("扫描条目", str(summary["total"])),
            ("问题条目", str(summary["flagged"])),
            ("覆盖缺口", str(summary["gaps"])),
            ("优先处理", str(len(report["priority"]))),
        ],
        panels=[
            ("问题类型", bars(summary["type_counts"])),
            ("治理建议逻辑", bullets([
                "与现行规则冲突 → 修改",
                "同一问题多答案 → 合并，保留新规则",
                "空答案 → 补全或删除",
                "规则有、FAQ 无 → 新增",
            ])),
        ],
        table_title="问题条目清单",
        headers=["ID", "问题", "类型", "建议"],
        rows=[
            [
                item["id"],
                item["question"],
                "、".join(issue["type"] for issue in item["issues"]),
                item["primary_action"],
            ]
            for item in report["findings"]
        ],
        footnote="0112 · 真值来自 business_context.md，不使用外部模型。",
    )
    (output_dir / "dashboard.html").write_text(page, encoding="utf-8")
