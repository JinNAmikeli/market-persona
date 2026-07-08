from __future__ import annotations

import json
from pathlib import Path
from typing import Any


WIKI_DIR = Path(__file__).resolve().parents[1] / "wiki"
INDEX_PATH = WIKI_DIR / "index.json"


def _load_pages() -> list[dict[str, Any]]:
    if not INDEX_PATH.exists():
        return []
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    pages = []
    for rel_path in index.get("pages") or []:
        path = WIKI_DIR / rel_path
        if not path.exists():
            continue
        try:
            pages.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return pages


def _tokens(query: str) -> list[str]:
    raw = query.replace("/", " ").replace("，", " ").replace("、", " ").split()
    tokens = [item.strip().lower() for item in raw if item.strip()]
    if not tokens and query.strip():
        tokens = [query.strip().lower()]
    return tokens


def _score(page: dict[str, Any], section: dict[str, Any], tokens: list[str], query_text: str) -> int:
    haystacks = [
        (page.get("title") or "", 4),
        (" ".join(page.get("tags") or []), 3),
        (section.get("title") or "", 3),
        (section.get("content") or "", 1),
    ]
    score = 0
    for token in tokens:
        for text, weight in haystacks:
            if token in text.lower():
                score += weight
    query_lower = query_text.lower()
    title = (page.get("title") or "").lower()
    if title and (title in query_lower or title.split("/")[0] in query_lower):
        score += 8
    for tag in page.get("tags") or []:
        tag_lower = tag.lower()
        if tag_lower and tag_lower in query_lower:
            score += 5
    return score


def search_wiki(queries: list[str], top_k: int = 5) -> list[dict[str, Any]]:
    query_text = " ".join(queries)
    tokens = []
    for query in queries:
        tokens.extend(_tokens(query))
    tokens = list(dict.fromkeys(tokens))
    if not tokens:
        return []

    hits = []
    for page in _load_pages():
        for section in page.get("sections") or []:
            score = _score(page, section, tokens, query_text)
            if score <= 0:
                continue
            hits.append(
                {
                    "topic_id": page.get("topic_id"),
                    "title": page.get("title"),
                    "version": page.get("version"),
                    "status": page.get("status"),
                    "reviewed_at": page.get("reviewed_at"),
                    "evidence_quality": page.get("evidence_quality"),
                    "sources": page.get("sources") or [],
                    "applicable_tasks": page.get("applicable_tasks") or [],
                    "forbidden_use": page.get("forbidden_use") or [],
                    "section_id": section.get("section_id"),
                    "section_title": section.get("title"),
                    "content": section.get("content"),
                    "score": score,
                    "evidence": section.get("evidence") or [],
                    "section_updated_at": section.get("updated_at"),
                }
            )
    return sorted(hits, key=lambda item: item["score"], reverse=True)[:top_k]
