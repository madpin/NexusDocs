"""Jira connector — fetches an issue (or a JQL query of issues) and ingests
its summary + description + comments through the markdown pipeline.
"""

from __future__ import annotations

from typing import Any

import httpx

from ...llm.client import LLMClient
from ..conflict import ConflictResolver
from .markdown import MarkdownConnector, MarkdownIngestionResult


def _fmt_issue(issue: dict[str, Any]) -> tuple[str, str, str]:
    fields = issue.get("fields", {})
    key = issue.get("key", "ISSUE")
    summary = fields.get("summary") or "<no summary>"
    description = fields.get("description") or ""
    if isinstance(description, dict):
        description = _flatten_adf(description)
    issue_type = (fields.get("issuetype") or {}).get("name") or "Issue"
    status = (fields.get("status") or {}).get("name") or "?"
    priority = (fields.get("priority") or {}).get("name") or "?"
    reporter = ((fields.get("reporter") or {}).get("displayName")) or "?"
    assignee = ((fields.get("assignee") or {}).get("displayName")) or "Unassigned"

    body_lines = [
        f"# {key} — {summary}",
        "",
        f"- type: {issue_type}",
        f"- status: {status}",
        f"- priority: {priority}",
        f"- reporter: {reporter}",
        f"- assignee: {assignee}",
        "",
        "## Description",
        "",
        description.strip() or "_(no description)_",
    ]

    comments = (fields.get("comment") or {}).get("comments") or []
    if comments:
        body_lines += ["", "## Comments", ""]
        for c in comments:
            author = (c.get("author") or {}).get("displayName") or "?"
            body = c.get("body")
            if isinstance(body, dict):
                body = _flatten_adf(body)
            body_lines.append(f"**{author}**: {body or ''}".rstrip())
            body_lines.append("")

    return key, summary, "\n".join(body_lines)


def _flatten_adf(node: dict[str, Any]) -> str:
    """Turn Atlassian Document Format into rough plaintext."""

    if not isinstance(node, dict):
        return ""
    out: list[str] = []
    if node.get("type") == "text":
        out.append(node.get("text", ""))
    for child in node.get("content") or []:
        out.append(_flatten_adf(child))
    if node.get("type") in {"paragraph", "heading", "bulletList", "orderedList"}:
        out.append("\n")
    if node.get("type") == "listItem":
        out.append("\n- ")
    return "".join(out)


class JiraConnector:
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
        self._md = MarkdownConnector(llm, resolver, source_type="jira")

    def ingest_issue(
        self,
        *,
        base_url: str,
        issue_key: str,
        token: str | None = None,
        username: str | None = None,
        lenses: list[str] | None = None,
    ) -> MarkdownIngestionResult:
        report = MarkdownIngestionResult()
        try:
            issue = self._fetch_issue(
                base_url, issue_key, token=token, username=username
            )
        except Exception as exc:
            report.errors.append(f"jira fetch failed: {exc}")
            return report

        key, summary, text = _fmt_issue(issue)
        source_path = f"{base_url.rstrip('/')}/browse/{key}"
        return self._md.ingest(
            text=text,
            title=f"{key}: {summary}",
            source_path=source_path,
            lenses=lenses,
            tags=["jira", key.split("-")[0].lower()],
        )

    # ---- internals ----------------------------------------------------

    def _fetch_issue(
        self,
        base_url: str,
        issue_key: str,
        *,
        token: str | None,
        username: str | None,
    ) -> dict[str, Any]:
        url = (
            f"{base_url.rstrip('/')}/rest/api/2/issue/{issue_key}"
            "?fields=summary,description,issuetype,status,priority,reporter,assignee,comment"
        )
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
