from __future__ import annotations
import re, datetime as dt
from typing import Iterable, Dict
import requests
from bs4 import BeautifulSoup

HEADERS = {
  "User-Agent": "AI-Weekly-Digest/1.0 (+github-actions; contact maintainer)"
}

def _norm_space(s: str) -> str:
  return re.sub(r"\s+", " ", s).strip()

def neuron_articles(url: str) -> Iterable[Dict]:
  """
  Scrape https://www.theneuron.ai/articles to extract explainer article links.
  Dates are not present in markup, so we set published=None and rely on first_seen.
  """
  resp = requests.get(url, headers=HEADERS, timeout=30)
  resp.raise_for_status()
  soup = BeautifulSoup(resp.text, "html.parser")

  items = []
  # Heuristic: pick prominent article links in the 'Explainers' section
  # We collect unique anchors pointing to theneuron.ai excluding anchors with no href.
  seen = set()
  for a in soup.find_all("a", href=True):
    href = a["href"]
    if not href.startswith("http"):
      continue
    if "theneuron.ai" not in href:
      continue
    if href in seen:
      continue
    text = _norm_space(a.get_text(" ") or "")
    # Filter likely article titles: long-ish text and not navigation
    if len(text) < 25:
      continue
    # Avoid "Read all..." or navigation
    if re.search(r"\b(Read all|Subscribe|Partner|Tools|Home)\b", text, re.I):
      continue
    seen.add(href)
    items.append({
      "title": text[:300],
      "url": href,
      "published": None,
    })
  return items

def datascientest_category(url: str) -> Iterable[Dict]:
  """
  Scrape the DataScientest category page (fallback if RSS is unavailable).
  """
  resp = requests.get(url, headers=HEADERS, timeout=30)
  resp.raise_for_status()
  soup = BeautifulSoup(resp.text, "html.parser")
  items = []
  seen = set()

  # Look for article blocks with headings and links
  for a in soup.find_all("a", href=True):
    href = a["href"]
    if not href.startswith("http") or "datascientest.com" not in href:
      continue
    if href in seen:
      continue
    text = _norm_space(a.get_text(" ") or "")
    # Heuristic: skip very short or obvious nav labels
    if len(text) < 20:
      continue
    if re.search(r"(Lire la suite|Read more|Catégorie|Accueil|Menu|Newsletter|Facebook|LinkedIn|YouTube|Instagram)", text, re.I):
      continue
    seen.add(href)
    items.append({
      "title": text[:300],
      "url": href,
      "published": None,
    })
  return items

STRATEGIES = {
  "neuron_articles": neuron_articles,
  "datascientest_category": datascientest_category,
}
