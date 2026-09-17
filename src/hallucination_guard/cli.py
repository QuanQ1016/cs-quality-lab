from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import HallucinationDetector
from .evaluation import evaluate, load_cases, load_ground_truth, write_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hallucination-guard",
        description="使用 Mock LLM 批量检测客服回复幻觉并生成验证报告。",
    )
    parser.add_argument("--input", type=Path, default=Path("data/replies.json"))
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=Path("data/ground_truth.json"),
    )
    parser.add_argument("--output", type=Path, default=Path("reports"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cases = load_cases(args.input)
        truth = load_ground_truth(args.ground_truth)
        detector = HallucinationDetector()
        detections = detector.detect_many(cases)
        report = evaluate(cases, detections, truth)
        write_reports(report, args.output)
    except (OSError, ValueError) as error:
        print(f"运行失败：{error}", file=sys.stderr)
        return 1

    metrics = report["metrics"]
    print("Hallucination Guard / Mock LLM")
    print(f"样本: {metrics['total']}  TP: {metrics['tp']}  FP: {metrics['fp']}  "
          f"TN: {metrics['tn']}  FN: {metrics['fn']}")
    print(
        f"Accuracy: {metrics['accuracy']:.2%}  "
        f"Precision: {metrics['precision']:.2%}  "
        f"Recall: {metrics['recall']:.2%}  F1: {metrics['f1']:.2%}"
    )
    print(f"报告已写入: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
