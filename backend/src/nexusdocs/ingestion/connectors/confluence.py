"""Confluence connector — fetches a page (or all pages in a space) and runs
each through the markdown ingestion pipeline.

Authentication: pass a Personal Access Token via ``token`` (Cloud) or
``username`` + ``token`` (Server). When unset, only public pages can be
fetched.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

import httpx

from ...llm.client import LLMClient
from ..conflict import ConflictResolver
from .markdown import MarkdownConnector, MarkdownIngestionResult


class _StripHTML(HTMLParser):
    """Very small HTML → plaintext converter — keeps headings and lists."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip += 1
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            self.parts.append("\n\n" + "#" * level + " ")
        elif tag in {"li"}:
            self.parts.append("\n- ")
        elif tag in {"p", "br", "tr", "div"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip:
            self._skip -= 1
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        self.parts.append(data)

    def text(self) -> str:
        joined = "".join(self.parts)
        joined = re.sub(r"\n{3,}", "\n\n", joined)
        return joined.strip()


def html_to_text(html: str) -> str:
    parser = _StripHTML()
    try:
        parser.feed(html)
    except Exception:
        return html
    return parser.text() or html


class ConfluenceConnector:
    """Confluence Cloud / Server adapter."""

    def __init__(
        self,
        llm: LLMClient,
        resolver: ConflictResolver,
        *,
        timeout: float = 20.0,
    ) -> None:
        self.llm = llm
        self.resolver = resolver
        self.timeout = timeout
        self._md = MarkdownConnector(llm, resolver, source_type="confluence")

    # ---- Public --------------------------------------------------------

    def ingest_page(
        self,
        *,
        base_url: str,
        page_id: str,
        token: str | None = None,
        username: str | None = None,
        lenses: list[str] | None = None,
    ) -> MarkdownIngestionResult:
        report = MarkdownIngestionResult()
        try:
            page = self._fetch_page(base_url, page_id, token=token, username=username)
        except Exception as exc:
            report.errors.append(f"confluence fetch failed: {exc}")
            return report

        title = page.get("title") or f"Confluence page {page_id}"
        html = (
            page.get("body", {})
            .get("storage", {})
            .get("value")
            or page.get("body", {}).get("view", {}).get("value")
            or ""
        )
        text = html_to_text(html)
        if not text:
            report.errors.append("confluence page has no extractable body")
            return report

        source_path = page.get("_links", {}).get(
            "webui", f"{base_url}/pages/{page_id}"
        )
        if not source_path.startswith("http"):
            source_path = base_url.rstrip("/") + source_path

        return self._md.ingest(
            text=text,
            title=title,
            source_path=source_path,
            lenses=lenses,
            tags=["confluence"],
        )

    # ---- Internals ----------------------------------------------------

    def _fetch_page(
        self,
        base_url: str,
        page_id: str,
        *,
        token: str | None,
        username: str | None,
    ) -> dict[str, Any]:
        url = f"{base_url.rstrip('/')}/rest/api/content/{page_id}?expand=body.storage,body.view"
        auth = None
        headers: dict[str, str] = {"Accept": "application/json"}
        if token and username:
            auth = (username, token)
        elif token:
            headers["Authorization"] = f"Bearer {token}"
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(url, headers=headers, auth=auth)
            r.raise_for_status()
            return r.json()
