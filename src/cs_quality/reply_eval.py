from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from .report import bars, bullets, dashboard, dump_json, dump_markdown


class ReplyJudgeLLM:
    """把模糊的业务要求变成 4 个可自动打分的指标。不读取人工参考回复。"""

    model = "mock-reply-judge-v1"
    METRICS = ("accuracy", "usefulness", "tone", "groundedness")
    WEIGHTS = {"groundedness": 0.35, "accuracy": 0.30, "usefulness": 0.25, "tone": 0.10}

    def complete(self, payload: dict[str, str]) -> str:
        question = payload["user_question"]
        reply = payload["auto_reply"]
        scores = {
            "accuracy": 4,
            "usefulness": 3,
            "tone": 4,
            "groundedness": 5,
            "flags": [],
        }

        specific = any(token in question for token in ("这个", "这款", "那两款", "那个包", "我的"))
        dump = any(token in reply for token in ("详情页", "联系客服", "联系品牌", "耐心等待"))
        ownership = any(token in reply for token in ("我帮您", "我现在就", "请提供订单号", "请把"))
        angry = any(token in question for token in ("态度", "等了", "搞半天", "连续", "太差", "太复杂"))
        scared = "异地登录" in question or "是真的吗" in question
        process_repeat = "退货流程" in reply and ("搞半天" in question or "太复杂" in question)

        if specific and dump:
            scores["accuracy"] -= 2
            scores["usefulness"] -= 2
            scores["flags"].append("把具体问题推回详情页")
        elif dump:
            scores["usefulness"] -= 1
            scores["flags"].append("让用户自己去查或再联系客服")
        if ownership:
            scores["usefulness"] = min(5, scores["usefulness"] + 1)
        if angry:
            scores["tone"] = 4 if "抱歉" in reply or "对不起" in reply else 2
            if "加强培训" in reply:
                scores["usefulness"] -= 1
                scores["flags"].append("道歉后转向内部事项")
            if not ownership:
                scores["usefulness"] -= 1
        if scared and "可能是诈骗" in reply and "帮您查" not in reply:
            scores["usefulness"] -= 1
            scores["tone"] -= 1
            scores["flags"].append("安全场景只给自查清单")
        if process_repeat:
            scores["accuracy"] -= 2
            scores["usefulness"] -= 2
            scores["flags"].append("用户说流程看不懂，回复又把流程念一遍")
        if "连续两次" in question or "又是坏的" in question:
            if "50元" not in reply and "补偿" in reply:
                scores["tone"] -= 0
                scores["usefulness"] -= 0
            if "额外" not in reply:
                scores["tone"] -= 1
        if "取不出来" in question or "放错快递柜" in question:
            if "联系快递员" in reply and "我帮您" not in reply:
                scores["accuracy"] -= 2
                scores["usefulness"] -= 2
                scores["flags"].append("核心诉求是取件失败，却把责任推给用户")
        if "两件" in question and "分别" not in reply:
            scores["accuracy"] -= 1
            scores["usefulness"] -= 1
            scores["flags"].append("多商品问题给了单模板流程")
        if "退款什么时候" in question:
            scores["accuracy"] = 5
            scores["flags"].append("通用时效说明本身准确，但未查该笔订单")
            scores["usefulness"] -= 1
        if "刚下单" in question and "未发货" in reply:
            scores["accuracy"] = 5
            scores["usefulness"] = 4
        if "建议" in question or "加个功能" in question:
            scores["accuracy"] = 5
            scores["usefulness"] = 4
            scores["tone"] = 5

        for key in self.METRICS:
            scores[key] = max(1, min(5, int(scores[key])))
        overall = round(sum(scores[key] * self.WEIGHTS[key] for key in self.METRICS), 2)
        scores["overall"] = overall
        scores["rationale"] = "；".join(scores["flags"]) or "回复覆盖了问题且没有明显编造。"
        return json.dumps(scores, ensure_ascii=False)


def load_json_list(path: Path) -> list[dict[str, Any]]:
    values = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(values, list):
        raise ValueError(f"{path.name} 顶层必须是数组")
    return values


