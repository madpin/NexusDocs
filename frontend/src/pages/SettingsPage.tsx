import { useEffect, useState } from "react";
import { getSettings, patchSettings, type SettingsView } from "../api/client";

export function SettingsPage() {
  const [settings, setSettings] = useState<SettingsView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);

  const [apiKey, setApiKey] = useState("");
  const [keepKey, setKeepKey] = useState(true);
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");

  useEffect(() => {
    getSettings()
      .then((s) => {
        setSettings(s);
        setModel(s.openai_model);
        setBaseUrl(s.openai_base_url ?? "");
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const apply = async () => {
    setBusy(true);
    setError(null);
    try {
      const body: Record<string, string> = {};
      if (!keepKey) body.openai_api_key = apiKey;
      if (model) body.openai_model = model;
      // Empty string clears the base URL deliberately.
      body.openai_base_url = baseUrl.trim();
      const next = await patchSettings(body);
      setSettings(next);
      setApiKey("");
      setKeepKey(true);
      setSavedAt(new Date());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <h1>Settings</h1>
        <p className="page-subtitle">
          Inspect the active configuration and override the LLM bindings at
          runtime. Changes here are <strong>not persisted</strong> — they reset
          when the API process restarts. To persist, set the matching{" "}
          <code>NEXUSDOCS_*</code> environment variables.
        </p>
      </header>

      <section className="page-body settings-body">
        {error && <div className="error">{error}</div>}
        {!settings ? (
          <p className="muted">Loading settings…</p>
        ) : (
          <>
            <div className="settings-grid">
              <SettingsCard title="Repository">
                <Row label="Backend" value={<Badge>{settings.repository_backend}</Badge>} />
                <Row label="Neo4j URI" value={<code>{settings.neo4j_uri}</code>} />
                <Row label="User" value={settings.neo4j_user} />
                <Row label="Database" value={settings.neo4j_database} />
              </SettingsCard>

              <SettingsCard title="API">
                <Row
                  label="Listening on"
                  value={
                    <code>
                      {settings.api_host}:{settings.api_port}
                    </code>
                  }
                />
                <Row
                  label="CORS origins"
                  value={settings.api_cors_origins.join(", ") || "—"}
                />
                <Row
                  label="LLM client"
                  value={
                    <Badge tone={settings.llm_client === "OpenAIClient" ? "ok" : "muted"}>
                      {settings.llm_client}
                    </Badge>
                  }
                />
              </SettingsCard>
            </div>

            <SettingsCard title="LLM bindings">
              <p className="muted small">
                NexusDocs talks to OpenAI by default, but any OpenAI-compatible
                server (Azure OpenAI, Ollama, vLLM, LM Studio, OpenRouter, …)
                works — just point the base URL at it.
              </p>

              <Row
                label="API key"
                value={
                  <Badge tone={settings.openai_api_key_set ? "ok" : "warn"}>
                    {settings.openai_api_key_set ? "configured" : "not set"}
                  </Badge>
                }
              />

              <div className="form-grid">
                <label className="ingest-field">
                  <span className="ingest-field-label">
                    OpenAI API key
                    <em>
                      paste a new key, or check &ldquo;keep current&rdquo; to leave it
                      untouched
                    </em>
                  </span>
                  <input
                    type="password"
                    value={apiKey}
                    placeholder={
                      settings.openai_api_key_set ? "•••••••• (set)" : "sk-…"
                    }
                    onChange={(e) => {
                      setApiKey(e.target.value);
                      setKeepKey(false);
                    }}
                  />
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={keepKey}
                      onChange={(e) => {
                        setKeepKey(e.target.checked);
                        if (e.target.checked) setApiKey("");
                      }}
                    />
                    <span>Keep current key</span>
                  </label>
                </label>

                <label className="ingest-field">
                  <span className="ingest-field-label">
                    Model
                    <em>e.g. gpt-4o-mini, gpt-4o, llama3:70b, ...</em>
                  </span>
                  <input
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    placeholder="gpt-4o-mini"
                  />
                </label>

                <label className="ingest-field">
                  <span className="ingest-field-label">
                    Base URL
                    <em>
                      leave empty for OpenAI; set for self-hosted /
                      OpenAI-compatible endpoints
                    </em>
                  </span>
                  <input
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    placeholder="https://api.openai.com/v1"
                  />
                </label>
              </div>

              <div className="form-actions">
                <button
                  type="button"
                  className="primary"
                  disabled={busy}
                  onClick={apply}
                >
                  {busy ? "Saving…" : "Apply runtime overrides"}
                </button>
                {savedAt && (
                  <span className="muted small">
                    saved at {savedAt.toLocaleTimeString()}
                  </span>
                )}
              </div>
            </SettingsCard>
          </>
        )}
      </section>
    </div>
  );
}

function SettingsCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <article className="settings-card">
      <header>
        <h2>{title}</h2>
      </header>
      <div className="settings-card-body">{children}</div>
    </article>
  );
}

function Row({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="settings-row">
      <span className="lhs">{label}</span>
      <span className="rhs">{value}</span>
    </div>
  );
}

function Badge({
  children,
  tone = "muted",
}: {
  children: React.ReactNode;
  tone?: "ok" | "warn" | "err" | "muted";
}) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}
