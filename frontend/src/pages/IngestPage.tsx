import { useEffect, useState } from "react";
import {
  ingestConfluence,
  ingestJira,
  ingestMarkdown,
  ingestRepository,
  listIngestJobs,
  type IngestResult,
  type IngestStatus,
} from "../api/client";
import { useViewStore } from "../store/view";
import { useRoute } from "../router";

type Tab = "markdown" | "git" | "confluence" | "jira";

const TABS: { id: Tab; label: string; description: string; icon: string }[] = [
  {
    id: "markdown",
    label: "Markdown",
    description: "Paste any markdown / plain-text doc and let the LLM build a graph",
    icon: "✎",
  },
  {
    id: "git",
    label: "Git Repository",
    description: "Clone GitHub / GitLab / any git URL, walk READMEs and architecture docs",
    icon: "⎇",
  },
  {
    id: "confluence",
    label: "Confluence",
    description: "Pull a page from Atlassian Confluence Cloud or Server",
    icon: "≡",
  },
  {
    id: "jira",
    label: "Jira",
    description: "Pull a single issue (summary, description, comments) from Jira",
    icon: "✓",
  },
];

const SAMPLE_MARKDOWN = `# Payments Platform — Architectural Overview

The Payments Platform processes credit-card and ACH transactions for the storefront.

## Components

- **api-gateway** is a Node.js service that fronts every public request.
- **payments-svc** is a Java service owned by team \`payments\`. It calls the
  Stripe API over REST and publishes settlement events to Kafka.
- **ledger-db** is a Postgres database storing immutable journal entries.
- **risk-svc** is a Python service owned by team \`risk\`. It consumes the
  settlement events and reads from \`ledger-db\` to score transactions for fraud.

## Flow

1. \`api-gateway\` forwards \`POST /charge\` to \`payments-svc\`.
2. \`payments-svc\` calls Stripe synchronously, then writes a row into \`ledger-db\`.
3. On commit, \`payments-svc\` publishes a \`settlement.created\` event to Kafka.
4. \`risk-svc\` consumes \`settlement.created\` and updates its fraud score.
`;

export function IngestPage() {
  const [tab, setTab] = useState<Tab>("markdown");
  const [jobs, setJobs] = useState<IngestStatus[]>([]);
  const [busy, setBusy] = useState(false);
  const [lastResult, setLastResult] = useState<IngestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshJobs = async () => {
    try {
      const fresh = await listIngestJobs();
      setJobs(
        fresh.sort((a, b) =>
          (b.started_at ?? "").localeCompare(a.started_at ?? "")
        )
      );
    } catch (e) {
      // Silently ignore — the user already saw the form-level error.
    }
  };

  useEffect(() => {
    refreshJobs();
    const handle = setInterval(refreshJobs, 4000);
    return () => clearInterval(handle);
  }, []);

  const runIngestion = async (fn: () => Promise<IngestResult>) => {
    setBusy(true);
    setError(null);
    setLastResult(null);
    try {
      const result = await fn();
      setLastResult(result);
      await refreshJobs();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <h1>Ingest documentation</h1>
        <p className="page-subtitle">
          Each ingestion saves the original document as a parent fragment, then
          uses the LLM (or the deterministic fallback) to extract entities,
          relationships and child fragments at multiple zoom levels.
        </p>
      </header>

      <section className="page-body ingest-body">
        <div className="ingest-tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`ingest-tab ${tab === t.id ? "active" : ""}`}
              onClick={() => setTab(t.id)}
              aria-pressed={tab === t.id}
            >
              <span className="ingest-tab-icon" aria-hidden>
                {t.icon}
              </span>
              <span>
                <span className="ingest-tab-label">{t.label}</span>
                <span className="ingest-tab-hint">{t.description}</span>
              </span>
            </button>
          ))}
        </div>

        <div className="ingest-pane">
          {tab === "markdown" && (
            <MarkdownForm
              busy={busy}
              run={(payload) => runIngestion(() => ingestMarkdown(payload))}
            />
          )}
          {tab === "git" && (
            <GitForm
              busy={busy}
              run={(payload) => runIngestion(() => ingestRepository(payload))}
            />
          )}
          {tab === "confluence" && (
            <ConfluenceForm
              busy={busy}
              run={(payload) => runIngestion(() => ingestConfluence(payload))}
            />
          )}
          {tab === "jira" && (
            <JiraForm
              busy={busy}
              run={(payload) => runIngestion(() => ingestJira(payload))}
            />
          )}

          {error && <div className="error" role="alert">{error}</div>}
          {lastResult && <ResultCard result={lastResult} />}
        </div>

        <div className="ingest-jobs">
          <header>
            <h2>Recent jobs</h2>
            <button
              type="button"
              className="text-button"
              onClick={refreshJobs}
              title="Refresh"
            >
              ⟳ refresh
            </button>
          </header>
          {jobs.length === 0 ? (
            <p className="muted">No ingestion jobs have run in this session.</p>
          ) : (
            <ul className="job-list">
              {jobs.map((j) => (
                <JobRow key={j.job_id} job={j} />
              ))}
            </ul>
          )}
        </div>
      </section>

      {tab === "markdown" && (
        <details className="ingest-help">
          <summary>Need a sample to try?</summary>
          <pre>{SAMPLE_MARKDOWN}</pre>
        </details>
      )}
    </div>
  );
}

