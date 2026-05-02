import { useEffect, useMemo, useRef, useState } from "react";
import { search, type SearchHit } from "../api/client";
import { useRoute } from "../router";
import { useViewStore } from "../store/view";

type Scope = "all" | "entities" | "relationships" | "fragments";

const SCOPES: { id: Scope; label: string }[] = [
  { id: "all", label: "All" },
  { id: "entities", label: "Entities" },
  { id: "relationships", label: "Relationships" },
  { id: "fragments", label: "Fragments" },
];

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [scope, setScope] = useState<Scope>("all");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hits, setHits] = useState<SearchHit[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const setFocus = useViewStore((s) => s.setFocus);
  const { navigate } = useRoute();

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!query.trim()) {
      setHits([]);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    const handle = setTimeout(() => {
      search(query.trim(), scope)
        .then((r) => {
          if (!cancelled) setHits(r.hits);
        })
        .catch((e: Error) => {
          if (!cancelled) setError(e.message);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 220);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [query, scope]);

  const grouped = useMemo(() => {
    const out: Record<string, SearchHit[]> = {
      entity: [],
      relationship: [],
      fragment: [],
    };
    for (const h of hits) out[h.kind]?.push(h);
    return out;
  }, [hits]);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Search the graph</h1>
        <p className="page-subtitle">
          Look across entities, relationships and documentation fragments. Click
          any entity hit to open it in the graph.
        </p>
      </header>

      <section className="page-body search-body">
        <div className="search-bar">
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Try: payments, kafka, team:risk, status, …"
            className="search-input"
            type="search"
            aria-label="Search query"
          />
          <div className="search-scope" role="group" aria-label="Scope">
            {SCOPES.map((s) => (
              <button
                key={s.id}
                type="button"
                className={`chip ${scope === s.id ? "active" : ""}`}
                onClick={() => setScope(s.id)}
                aria-pressed={scope === s.id}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        <div className="search-meta">
          {loading && <span className="muted">searching…</span>}
          {!loading && query && (
            <span className="muted">
              {hits.length} hit{hits.length === 1 ? "" : "s"} for{" "}
              <code>{query}</code>
            </span>
          )}
          {error && <span className="error inline">{error}</span>}
        </div>

        {!query && <SearchEmpty />}

        {query && (
          <div className="search-groups">
            <SearchGroup
              title="Entities"
              hint="open in the graph view"
              hits={grouped.entity ?? []}
              onSelect={(id) => {
                setFocus(id);
                navigate("view");
              }}
            />
            <SearchGroup
              title="Relationships"
              hint="topology edges that match"
              hits={grouped.relationship ?? []}
            />
            <SearchGroup
              title="Fragments"
              hint="documentation chunks that match"
              hits={grouped.fragment ?? []}
            />
          </div>
        )}
      </section>
    </div>
  );
}

function SearchGroup({
  title,
  hint,
  hits,
  onSelect,
}: {
  title: string;
  hint: string;
  hits: SearchHit[];
  onSelect?: (id: string) => void;
}) {
  if (hits.length === 0) return null;
  return (
    <section className="search-group">
      <header>
        <h2>{title}</h2>
        <span className="muted small">
          {hits.length} · {hint}
        </span>
      </header>
      <ul>
        {hits.map((h) => (
          <li
            key={h.id}
            className={`search-hit ${onSelect ? "clickable" : ""}`}
            onClick={() => onSelect?.(h.id)}
            role={onSelect ? "button" : undefined}
            tabIndex={onSelect ? 0 : undefined}
            onKeyDown={(ev) => {
              if (onSelect && (ev.key === "Enter" || ev.key === " ")) {
                ev.preventDefault();
                onSelect(h.id);
              }
            }}
          >
            <div className="search-hit-head">
              <code>{h.id}</code>
              <span className="muted small">score {h.score.toFixed(2)}</span>
            </div>
            {h.snippet && <div className="search-hit-snippet">{h.snippet}</div>}
          </li>
        ))}
      </ul>
    </section>
  );
}

function SearchEmpty() {
  return (
    <div className="search-empty">
      <h3>Search anything in the graph</h3>
      <ul>
        <li>
          Type an entity name like <code>payments</code> or <code>ledger-db</code>{" "}
          to find services and infrastructure.
        </li>
        <li>
          Search for a relationship type like <code>publishes</code> or{" "}
          <code>depends_on</code> to find topology edges.
        </li>
        <li>
          Search prose like <code>fraud score</code> to surface documentation
          fragments.
        </li>
      </ul>
    </div>
  );
}
