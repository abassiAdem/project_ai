from __future__ import annotations

import re
from typing import List, Tuple

from backend.app.config import settings
from backend.app.vectorstore.chroma import get_collection


def _source_tokens_from_query(query: str) -> List[str]:
    q = query.lower()
    tokens = []
    if "constitution" in q or "دستور" in q or "الدستور" in q:
        tokens.append("constitution")
    if "journal" in q or "جريدة" in q or "الجريدة" in q:
        tokens.append("journal")
    return tokens


def _article_number_from_query(query: str) -> str | None:
    match = re.search(r"(article|الفصل|المادة)\s*(\d+)", query.lower())
    if not match:
        return None
    return match.group(2)


def _expand_queries(query: str) -> List[str]:
    q = query
    lower_q = q.lower()
    expansions = {q}

    pairs = [
        ("الدستور", "constitution"),
        ("دستور", "constitution"),
        ("الرائد", "journal"),
        ("الباب الأول", "chapitre premier"),
        ("الفصل 1", "article 1"),
    ]

    for arabic, french in pairs:
        if arabic in q:
            expansions.add(q.replace(arabic, french))
        if french in lower_q:
            expansions.add(q.replace(french, arabic))

    return list(expansions)


def search(query: str, top_k: int | None = None) -> List[Tuple[str, dict]]:
    collection = get_collection()
    k = top_k or settings.top_k
    expanded_k = max(k, k * 3)

    query_variants = _expand_queries(query)

    results = collection.query(
        query_texts=query_variants,
        n_results=expanded_k,
        include=["documents", "metadatas", "distances"],
    )

    docs_list = results.get("documents", [])
    metas_list = results.get("metadatas", [])
    distances_list = results.get("distances", [])

    tokens = _source_tokens_from_query(query)
    ranked = []
    seen = {}
    for docs, metas, distances in zip(docs_list, metas_list, distances_list):
        for doc, meta, dist in zip(docs, metas, distances):
            chunk_id = (meta or {}).get("chunk_id") or ""
            source = (meta or {}).get("source", "").lower()
            boost = 1 if any(t in source for t in tokens) else 0
            key = chunk_id or f"{source}:{(meta or {}).get('page', '')}:{dist}"
            prev = seen.get(key)
            if prev is None or dist < prev[1]:
                seen[key] = (boost, dist, doc, meta)

    article_num = _article_number_from_query(query)
    if article_num:
        article_pattern = re.compile(rf"article\s*{article_num}(?!\d)", re.IGNORECASE)
        keyword_tokens = [
            f"article {article_num}",
            f"Article {article_num}",
            f"ARTICLE {article_num}",
            f"الفصل {article_num}",
            f"المادة {article_num}",
        ]
        source_hint = ""
        if "constitution" in tokens:
            source_hint = "constitution"
        if "journal" in tokens:
            source_hint = "journal"

        keyword_hits = []
        for token in keyword_tokens:
            try:
                hits = collection.get(
                    where_document={"$contains": token},
                    include=["documents", "metadatas"],
                )
            except Exception:
                hits = collection.get(include=["documents", "metadatas"])

            docs = hits.get("documents", [])
            metas = hits.get("metadatas", [])
            for doc, meta in zip(docs, metas):
                if token.lower() not in (doc or "").lower():
                    continue
                if not article_pattern.search(doc or ""):
                    continue
                source = (meta or {}).get("source", "").lower()
                if source_hint and source_hint not in source:
                    continue
                key = (meta or {}).get("chunk_id") or f"{source}:{(meta or {}).get('page', '')}:{token}"
                if key in seen:
                    existing = seen[key]
                    if existing[0] < 2:
                        seen[key] = (2, existing[1], doc, meta)
                    continue
                keyword_hits.append((2, 0.0, doc, meta))

        for boost, dist, doc, meta in keyword_hits:
            key = (meta or {}).get("chunk_id") or f"{(meta or {}).get('source', '')}:{(meta or {}).get('page', '')}"
            seen[key] = (boost, dist, doc, meta)

    ranked = list(seen.values())
    ranked.sort(key=lambda item: (-item[0], item[1]))
    top = ranked[:k]

    return [(doc, meta) for _, _, doc, meta in top]
