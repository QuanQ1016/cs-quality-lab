from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


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
    cards = "".join(
        f'<article class="metric"><span>{html.escape(label)}</span>'
        f"<strong>{html.escape(value)}</strong></article>"
        for label, value in metrics
    )
    panel_html = "".join(
        f'<article class="panel"><h2>{html.escape(name)}</h2>{body}</article>'
        for name, body in panels
    )
    head = "".join(f"<th>{html.escape(item)}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    grid_class = "grid two" if len(panels) == 2 else "grid"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root{{--ink:#172033;--muted:#667085;--paper:#f4f6f9;--card:#fff;--navy:#14213d;
--blue:#356ae6;--cyan:#2bb5a8;--red:#d64550}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);
font:14px/1.5 Inter,"Segoe UI","Microsoft YaHei",sans-serif}}
.top{{background:var(--navy);color:#fff;padding:42px max(6vw,24px) 78px}}
.eyebrow{{color:#89a9f5;letter-spacing:.14em;font-size:12px;font-weight:700}}
h1{{font-size:34px;margin:8px 0}} .top p{{color:#bdc7dc;margin:0}}
main{{max-width:1180px;margin:-48px auto 56px;padding:0 24px}}
.metrics{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}}
.metric,.panel{{background:var(--card);border:1px solid #e7eaf0;border-radius:14px;
box-shadow:0 8px 24px #14213d0d}} .metric{{padding:22px}}
.metric span{{display:block;color:var(--muted)}} .metric strong{{font-size:28px}}
.grid{{display:grid;gap:18px;margin-top:18px}} .two{{grid-template-columns:1fr 1fr}}
.panel{{padding:24px}} h2{{font-size:18px;margin:0 0 16px}}
.bar-row{{display:grid;grid-template-columns:140px 1fr 36px;gap:10px;align-items:center;margin:10px 0}}
.track{{height:9px;background:#edf0f5;border-radius:9px;overflow:hidden}}
.track i{{display:block;height:100%;background:linear-gradient(90deg,var(--blue),var(--cyan));border-radius:9px}}
.wide{{margin-top:18px}} table{{width:100%;border-collapse:collapse}}
th,td{{padding:11px 10px;text-align:left;border-bottom:1px solid #edf0f5;vertical-align:top}}
th{{color:var(--muted);font-size:12px}} .pill{{display:inline-block;padding:3px 8px;
border-radius:99px;background:#edf2ff;color:#2857bf}}
.bad{{color:var(--red);font-weight:700}} .ok{{color:#08765d;font-weight:700}}
.nav{{margin:12px 0 0}} .nav a{{color:#c9d7ff;margin-right:16px}}
.foot{{color:var(--muted);font-size:12px;margin-top:18px}}
@media(max-width:760px){{.metrics,.two{{grid-template-columns:1fr 1fr}}}}
</style>
</head>
<body>
<header class="top"><div class="eyebrow">{html.escape(eyebrow)}</div>
<h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p>
<div class="nav"><a href="../index.html">总览</a></div></header>
<main>
<section class="metrics">{cards}</section>
<section class="{grid_class}">{panel_html}</section>
<section class="panel wide"><h2>{html.escape(table_title)}</h2>
<div style="overflow:auto"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>
</section>
<p class="foot">{html.escape(footnote)}</p>
</main></body></html>"""


def bars(items: dict[str, float | int]) -> str:
    if not items:
        return "<p>无数据</p>"
    maximum = max(float(value) for value in items.values()) or 1
    return "".join(
        '<div class="bar-row">'
        f"<span>{html.escape(str(name))}</span>"
        f'<div class="track"><i style="width:{float(value) / maximum * 100:.1f}%"></i></div>'
        f"<b>{html.escape(str(value))}</b></div>"
        for name, value in items.items()
    )


def bullets(lines: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{html.escape(line)}</li>" for line in lines) + "</ul>"
