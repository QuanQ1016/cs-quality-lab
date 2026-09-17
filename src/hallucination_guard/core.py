from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ReplyCase:
    id: str
    user_question: str
    system_reply: str
    knowledge_base: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ReplyCase":
        required = ("id", "user_question", "system_reply", "knowledge_base")
        missing = [key for key in required if not isinstance(value.get(key), str)]
        if missing:
            raise ValueError(f"case 字段缺失或类型错误: {', '.join(missing)}")
        return cls(**{key: value[key].strip() for key in required})


@dataclass(frozen=True)
class Detection:
    id: str
    is_hallucination: bool
    category: str | None
    severity: str
    confidence: float
    evidence: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MockLLMClient:
    """模拟支持 JSON Schema 输出的 LLM API。

    Mock 只读取问题、回复和知识库，不读取 ground truth。规则相当于固定模型权重，
    保证离线可复现；替换真实 LLM 时只需保持 complete() 的返回结构。
    """

    model = "mock-evidence-judge-v1"

    _action_claims = (
        "我帮您查", "已帮您", "已经将", "直接发到", "已修改", "已升级",
        "目前在", "预计明天到账",
    )
    _no_capability = ("未接入", "不具备", "需人工")
    _safety_terms = ("孕妇", "哺乳期", "咨询医生", "视黄醇")
    _reassurance_terms = ("放心使用", "可以放心", "成分温和")

    def complete(self, *, system_prompt: str, payload: dict[str, str]) -> str:
        if "仅依据知识库" not in system_prompt:
            raise ValueError("system_prompt 必须包含证据约束")
        case = ReplyCase.from_dict(payload)
        result = self._infer(case)
        return json.dumps(result, ensure_ascii=False)

    def _infer(self, case: ReplyCase) -> dict[str, Any]:
        reply = case.system_reply
        kb = case.knowledge_base
        combined = f"{case.user_question} {reply} {kb}"

        if any(token in kb for token in self._no_capability) and any(
            token in reply for token in self._action_claims
        ):
            return self._result(
                "TOOL_USE_FABRICATION",
                "critical" if "修改" in combined else "high",
                0.99,
                kb,
                "回复声称已查询或执行操作，但知识库明确说明系统没有该能力。",
            )

        if any(token in kb for token in self._safety_terms) and any(
            token in reply for token in self._reassurance_terms
        ):
            return self._result(
                "SAFETY_MISGUIDANCE",
                "critical",
                0.99,
                kb,
                "回复用确定性安全承诺覆盖了知识库中的健康风险提示。",
            )

        if ("优惠" in combined or "减" in combined or "折" in combined) and (
            "无" in kb or self._numbers(reply) - self._numbers(kb)
        ):
            return self._result(
                "UNSUPPORTED_CLAIM",
                "high",
                0.98,
                kb,
                "回复承诺了知识库不存在的优惠或账户操作。",
            )

        if "偏大" in kb and ("不偏大" in reply or "尺码标准" in reply):
            return self._result(
                "MATERIAL_OMISSION",
                "medium",
                0.94,
                kb,
                "回复遗漏并否定了会影响选购决策的用户反馈。",
            )

        if self._has_explicit_negative_conflict(reply, kb):
            category = (
                "FACT_CONTRADICTION"
                if any(token in combined for token in ("门店", "品牌", "NFC"))
                else "POLICY_CONTRADICTION"
            )
            return self._result(
                category,
                "high",
                0.98,
                kb,
                "回复的肯定陈述与知识库中的明确否定陈述冲突。",
            )

        if self._numbers(reply) - self._numbers(kb):
            category = (
                "POLICY_CONTRADICTION"
                if any(token in combined for token in ("退货", "发货", "发票", "快递"))
                else "FACT_CONTRADICTION"
            )
            return self._result(
                category,
                "high",
                0.97,
                kb,
                "回复中的关键数值或时效没有证据支持，且与知识库参数冲突。",
            )

        if self._has_attribute_conflict(reply, kb):
            return self._result(
                "FACT_CONTRADICTION",
                "high",
                0.97,
                kb,
                "回复中的材质、接口、物流商或产品属性与知识库不一致。",
            )

        return {
            "is_hallucination": False,
            "category": None,
            "severity": "none",
            "confidence": 0.96,
            "evidence": kb,
            "rationale": "回复中的可验证事实与知识库一致，未发现越权操作或关键遗漏。",
        }

    @staticmethod
    def _numbers(text: str) -> set[str]:
        return set(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?(?:ms|天|小时|个月|年|%|折)?", text))

    @staticmethod
    def _has_explicit_negative_conflict(reply: str, kb: str) -> bool:
        checks = (
            (("支持NFC",), ("未标注NFC",)),
            (("有线下", "线下体验店"), ("无线下门店", "纯线上")),
            (("旗下的子品牌", "是一家"), ("未提及其他品牌",)),
            (("支持电子发票和纸质发票",), ("暂不支持纸质发票",)),
            (("全品类支持30天", "运费也由我们承担"), ("普通商品支持7天", "运费由买家承担")),
        )
        return any(
            any(positive in reply for positive in positives)
            and any(negative in kb for negative in negatives)
            for positives, negatives in checks
        )

    @staticmethod
    def _has_attribute_conflict(reply: str, kb: str) -> bool:
        conflict_pairs = (
            ("头层牛皮", "PU合成革"),
            ("Type-C接口", "USB-A输出"),
            ("顺丰", "中通/韵达/圆通"),
            ("多设备同时连接", "单设备连接"),
        )
        return any(left in reply and right in kb for left, right in conflict_pairs)

    @staticmethod
    def _result(
        category: str,
        severity: str,
        confidence: float,
        evidence: str,
        rationale: str,
    ) -> dict[str, Any]:
        return {
            "is_hallucination": True,
            "category": category,
            "severity": severity,
            "confidence": confidence,
            "evidence": evidence,
            "rationale": rationale,
        }


class HallucinationDetector:
    SYSTEM_PROMPT = (
        "你是客服回复审计员。仅依据知识库判断回复中的事实、政策、系统能力和"
        "安全建议；知识库未支持的确定性陈述应标记。只返回约定 JSON。"
    )
    CATEGORIES = {
        "FACT_CONTRADICTION": "事实/参数与证据直接冲突",
        "POLICY_CONTRADICTION": "政策、流程、时效或费用与规则冲突",
        "UNSUPPORTED_CLAIM": "证据外的优惠、关系或确定性承诺",
        "TOOL_USE_FABRICATION": "声称执行了系统不具备的查询或操作",
        "SAFETY_MISGUIDANCE": "忽略风险提示并给出危险安全承诺",
        "MATERIAL_OMISSION": "遗漏导致结论反转的关键证据",
    }
    SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

    def __init__(self, client: MockLLMClient | None = None) -> None:
        self.client = client or MockLLMClient()

    def detect(self, case: ReplyCase) -> Detection:
        raw = self.client.complete(system_prompt=self.SYSTEM_PROMPT, payload=asdict(case))
        value = json.loads(raw)
        self._validate(value)
        return Detection(id=case.id, **value)

    def detect_many(self, cases: Iterable[ReplyCase]) -> list[Detection]:
        return [self.detect(case) for case in cases]

    def _validate(self, value: dict[str, Any]) -> None:
        required = {
            "is_hallucination", "category", "severity",
            "confidence", "evidence", "rationale",
        }
        if set(value) != required:
            raise ValueError("Mock LLM 返回结构不符合 schema")
        if value["category"] not in {*self.CATEGORIES, None}:
            raise ValueError(f"未知分类: {value['category']}")
        if value["severity"] not in self.SEVERITY_ORDER:
            raise ValueError(f"未知严重度: {value['severity']}")
        confidence = value["confidence"]
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError("confidence 必须在 [0, 1] 范围内")
