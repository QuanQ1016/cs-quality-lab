# 客服回复幻觉检测报告

> 运行模式：Mock LLM（离线、确定性、可复现）

## 核心指标

- 样本数：20
- Accuracy：100.00%
- Precision：100.00%
- Recall：100.00%
- F1：100.00%
- 混淆矩阵：TP=18 / FP=0 / TN=2 / FN=0

## 逐条结果

| ID | 预测 | 分类 | 严重度 | 置信度 | 验证 |
|---|---|---|---|---:|---|
| h01 | 幻觉 | POLICY_CONTRADICTION | high | 98% | TP |
| h02 | 幻觉 | FACT_CONTRADICTION | high | 97% | TP |
| h03 | 幻觉 | TOOL_USE_FABRICATION | high | 99% | TP |
| h04 | 幻觉 | POLICY_CONTRADICTION | high | 98% | TP |
| h05 | 幻觉 | UNSUPPORTED_CLAIM | high | 98% | TP |
| h06 | 幻觉 | FACT_CONTRADICTION | high | 97% | TP |
| h07 | 幻觉 | POLICY_CONTRADICTION | high | 97% | TP |
| h08 | 幻觉 | POLICY_CONTRADICTION | high | 97% | TP |
| h09 | 幻觉 | FACT_CONTRADICTION | high | 98% | TP |
| h10 | 幻觉 | TOOL_USE_FABRICATION | high | 99% | TP |
| h11 | 幻觉 | FACT_CONTRADICTION | high | 98% | TP |
| h12 | 通过 | - | none | 96% | TN |
| h13 | 幻觉 | SAFETY_MISGUIDANCE | critical | 99% | TP |
| h14 | 幻觉 | TOOL_USE_FABRICATION | critical | 99% | TP |
| h15 | 幻觉 | FACT_CONTRADICTION | high | 98% | TP |
| h16 | 通过 | - | none | 96% | TN |
| h17 | 幻觉 | FACT_CONTRADICTION | high | 97% | TP |
| h18 | 幻觉 | TOOL_USE_FABRICATION | high | 99% | TP |
| h19 | 幻觉 | UNSUPPORTED_CLAIM | high | 98% | TP |
| h20 | 幻觉 | MATERIAL_OMISSION | medium | 94% | TP |

## 误判

- 误报：无
- 漏检：无
