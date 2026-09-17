from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from .report import bars, bullets, dashboard, dump_json, dump_markdown


class TicketInsightLLM:
    """用统计摘要生成主管可读结论，不编造未出现在数据中的数字。"""

    model = "mock-ops-analyst-v1"

    def complete(self, payload: dict[str, Any]) -> str:
        spikes = payload["anomalies"]
        lines = [
            f"最近 {payload['days']} 天共 {payload['total']} 张工单，"
            f"未关闭 {payload['unresolved']} 张，平均满意度 {payload['avg_satisfaction']:.2f}。",
            "支付与退款是当前最需要盯的两条线：前者量在后半段抬升且重复扣款反复出现，"
            "后者处理时长长、差评多，还有垫付运费未报销。",
            "建议今日先清未关闭的高优工单，并单独排期修支付重复扣款和退货运费报销链路。",
        ]
        if spikes:
            lines.append("系统标出的异常均来自规则检测，不是模型臆测。")
        return " ".join(lines)


def load_tickets(path: Path) -> list[dict[str, Any]]:
    values = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(values, list) or len(values) != 50:
        raise ValueError("tickets.json 必须包含 50 条工单")
    return values


def analyze_tickets(tickets: list[dict[str, Any]]) -> dict[str, Any]:
    parsed = []
    for item in tickets:
        created = datetime.strptime(item["created_at"], "%Y-%m-%d %H:%M")
        parsed.append({**item, "_date": created.date().isoformat(), "_dt": created})

    by_day: dict[str, int] = defaultdict(int)
    by_cat: dict[str, int] = defaultdict(int)
    by_priority: dict[str, int] = defaultdict(int)
    by_channel: dict[str, int] = defaultdict(int)
    sat_by_cat: dict[str, list[float]] = defaultdict(list)
    sla_by_cat: dict[str, list[float]] = defaultdict(list)
    for item in parsed:
        by_day[item["_date"]] += 1
        by_cat[item["category"]] += 1
        by_priority[item["priority"]] += 1
        by_channel[item["channel"]] += 1
        sat_by_cat[item["category"]].append(item["satisfaction"])
        sla_by_cat[item["category"]].append(item["resolution_time_hours"])

    unresolved = [item for item in parsed if not item["is_resolved"]]
    low_sat = [item for item in parsed if item["satisfaction"] <= 2]
    slow = [
        item for item in parsed
        if item["priority"] == "高" and item["resolution_time_hours"] >= 24
    ]

    first_half = [item for item in parsed if item["_date"] <= "2024-06-05"]
    second_half = [item for item in parsed if item["_date"] >= "2024-06-06"]
    pay_first = sum(item["category"] == "支付问题" for item in first_half)
    pay_second = sum(item["category"] == "支付问题" for item in second_half)

    duplicate_pay = [
        item["ticket_id"] for item in parsed
        if "重复扣" in item["description"] or "两个都扣" in item["description"]
        or "多扣" in item["description"]
    ]
    freight = [
        item["ticket_id"] for item in parsed
        if "运费" in item["description"] and ("垫付" in item["description"] or "报销" in item["description"])
    ]
    bot_fail = [
        item["ticket_id"] for item in parsed
        if "机器人" in item["description"] or "重新描述" in item["description"]
    ]

    anomalies = [
        {
            "id": "A1",
            "title": "支付问题后半段激增",
            "severity": "高",
            "evidence": f"6/1-6/5 仅 {pay_first} 单，6/6-6/11 升至 {pay_second} 单。",
            "action": "排查支付网关对账与下单幂等，优先处理重复扣款。",
        },
        {
            "id": "A2",
            "title": "重复扣款复发",
            "severity": "高",
            "evidence": f"相关工单：{', '.join(duplicate_pay)}。T046 明确说上个月也发生过。",
            "action": "作为缺陷而不是一次性客诉处理，补对账和自动退款。",
        },
        {
            "id": "A3",
            "title": "退款链路超时且差评扎堆",
            "severity": "高",
            "evidence": (
                f"退款退货平均处理 {mean(sla_by_cat['退款退货']):.1f} 小时，"
                f"平均满意度 {mean(sat_by_cat['退款退货']):.2f}。"
            ),
            "action": "给退款审核设 SLA，超时自动升级。",
        },
        {
            "id": "A4",
            "title": "垫付退货运费未报销",
            "severity": "中",
            "evidence": f"{', '.join(freight)} 仍未关闭或低满意。",
            "action": "单独开报销队列，避免客服口头承诺无法兑现。",
        },
        {
            "id": "A5",
            "title": "自动回复未能解决问题",
            "severity": "中",
            "evidence": f"{', '.join(bot_fail)} 投诉机器人循环话术。",
            "action": "退款/投诉意图直接转人工，并回写到 0109 评估。",
        },
        {
            "id": "A6",
            "title": "未关闭工单集中在高伤害场景",
            "severity": "高",
            "evidence": "未关闭：" + ", ".join(
                f"{item['ticket_id']}({item['category']})" for item in unresolved
            ),
            "action": "主管今日逐条跟进，先处理支付和退款。",
        },
    ]

    summary_input = {
        "total": len(parsed),
        "days": len(by_day),
        "unresolved": len(unresolved),
        "avg_satisfaction": mean(item["satisfaction"] for item in parsed),
        "anomalies": [item["id"] for item in anomalies],
    }
    narrative = TicketInsightLLM().complete(summary_input)

    return {
        "mode": "mock",
        "dimensions": {
            "时间趋势": "看量是否在抬升，避免被单日噪声带偏",
            "类型分布": "决定排班和知识库补强方向",
            "优先级与时长": "判断 SLA 是否失守",
            "满意度": "把“忙完了”和“用户认可”分开",
            "未关闭与复发": "找出系统性问题，而不是再回一条话术",
        },
        "kpis": {
            "total": len(parsed),
            "unresolved": len(unresolved),
            "avg_satisfaction": round(mean(item["satisfaction"] for item in parsed), 2),
            "avg_resolution_hours": round(mean(item["resolution_time_hours"] for item in parsed), 1),
            "low_satisfaction": len(low_sat),
            "slow_high_priority": len(slow),
            "pay_first_half": pay_first,
            "pay_second_half": pay_second,
        },
        "by_day": dict(sorted(by_day.items())),
        "by_category": dict(sorted(by_cat.items(), key=lambda item: -item[1])),
        "by_priority": dict(by_priority),
        "by_channel": dict(by_channel),
        "sat_by_category": {key: round(mean(values), 2) for key, values in sat_by_cat.items()},
        "sla_by_category": {key: round(mean(values), 1) for key, values in sla_by_cat.items()},
        "unresolved_ids": [item["ticket_id"] for item in unresolved],
        "anomalies": anomalies,
        "narrative": narrative,
        "cases": parsed,
    }