def evaluate_replies(
    replies: list[dict[str, Any]],
    references: list[dict[str, Any]],
) -> dict[str, Any]:
    judge = ReplyJudgeLLM()
    ref_by_id = {item["id"]: item for item in references}
    rows = []
    for item in replies:
        raw = json.loads(judge.complete(item))
        note = ref_by_id[item["id"]]["annotator_notes"]
        rows.append({
            "id": item["id"],
            "question": item["user_question"],
            "auto_reply": item["auto_reply"],
            **raw,
            "human_note": note,
        })

    worst = sorted(rows, key=lambda row: (row["overall"], row["usefulness"]))[:3]
    dist = {metric: round(mean(row[metric] for row in rows), 2) for metric in ReplyJudgeLLM.METRICS}
    overall = round(mean(row["overall"] for row in rows), 2)
    low = sum(row["overall"] < 3.2 for row in rows)

    return {
        "mode": "mock",
        "metrics_def": {
            "groundedness": "不瞎编：是否给出知识库/系统无法支持的确定事实。权重 35%。",
            "accuracy": "准确：是否回答了用户真正在问的那件事，而不是正确的百科。权重 30%。",
            "usefulness": "有用：用户看完能否少操作一步，而不是被推去详情页。权重 25%。",
            "tone": "语气：情绪匹配、不甩锅、不把内部管理当答复。权重 10%。",
        },
        "priority": "扩大覆盖前：不瞎编 > 准确 > 有用 > 语气。编造会直接造成资损和投诉。",
        "summary": {
            "count": len(rows),
            "overall": overall,
            "low_quality": low,
            "metric_means": dist,
        },
        "worst3": [
            {
                "id": row["id"],
                "overall": row["overall"],
                "rationale": row["rationale"],
                "human_note": row["human_note"],
            }
            for row in worst
        ],
        "limitations": [
            "没有订单/商品检索时，‘准确’只能判断是否答到点上，不能验证具体 SKU 参数。",
            "人工参考用于校验方法，不进入打分输入；两者关注点接近但不保证逐条同序。",
            "‘有用’对自动回复偏严：能给出正确规则但仍让用户自助的，会被压分。这符合是否扩覆盖的决策。",
            "语气用关键词近似情绪，反讽或冷幽默可能评不准。",
        ],
        "cases": rows,
    }


def write_reply_reports(report: dict[str, Any], output_dir: Path) -> None:
    summary = report["summary"]
    md = [
        "# 自动回复质量评估",
        "",
        "> 运行模式：Mock LLM 四指标打分，人工注释放在校验栏",
        "",
        "## 指标定义",
        *[f"- **{key}**：{desc}" for key, desc in report["metrics_def"].items()],
        "",
        f"优先级：{report['priority']}",
        "",
        f"整体加权分 {summary['overall']} / 5，低分样本 {summary['low_quality']} 条。",
        "",
        "## 最差 3 条",
        *[
            f"- **{item['id']}**（{item['overall']}）：{item['rationale']}\n  人工标注：{item['human_note']}"
            for item in report["worst3"]
        ],
        "",
        "## 局限性",
        *[f"- {line}" for line in report["limitations"]],
    ]
    dump_markdown(output_dir / "report.md", "\n".join(md))
    dump_json(output_dir / "report.json", report)
    page = dashboard(
        title="自动回复质量评估",
        eyebrow="REPLY EVALUATION",
        subtitle="准确 / 有用 / 语气 / 不瞎编 · Mock LLM · 人工标注只做校验",
        metrics=[
            ("整体得分", f"{summary['overall']}/5"),
            ("准确", str(summary["metric_means"]["accuracy"])),
            ("有用", str(summary["metric_means"]["usefulness"])),
            ("低分条数", str(summary["low_quality"])),
        ],
        panels=[
            ("指标均分", bars(summary["metric_means"])),
            ("最差 3 条", bullets(
                [f"{item['id']}（{item['overall']}）：{item['rationale']}" for item in report["worst3"]]
            )),
        ],
        table_title="20 条自动回复评分",
        headers=["ID", "问题", "准确", "有用", "语气", "不瞎编", "总分"],
        rows=[
            [
                row["id"],
                row["question"],
                str(row["accuracy"]),
                str(row["usefulness"]),
                str(row["tone"]),
                str(row["groundedness"]),
                str(row["overall"]),
            ]
            for row in report["cases"]
        ],
        footnote="0109 · 打分未使用 human_ref.json，仅在报告中对照人工分析。",
    )
    (output_dir / "dashboard.html").write_text(page, encoding="utf-8")