function MarkdownForm({
  busy,
  run,
}: {
  busy: boolean;
  run: (payload: { text: string; title?: string; source_path?: string }) => void;
}) {
  const [title, setTitle] = useState("");
  const [source, setSource] = useState("");
  const [text, setText] = useState("");

  return (
    <form
      className="ingest-form"
      onSubmit={(ev) => {
        ev.preventDefault();
        if (!text.trim()) return;
        run({
          text,
          title: title || undefined,
          source_path: source || undefined,
        });
      }}
    >
      <Field label="Title" hint="Optional — used as the parent doc title">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Payments architecture"
        />
      </Field>
      <Field label="Source URL" hint="Optional — recorded as provenance">
        <input
          value={source}
          onChange={(e) => setSource(e.target.value)}
          placeholder="https://wiki.company.com/Payments"
        />
      </Field>
      <Field
        label="Document body"
        hint="Markdown or plain text — anything you want analysed"
      >
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={16}
          placeholder="# Payments Platform&#10;&#10;The Payments Platform consists of…"
        />
      </Field>
      <div className="form-actions">
        <button type="submit" className="primary" disabled={busy || !text.trim()}>
          {busy ? "Ingesting…" : "Ingest document"}
        </button>
        <button
          type="button"
          className="text-button"
          onClick={() => {
            setText(SAMPLE_MARKDOWN);
            setTitle("Payments Platform — Architectural Overview");
          }}
        >
          paste sample
        </button>
      </div>
    </form>
  );
}

function GitForm({
  busy,
  run,
}: {
  busy: boolean;
  run: (payload: { repo_url: string; branch: string }) => void;
}) {
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const looksLikeGitHub = /github\.com/i.test(url);
  const looksLikeGitLab = /gitlab\.com/i.test(url);

  return (
    <form
      className="ingest-form"
      onSubmit={(ev) => {
        ev.preventDefault();
        if (!url.trim()) return;
        run({ repo_url: url.trim(), branch: branch.trim() || "main" });
      }}
    >
      <Field label="Repository URL" hint="https + .git URL works for GitHub, GitLab, Bitbucket, …">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/org/repo.git"
          autoFocus
        />
      </Field>
      <Field label="Branch">
        <input
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          placeholder="main"
        />
      </Field>
      <p className="muted small">
        The connector clones a shallow copy, walks for README / docker-compose /
        proto / openapi files and feeds each through the same extraction
        pipeline.
        {looksLikeGitHub && " Detected: GitHub."}
        {looksLikeGitLab && " Detected: GitLab."}
      </p>
      <div className="form-actions">
        <button type="submit" className="primary" disabled={busy || !url.trim()}>
          {busy ? "Cloning…" : "Ingest repository"}
        </button>
      </div>
    </form>
  );
}

function ConfluenceForm({
  busy,
  run,
}: {
  busy: boolean;
  run: (payload: {
    base_url: string;
    page_id: string;
    token?: string;
    username?: string;
  }) => void;
}) {
  const [baseUrl, setBaseUrl] = useState("");
  const [pageId, setPageId] = useState("");
  const [username, setUsername] = useState("");
  const [token, setToken] = useState("");

  return (
    <form
      className="ingest-form"
      onSubmit={(ev) => {
        ev.preventDefault();
        if (!baseUrl.trim() || !pageId.trim()) return;
        run({
          base_url: baseUrl.trim(),
          page_id: pageId.trim(),
          username: username.trim() || undefined,
          token: token.trim() || undefined,
        });
      }}
    >
      <Field label="Base URL" hint="e.g. https://your-org.atlassian.net/wiki">
        <input
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder="https://your-org.atlassian.net/wiki"
        />
      </Field>
      <Field label="Page ID" hint="Numeric ID from Confluence (visible in the URL)">
        <input
          value={pageId}
          onChange={(e) => setPageId(e.target.value)}
          placeholder="123456789"
        />
      </Field>
      <div className="form-row">
        <Field label="Email / username" hint="For Atlassian Cloud — basic auth">
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="you@company.com"
          />
        </Field>
        <Field label="API token" hint="PAT or Atlassian API token">
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="••••••••"
          />
        </Field>
      </div>
      <div className="form-actions">
        <button
          type="submit"
          className="primary"
          disabled={busy || !baseUrl.trim() || !pageId.trim()}
        >
          {busy ? "Fetching…" : "Ingest Confluence page"}
        </button>
      </div>
    </form>
  );
}

