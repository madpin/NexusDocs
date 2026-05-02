import { useEffect, useState } from "react";
import { getMeta, type Meta } from "../api/client";

export function AboutPage() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMeta()
      .then(setMeta)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <h1>About NexusDocs</h1>
        <p className="page-subtitle">
          Topology-aware documentation built around a knowledge graph and a
          continuous zoom axis. Browse architecture from the org-chart down to
          a single API call without context-switching across tools.
        </p>
      </header>

      <section className="page-body about-body">
        {error && <div className="error">{error}</div>}
        {meta && (
          <>
            <article className="about-card">
              <header>
                <h2>{meta.name}</h2>
                <span className="pill pill-ok">v{meta.version}</span>
              </header>
              <p>{meta.tagline}</p>
              <ul className="about-links">
                <li>
                  Repository:{" "}
                  <a href={meta.homepage} target="_blank" rel="noreferrer">
                    {meta.homepage}
                  </a>
                </li>
                <li>License: {meta.license}</li>
              </ul>
            </article>

            <article className="about-card">
              <header>
                <h2>Graph at a glance</h2>
              </header>
              <div className="totals">
                <Total label="Entities" value={meta.totals.entities} />
                <Total label="Relationships" value={meta.totals.relationships} />
                <Total label="Fragments" value={meta.totals.fragments} />
              </div>
            </article>

            <article className="about-card">
              <header>
                <h2>Entities by kind</h2>
              </header>
              <BarList counts={meta.entities_by_kind} />
            </article>

            <article className="about-card">
              <header>
                <h2>Fragments by lens</h2>
              </header>
              <BarList counts={meta.fragments_by_lens} />
            </article>

            <article className="about-card">
              <header>
                <h2>Stack</h2>
              </header>
              <ul className="stack-list">
                <li>
                  <strong>Backend</strong> — FastAPI, Pydantic v2, Typer CLI,
                  pytest, ruff, pyright.
                </li>
                <li>
                  <strong>Graph</strong> — Neo4j 5 (production), NetworkX
                  (in-memory dev/testing).
                </li>
                <li>
                  <strong>LLM</strong> — OpenAI-compatible client (works with
                  Azure OpenAI, Ollama, vLLM, LM Studio, OpenRouter, …).
                </li>
                <li>
                  <strong>Frontend</strong> — React + Vite + TypeScript +
                  Cytoscape + Mermaid.
                </li>
                <li>
                  <strong>Infra</strong> — Docker Compose for the whole stack
                  in one command.
                </li>
              </ul>
            </article>
          </>
        )}
      </section>
    </div>
  );
}

function Total({ label, value }: { label: string; value: number }) {
  return (
    <div className="total-card">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function BarList({ counts }: { counts: Record<string, number> }) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) {
    return <p className="muted">No data yet — try ingesting a document first.</p>;
  }
  const max = entries[0][1] || 1;
  return (
    <ul className="bar-list">
      {entries.map(([k, v]) => (
        <li key={k}>
          <span className="bar-label">{k}</span>
          <span className="bar-track">
            <span
              className="bar-fill"
              style={{ width: `${(v / max) * 100}%` }}
              aria-label={`${v}`}
            />
          </span>
          <span className="bar-value">{v}</span>
        </li>
      ))}
    </ul>
  );
}
