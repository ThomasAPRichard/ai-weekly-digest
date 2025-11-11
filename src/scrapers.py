# scrapers.py

from __future__ import annotations

import re
import pathlib
import datetime as dt
from typing import Iterable, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from dateutil import parser as dtp


# Use a browser-like UA to avoid CDN blocks (Cloudflare, etc.)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    )
}


def _norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _to_abs(href: str, base: str) -> str:
    try:
        return urljoin(base, href)
    except Exception:
        return href


def _is_same_domain(url: str, domain: str) -> bool:
    try:
        return urlparse(url).netloc.endswith(domain)
    except Exception:
        return False


def _parse_time(node) -> Optional[datetime]:
    """
    Try common patterns:
      <time datetime="...">
      data-time / data-datetime
      aria-label date strings
      Any text that looks like a date.
    Return aware UTC datetime if found, else None.
    """
    # 1) <time datetime="...">
    t = node.find("time")
    if t:
        # Try standard "datetime" attribute
        if t.has_attr("datetime"):
            try:
                d = dtp.parse(t["datetime"])
                if not d.tzinfo:
                    d = d.replace(tzinfo=timezone.utc)
                return d.astimezone(timezone.utc)
            except Exception:
                pass
        # Sometimes date text is inside the tag
        try:
            txt = _norm_space(t.get_text(" ") or "")
            if txt:
                d = dtp.parse(txt, fuzzy=True)
                if not d.tzinfo:
                    d = d.replace(tzinfo=timezone.utc)
                return d.astimezone(timezone.utc)
        except Exception:
            pass

    # 2) Look for data-* attributes on card nodes
    for attr in ("data-time", "data-datetime", "aria-label", "title"):
        val = node.get(attr)
        if val:
            try:
                d = dtp.parse(val, fuzzy=True)
                if not d.tzinfo:
                    d = d.replace(tzinfo=timezone.utc)
                return d.astimezone(timezone.utc)
            except Exception:
                pass

    # 3) Last resort: scan short date-text children
    txt = _norm_space(node.get_text(" ") or "")
    if txt:
        # Heuristic to avoid parsing entire article text; only if it looks like a date
        if re.search(r"\b(20\d{2}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|"
                     r"janv|févr|mars|avr|mai|juin|juil|août|sept|oct|nov|déc)\b", txt, re.I):
            try:
                d = dtp.parse(txt, fuzzy=True)
                if not d.tzinfo:
                    d = d.replace(tzinfo=timezone.utc)
                return d.astimezone(timezone.utc)
            except Exception:
                pass

    return None


# -----------------------
# The Neuron — Explainers
# -----------------------
def neuron_articles(url: str) -> Iterable[Dict]:
    """
    Scrape https://www.theneuron.ai/articles to extract explainer article links.
    If no publish date is found, default to 'now' so items survive date filters.
    """
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items: List[Dict] = []
    seen: set[str] = set()

    # Prefer article/card containers when available
    # Fallback to scanning anchors.
    cards = soup.find_all(["article", "section", "div"], recursive=True)
    candidate_links: List[tuple[str, str, BeautifulSoup]] = []

    # Collect candidates from likely card containers
    for card in cards:
        a = card.find("a", href=True)
        if not a:
            continue
        href = _to_abs(a["href"], url)
        if not _is_same_domain(href, "theneuron.ai"):
            continue
        # Prefer article-like paths
        if not re.search(r"/articles?/|/explainer|/explainers?", href, re.I):
            continue

        title = _norm_space(a.get_text(" ") or "")
        if len(title) < 20:
            continue

        candidate_links.append((href, title, card))

    # If nothing found by cards, fallback to all anchors
    if not candidate_links:
        for a in soup.find_all("a", href=True):
            href = _to_abs(a["href"], url)
            if not _is_same_domain(href, "theneuron.ai"):
                continue
            if not re.search(r"/articles?/|/explainer|/explainers?", href, re.I):
                continue
            title = _norm_space(a.get_text(" ") or "")
            if len(title) < 20:
                continue
            candidate_links.append((href, title, soup))

    # Build items; ensure published is present
    for href, title, card in candidate_links:
        if href in seen:
            continue
        seen.add(href)

        published = _parse_time(card)
        if not published:
            published = datetime.now(timezone.utc)  # ensure it passes since-filter

        items.append({
            "title": title[:300],
            "url": href,
            "published": published,
        })

    return items


# -------------------------------------
# DataScientest — Category page (HTML)
# -------------------------------------
def datascientest_category(url: str) -> Iterable[Dict]:
    """
    Scrape a DataScientest WordPress category listing.
    Works for EN pages like:
      https://datascientest.com/en/category/news/
    If no publish date can be found, default to 'now'.
    """
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items: List[Dict] = []
    seen: set[str] = set()

    # WordPress commonly uses <article> wrappers with an <a> in the header and a <time> tag.
    articles = soup.find_all("article") or []

    def pick_title(node) -> str:
        for tag in ("h2", "h3", "h1"):
            h = node.find(tag)
            if h:
                txt = _norm_space(h.get_text(" ") or "")
                if txt:
                    return txt
        # Fallback: first anchor text
        a = node.find("a")
        if a:
            return _norm_space(a.get_text(" ") or "")
        return ""

    # Prefer structured <article> parsing
    for art in articles:
        a = art.find("a", href=True)
        if not a:
            continue
        href = _to_abs(a["href"], url)
        if not _is_same_domain(href, "datascientest.com"):
            continue
        if href in seen:
            continue

        title = pick_title(art)
        if len(title) < 10:
            # Try anchor text if header is empty
            title = _norm_space(a.get_text(" ") or "")
        if len(title) < 10:
            continue

        published = _parse_time(art)
        if not published:
            published = datetime.now(timezone.utc)

        seen.add(href)
        items.append({
            "title": title[:300],
            "url": href,
            "published": published,
        })

    # Fallback: if structured parsing failed (empty list), scan anchors
    if not items:
        for a in soup.find_all("a", href=True):
            href = _to_abs(a["href"], url)
            if not _is_same_domain(href, "datascientest.com"):
                continue
            if href in seen:
                continue
            txt = _norm_space(a.get_text(" ") or "")
            if len(txt) < 12:
                continue
            if re.search(r"(Lire la suite|Read more|Catégorie|Category|Accueil|Menu|Newsletter|"
                         r"Facebook|LinkedIn|YouTube|Instagram)", txt, re.I):
                continue

            # Try to find a nearby time tag (look at parent containers)
            parent = a.parent or soup
            published = _parse_time(parent) or datetime.now(timezone.utc)

            seen.add(href)
            items.append({
                "title": txt[:300],
                "url": href,
                "published": published,
            })

    return items


STRATEGIES = {
    "neuron_articles": neuron_articles,
    "datascientest_category": datascientest_category,
}