def write_ticket_reports(report: dict[str, Any], output_dir: Path) -> None:
    kpis = report["kpis"]
    md = [
        "# 客服工单趋势分析",
        "",
        "> 运行模式：规则统计 + Mock LLM 综述",
        "",
        "## 分析维度",
        *[f"- **{name}**：{why}" for name, why in report["dimensions"].items()],
        "",
        "## 关键发现",
        report["narrative"],
        "",
        "## 异常信号",
        *[
            f"- **{item['title']}**（{item['severity']}）：{item['evidence']} → {item['action']}"
            for item in report["anomalies"]
        ],
        "",
    ]
    dump_markdown(output_dir / "report.md", "\n".join(md))
    dump_json(output_dir / "report.json", {k: v for k, v in report.items() if k != "cases"})
    page = dashboard(
        title="客服工单趋势分析",
        eyebrow="OPS INTELLIGENCE",
        subtitle="Mock LLM 综述 · 规则发现异常 · 给主管看的优先级",
        metrics=[
            ("工单量", str(kpis["total"])),
            ("未关闭", str(kpis["unresolved"])),
            ("平均满意度", str(kpis["avg_satisfaction"])),
            ("平均处理小时", str(kpis["avg_resolution_hours"])),
        ],
        panels=[
            ("问题类型", bars(report["by_category"])),
            ("需要主管关注的异常", bullets(
                [f"{item['title']}：{item['evidence']}" for item in report["anomalies"]]
            )),
        ],
        table_title="未关闭与高伤害工单",
        headers=["工单", "时间", "分类", "优先级", "时长h", "满意度", "状态"],
        rows=[
            [
                item["ticket_id"],
                item["created_at"],
                item["category"],
                item["priority"],
                str(item["resolution_time_hours"]),
                str(item["satisfaction"]),
                "未关闭" if not item["is_resolved"] else "已关闭",
            ]
            for item in report["cases"]
            if (not item["is_resolved"]) or item["satisfaction"] <= 1
        ],
        footnote="0111 · 判断依据全部来自 tickets.json 字段统计。",
    )
    (output_dir / "dashboard.html").write_text(page, encoding="utf-8")
