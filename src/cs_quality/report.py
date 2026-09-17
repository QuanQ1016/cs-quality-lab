from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .theme import page_foot, page_head


def _metric_card(label: str, value: str, index: int) -> str:
    text = value.strip()
    suffix = ""
    prefix = ""
    core = text
    extra = ""
    if core.endswith("%"):
        suffix = "%"
        core = core[:-1].strip()
    if "/" in core and core.replace("/", "").replace(".", "").isdigit():
        left, right = core.split("/", 1)
        core = left.strip()
        suffix = f"/{right.strip()}{suffix}"
    try:
        number = float(core.replace(",", ""))
        decimals = len(core.split(".")[1]) if "." in core else 0
        extra = (
            f' data-count="{number}" data-prefix="{html.escape(prefix)}" '
            f'data-suffix="{html.escape(suffix)}" data-decimals="{decimals}"'
        )
    except ValueError:
        extra = ""
    return (
        f'<article class="metric reveal" style="--d:{index}">'
        f"<span>{html.escape(label)}</span>"
        f"<strong{extra}>{html.escape(value)}</strong></article>"
    )


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def dump_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def dashboard(
    *,
    title: str,
    eyebrow: str,
    subtitle: str,
    metrics: list[tuple[str, str]],
    panels: list[tuple[str, str]],
    table_title: str,
    headers: list[str],
    rows: list[list[str]],
    footnote: str,
) -> str:
    cards = "".join(_metric_card(label, value, index) for index, (label, value) in enumerate(metrics))
    panel_html = "".join(
        f'<article class="panel reveal" style="--d:{index + 4}">'
        f"<h2>{html.escape(name)}</h2>{body}</article>"
        for index, (name, body) in enumerate(panels)
    )
    head = "".join(f"<th>{html.escape(item)}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    grid_class = "grid two" if len(panels) == 2 else "grid"
    return (
        page_head(title)
        + f"""<header class="top reveal">
<div class="eyebrow">{html.escape(eyebrow)}</div>
<h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p>
<div class="nav"><a href="../index.html">总览</a></div></header>
<main>
<section class="metrics">{cards}</section>
<section class="{grid_class}">{panel_html}</section>
<section class="panel wide reveal" style="--d:6"><h2>{html.escape(table_title)}</h2>
<div style="overflow:auto"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>
</section>
<p class="foot">{html.escape(footnote)}</p>
</main>"""
        + page_foot()
    )


def bars(items: dict[str, float | int]) -> str:
    if not items:
        return "<p>无数据</p>"
    maximum = max(float(value) for value in items.values()) or 1
    return "".join(
        f'<div class="bar-row" style="--i:{index}">'
        f"<span>{html.escape(str(name))}</span>"
        f'<div class="track"><i style="--fill:{float(value) / maximum:.4f}"></i></div>'
        f"<b>{html.escape(str(value))}</b></div>"
        for index, (name, value) in enumerate(items.items())
    )


def bullets(lines: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{html.escape(line)}</li>" for line in lines) + "</ul>"
