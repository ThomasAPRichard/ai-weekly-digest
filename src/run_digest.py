from __future__ import annotations
import argparse, datetime as dt, os, pathlib, sys, traceback
from typing import Dict, Any, List
import yaml

from .config import load_config, get_db_path, ROOT_DIR
from .storage import connect, upsert_items, select_since
from .collect import from_rss, from_html
from .digest import render_html, render_text
from .mailer import send_email

def top_k_per_source(rows: List[Dict[str, Any]], k: int = 3) -> List[Dict[str, Any]]:
    # Regroupe par source
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        grouped.setdefault(r["source"], []).append(r)

    # Clé de tri : date (published puis first_seen)
    def sort_key(it: Dict[str, Any]) -> dt.datetime:
        when = it.get("published") or it.get("first_seen")
        if isinstance(when, dt.datetime):
            try:
                # Comparaison robuste en UTC (évite les soucis naive/aware)
                return when.astimezone(dt.timezone.utc)
            except Exception:
                return when
        return dt.datetime.min.replace(tzinfo=dt.timezone.utc)

    # Trie chaque liste et coupe à 3
    groups: List[Dict[str, Any]] = []
    for name, items in grouped.items():
        items.sort(key=sort_key, reverse=True)
        groups.append({"name": name, "items": items[:k]})

    # Ordre des groupes (par nom ; tu peux changer si tu préfères)
    groups.sort(key=lambda g: g["name"].lower())
    return groups

def collect_from_sources(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
  all_rows = []
  for src in cfg["sources"]:
    name = src["name"]
    typ = src["type"]
    url = src["url"]
    strategy = src.get("strategy")
    if typ == "rss":
      rows = from_rss(name, url)
    elif typ == "html":
      if not strategy:
        raise ValueError(f"HTML source '{name}' requires a 'strategy'")
      rows = from_html(name, url, strategy)
    else:
      raise ValueError(f"Unknown source type: {typ}")
    # Normalize timestamps to ISO strings for SQLite
    now = dt.datetime.utcnow()
    for r in rows:
      r["first_seen"] = now
      if r["published"] is not None and not isinstance(r["published"], dt.datetime):
        # Let SQLite handle ISO strings
        try:
          r["published"] = r["published"].isoformat()
        except Exception:
          r["published"] = None
      if isinstance(r["first_seen"], dt.datetime):
        r["first_seen"] = r["first_seen"].isoformat()
    all_rows.extend(rows)
  return all_rows

def main(argv=None):
  ap = argparse.ArgumentParser(description="AI Weekly Digest")
  ap.add_argument("--config", default=str(ROOT_DIR / "config" / "sources.yaml"))
  ap.add_argument("--since-days", type=int, default=7)
  ap.add_argument("--db", default=str(get_db_path()))
  ap.add_argument("--send-email", action="store_true", help="Send the email (requires SMTP env vars)")
  args = ap.parse_args(argv)

  cfg = load_config(args.config)

  db_path = pathlib.Path(args.db)
  con = connect(db_path)

  # 1) Collect & store
  rows = collect_from_sources(cfg)
  inserted = upsert_items(con, rows)

  # 2) Query last N days
  now = dt.datetime.utcnow()
  since = now - dt.timedelta(days=args.since_days)
  selected = select_since(con, since)

  # Group by source (ne garder que les 3 derniers articles par site)
  groups_map: Dict[str, List[Dict[str, Any]]] = {}
  for r in selected:
    groups_map.setdefault(r["source"], []).append(r)

  def _when(it):
    # On privilégie 'published', sinon 'first_seen'
    return (it.get("published") or it.get("first_seen") or dt.datetime.min)

  groups: List[Dict[str, Any]] = []
  for name, items in groups_map.items():
    items_sorted = sorted(items, key=_when, reverse=True)
    groups.append({"name": name, "items": items_sorted[:3]})

  # Tri des groupes (facultatif) : alphabétique
  groups.sort(key=lambda g: g["name"].lower())

  # Subject & bodies
  subject_prefix = os.environ.get("SUBJECT_PREFIX", "AI Weekly Digest")
  """SUBJECT LAST WEEK VERSION
  subject = f"{subject_prefix} — {since.date()} → {now.date()}"
  """
  subject = f"{subject_prefix} — 3 dernies articles par site"
  html_body = render_html(subject, groups, since, now, ROOT_DIR / "templates")
  text_body = render_text(subject, groups, since, now)


  # 3) Optionally send email
  if args.send_email:
    send_email(subject, html_body, text_body)

  # Print a short summary to stdout for the CI logs
  total = sum(len(g["items"]) for g in groups)
  print(f"Inserted new: {inserted} — Digest items: {total}")
  for g in groups:
    print(f"  {g['name']}: {len(g['items'])}")

if __name__ == "__main__":
  main()
