"""Present existing responses without another model call or invented citations."""

import re
from ipaddress import ip_address
from urllib.parse import urlsplit

from services.ai_data_scope import PROFILE_FIELDS


async def retrieve_for_chat(service, query):
    if service is None or not query:
        return {"context": "", "sources": []}
    return await service.search_with_sources(query)


def chat_presentation(query, text, context, sources, previous_exchange=None):
    paragraphs = [part.strip() for part in text.split("\n") if part.strip()]
    excerpt = paragraphs[0] if paragraphs else ""
    if len(excerpt) > 320:
        excerpt = excerpt[:320] + "…"
    questions = [part.strip()[:250] for part in re.findall(r"[^。！？.!?\n]*[?？]", text) if part.strip()][:3]
    actual_sources = []
    seen = set()
    for source in sources or []:
        if not isinstance(source, dict):
            continue
        url = source.get("url", "")
        try:
            if not isinstance(url, str) or len(url) > 2000:
                continue
            parts = urlsplit(url)
            _ = parts.port
            if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or url in seen:
                continue
            host = parts.hostname.lower().rstrip(".")
            if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
                continue
            try:
                if not ip_address(host).is_global:
                    continue
            except ValueError:
                if "." not in host:
                    continue
        except (TypeError, ValueError):
            continue
        seen.add(url)
        actual_sources.append({"title": str(source.get("title") or parts.hostname)[:150], "url": url,
                               "kind": "retrieved_document"})
    return {"summary_excerpt": excerpt, "provided_question": query,
        "provided_profile": {key: value for key, value in (context or {}).items() if key in PROFILE_FIELDS},
        "provided_previous_exchange": previous_exchange,
        "clarifying_questions": questions, "sources": actual_sources[:5]}
