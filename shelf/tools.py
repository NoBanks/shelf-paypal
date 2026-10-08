"""SHELF crew tools.

comps_search: free, keyless web search for comparable prices.
Primary backend: the ddgs library (DuckDuckGo) - keyless, free, no card,
verified working 2026-08-16 with real price snippets. Fallbacks: Mojeek HTML,
Jina reader proxy. Rejected along the way (documented so nobody re-treads):
Gemini built-in search grounding = not on the free API tier (429s); raw DDG
endpoints = bot-walled (202); Brave Search API = free tier KILLED Feb 2026,
card-on-file with uncapped overage billing. Free-first is a project law.
"""
from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request

_UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36"
}


def _fetch(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "ignore")


def _strip(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment)).strip()


def _mojeek(query: str) -> list[dict]:
    page = _fetch("https://www.mojeek.com/search?q=" + urllib.parse.quote(query))
    results = []
    # Result blocks: <h2><a href="URL">TITLE</a></h2> ... <p class="s">SNIPPET</p>
    for m in re.finditer(
        r"<h2[^>]*>\s*<a[^>]+href=\"(https?://[^\"]+)\"[^>]*>(.*?)</a>.*?"
        r"<p[^>]*class=\"s\"[^>]*>(.*?)</p>",
        page,
        re.S,
    ):
        url, title, snippet = m.groups()
        results.append(
            {"title": _strip(title), "url": url, "snippet": _strip(snippet)[:240]}
        )
        if len(results) >= 8:
            break
    return results


def _jina_ddg(query: str) -> list[dict]:
    page = _fetch(
        "https://r.jina.ai/https://duckduckgo.com/html/?q="
        + urllib.parse.quote(query),
        timeout=30,
    )
    results = []
    # Jina returns markdown: [TITLE](URL) lines followed by snippet text.
    for m in re.finditer(r"\[([^\]]{10,120})\]\((https?://[^)]+)\)\s*\n+([^\[\n][^\n]{0,240})", page):
        title, url, snippet = m.groups()
        if "duckduckgo.com" in url:
            continue
        results.append({"title": title.strip(), "url": url, "snippet": snippet.strip()})
        if len(results) >= 8:
            break
    return results


def _ddgs(query: str) -> list[dict]:
    from ddgs import DDGS

    out = []
    for r in DDGS().text(query, max_results=8):
        out.append(
            {
                "title": r.get("title", ""),
                "url": r.get("href", "") or r.get("url", ""),
                "snippet": (r.get("body", "") or "")[:240],
            }
        )
    return out


def comps_search(query: str) -> list[dict]:
    """Search the web for comparable prices for an item.

    Args:
        query: what to search, e.g. "24x24 gallery wrap canvas print price".

    Returns:
        Up to 8 results as {title, url, snippet}. Snippets often contain
        prices; cite the url of any comp you use. Returns [] if all backends
        fail (then abstain from pricing).
    """
    for backend in (_ddgs, _mojeek, _jina_ddg):
        try:
            results = backend(query)
            if results:
                return results
        except Exception:
            continue
    return []
