from __future__ import annotations
import datetime as dt
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import List, Dict, Any
import pathlib

def render_html(subject: str, groups: List[Dict[str, Any]], since: dt.datetime, now: dt.datetime, templates_dir: pathlib.Path) -> str:
  env = Environment(
    loader=FileSystemLoader(str(templates_dir)),
    autoescape=select_autoescape(['html', 'xml'])
  )
  tpl = env.get_template("digest.html.j2")
  total = sum(len(g["items"]) for g in groups)
  return tpl.render(
    subject=subject,
    title=subject,
    groups=groups,
    since_date=since.strftime("%Y-%m-%d"),
    now_date=now.strftime("%Y-%m-%d"),
    total_count=total,
  )

def render_text(subject: str, groups: List[Dict[str, Any]], since: dt.datetime, now: dt.datetime) -> str:
  lines = [subject, f"Période : {since:%Y-%m-%d} → {now:%Y-%m-%d}"]
  for g in groups:
    lines.append("")
    lines.append(f"## {g['name']} ({len(g['items'])})")
    for it in g["items"]:
      when = it["published"] or it["first_seen"]
      when_s = when.strftime("%Y-%m-%d") if when else ""
      lines.append(f"- {it['title']} — {when_s}\n  {it['url']}")
  return "\n".join(lines)
