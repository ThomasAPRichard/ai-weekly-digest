from __future__ import annotations
import hashlib, datetime as dt, time
from typing import Dict, Iterable, List
import feedparser, requests
from dateutil import parser as dtparser

from .scrapers import STRATEGIES

UA = "AI-Weekly-Digest/1.0 (+github-actions; contact maintainer)"

def _hash_guid(source: str, guid: str) -> str:
  return hashlib.sha1(f"{source}::{guid}".encode("utf-8")).hexdigest()

def _to_dt(value):
  if not value:
    return None
  if isinstance(value, dt.datetime):
    return value
  # feedparser returns 'published_parsed' or 'updated_parsed' as time.struct_time
  if isinstance(value, time.struct_time):
    return dt.datetime(*value[:6])
  try:
    return dtparser.parse(str(value))
  except Exception:
    return None

def from_rss(source_name: str, url: str) -> List[Dict]:
  feed = feedparser.parse(url, request_headers={"User-Agent": UA})
  items = []
  for e in feed.entries:
    title = (e.get("title") or "").strip() or "(no title)"
    link = e.get("link")
    guid = e.get("id") or link or title
    published = _to_dt(e.get("published_parsed") or e.get("updated_parsed") or e.get("published") or e.get("updated"))
    items.append({
      "source": source_name,
      "guid": guid,
      "url": link,
      "title": title,
      "published": published,
    })
  return items

def from_html(source_name: str, url: str, strategy: str) -> List[Dict]:
  fn = STRATEGIES.get(strategy)
  if not fn:
    raise ValueError(f"Unknown scraping strategy: {strategy}")
  out = []
  for e in fn(url):
    guid = e["url"]
    out.append({
      "source": source_name,
      "guid": guid,
      "url": e["url"],
      "title": e["title"],
      "published": e.get("published"),
    })
  return out