function JiraForm({
  busy,
  run,
}: {
  busy: boolean;
  run: (payload: {
    base_url: string;
    issue_key: string;
    token?: string;
    username?: string;
  }) => void;
}) {
  const [baseUrl, setBaseUrl] = useState("");
  const [issueKey, setIssueKey] = useState("");
  const [username, setUsername] = useState("");
  const [token, setToken] = useState("");

  return (
    <form
      className="ingest-form"
      onSubmit={(ev) => {
        ev.preventDefault();
        if (!baseUrl.trim() || !issueKey.trim()) return;
        run({
          base_url: baseUrl.trim(),
          issue_key: issueKey.trim(),
          username: username.trim() || undefined,
          token: token.trim() || undefined,
        });
      }}
    >
      <Field label="Base URL" hint="https://your-org.atlassian.net">
        <input
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder="https://your-org.atlassian.net"
        />
      </Field>
      <Field label="Issue key" hint="e.g. PAY-123">
        <input
          value={issueKey}
          onChange={(e) => setIssueKey(e.target.value.toUpperCase())}
          placeholder="PAY-123"
        />
      </Field>
      <div className="form-row">
        <Field label="Email / username">
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="you@company.com"
          />
        </Field>
        <Field label="API token">
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="••••••••"
          />
        </Field>
      </div>
      <div className="form-actions">
        <button
          type="submit"
          className="primary"
          disabled={busy || !baseUrl.trim() || !issueKey.trim()}
        >
          {busy ? "Fetching…" : "Ingest Jira issue"}
        </button>
      </div>
    </form>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="ingest-field">
      <span className="ingest-field-label">
        {label}
        {hint && <em>{hint}</em>}
      </span>
      {children}
    </label>
  );
}

function ResultCard({ result }: { result: IngestResult }) {
  const setFocus = useViewStore((s) => s.setFocus);
  const { navigate } = useRoute();
  const ok = result.status === "succeeded";
  return (
    <div className={`result-card ${ok ? "ok" : "err"}`}>
      <div className="result-summary">
        <strong>{ok ? "Done." : "Finished with errors."}</strong>
        <span className="muted">{result.job_id}</span>
      </div>
      <div className="result-stats">
        <Stat label="docs" value={result.documents_processed ?? 0} />
        <Stat
          label="entities (new)"
          value={result.entities_created ?? 0}
        />
        <Stat
          label="entities (updated)"
          value={result.entities_updated ?? 0}
        />
        <Stat
          label="relationships"
          value={result.relationships_created ?? 0}
        />
        <Stat label="fragments" value={result.fragments_created ?? 0} />
      </div>
      {result.parent_fragment_id && (
        <div className="muted small">
          Parent fragment <code>{result.parent_fragment_id}</code> stored verbatim.
        </div>
      )}
      {result.errors && result.errors.length > 0 && (
        <details>
          <summary>{result.errors.length} extraction warning(s)</summary>
          <ul>
            {result.errors.map((e) => (
              <li key={e}>
                <code>{e}</code>
              </li>
            ))}
          </ul>
        </details>
      )}
      <div className="form-actions">
        <button
          type="button"
          className="text-button"
          onClick={() => {
            if (result.parent_fragment_id) {
              // not focusable, but still useful — go to view
            }
            navigate("view");
          }}
        >
          ↗ open the graph view
        </button>
        {result.parent_fragment_id && (
          <button
            type="button"
            className="text-button"
            onClick={() => {
              if (result.parent_fragment_id) {
                // The parent is a fragment, not an entity — focus the most
                // central freshly-created entity instead, if one exists.
                navigate("search");
              }
              if (result.parent_fragment_id) setFocus(result.parent_fragment_id);
            }}
          >
            ⌕ search the new fragments
          </button>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="result-stat">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function JobRow({ job }: { job: IngestStatus }) {
  const stateClass =
    job.status === "succeeded"
      ? "ok"
      : job.status === "failed"
        ? "err"
        : "running";
  const meta = job.metadata || {};
  const sourceLabel =
    typeof meta.source === "string" ? String(meta.source) : "unknown";
  const subtitle =
    sourceLabel === "git"
      ? `${meta.repo_url ?? ""}@${meta.branch ?? ""}`
      : sourceLabel === "markdown"
        ? `markdown · ${(meta.title as string) || (meta.bytes as number) + " bytes"}`
        : sourceLabel === "confluence"
          ? `confluence · page ${meta.page_id}`
          : sourceLabel === "jira"
            ? `jira · ${meta.issue_key}`
            : "";
  return (
    <li className={`job-row ${stateClass}`}>
      <div className="job-row-head">
        <span className={`job-status ${stateClass}`}>{job.status}</span>
        <code className="job-id">{job.job_id}</code>
        <span className="muted small">
          {job.finished_at
            ? new Date(job.finished_at).toLocaleTimeString()
            : "in progress"}
        </span>
      </div>
      <div className="muted small">{subtitle}</div>
      <div className="job-stats">
        <span>{job.documents_processed} docs</span>
        <span>{job.entities_created}+{job.entities_updated} entities</span>
        <span>{job.relationships_created} edges</span>
        <span>{job.fragments_created} fragments</span>
        {job.errors.length > 0 && <span className="err">{job.errors.length} errors</span>}
      </div>
    </li>
  );
}
