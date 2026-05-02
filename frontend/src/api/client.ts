/**
 * Minimal client for the NexusDocs API. Hand-written types live next to
 * each function so the UI works without running `openapi-typescript` first.
 * Run `npm run gen:api` to regenerate the full schema.d.ts when the
 * backend is running.
 */

const BASE = "/api/v1";

export interface Entity {
  id: string;
  kind: string;
  name: string;
  parent?: string | null;
  labels: string[];
  metadata: Record<string, unknown>;
}

export interface Relationship {
  id: string;
  source: string;
  target: string;
  type: string;
  protocol?: string | null;
  mode?: string | null;
  metadata: Record<string, unknown>;
}

export interface RankedFragment {
  id: string;
  title: string;
  body: string;
  rank: number;
  effective_zoom_min: number;
  lifted: boolean;
  lenses: string[];
  confidence: number;
  reviewed: boolean;
  source_path?: string | null;
}

export interface RenderedView {
  summary: string;
  diagram: string;
  fragments: RankedFragment[];
  entities: Entity[];
  relationships: Relationship[];
  topology_highlights: {
    most_central: string | null;
    structural_concerns: string[];
  };
  follow_up_suggestions: string[];
}

export interface ViewRequestBody {
  focus: string;
  zoom: number;
  lenses: string[];
  radius: number;
  filters?: {
    entity_kinds?: string[];
    relationship_types?: string[];
    protocols?: string[];
    tags?: string[];
  };
  navigation_path?: string[];
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "content-type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return (await res.json()) as T;
}

export async function renderView(req: ViewRequestBody): Promise<RenderedView> {
  return call<RenderedView>("/views/render", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function listEntities(): Promise<Entity[]> {
  return call<Entity[]>("/entities");
}

export interface SearchHit {
  kind: "entity" | "relationship" | "fragment";
  id: string;
  score: number;
  snippet?: string | null;
}

export async function search(
  query: string,
  scope: "entities" | "relationships" | "fragments" | "all" = "all"
): Promise<{ hits: SearchHit[] }> {
  return call<{ hits: SearchHit[] }>("/search", {
    method: "POST",
    body: JSON.stringify({ query, scope }),
  });
}

// ---- Ingestion -----------------------------------------------------------

export interface IngestResult {
  job_id: string;
  status: string;
  documents_processed?: number;
  entities_created?: number;
  entities_updated?: number;
  relationships_created?: number;
  fragments_created?: number;
  parent_fragment_id?: string | null;
  errors?: string[];
  metadata?: Record<string, unknown>;
}

export interface IngestStatus {
  job_id: string;
  status: string;
  progress: number;
  documents_processed: number;
  entities_created: number;
  entities_updated: number;
  relationships_created: number;
  fragments_created: number;
  errors: string[];
  started_at: string | null;
  finished_at: string | null;
  metadata: Record<string, unknown>;
}

export async function ingestMarkdown(payload: {
  text: string;
  title?: string | null;
  source_path?: string | null;
  lenses?: string[] | null;
}): Promise<IngestResult> {
  return call<IngestResult>("/ingest/markdown", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function ingestRepository(payload: {
  repo_url: string;
  branch?: string;
}): Promise<IngestResult> {
  return call<IngestResult>("/ingest/repository", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function ingestConfluence(payload: {
  base_url: string;
  page_id: string;
  token?: string;
  username?: string;
  lenses?: string[] | null;
}): Promise<IngestResult> {
  return call<IngestResult>("/ingest/confluence", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function ingestJira(payload: {
  base_url: string;
  issue_key: string;
  token?: string;
  username?: string;
  lenses?: string[] | null;
}): Promise<IngestResult> {
  return call<IngestResult>("/ingest/jira", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listIngestJobs(): Promise<IngestStatus[]> {
  return call<IngestStatus[]>("/ingest");
}

// ---- Settings / meta -----------------------------------------------------

export interface SettingsView {
  repository_backend: string;
  neo4j_uri: string;
  neo4j_user: string;
  neo4j_database: string;
  openai_api_key_set: boolean;
  openai_model: string;
  openai_base_url: string | null;
  api_host: string;
  api_port: number;
  api_cors_origins: string[];
  llm_client: string;
}

export interface SettingsPatchBody {
  openai_api_key?: string;
  openai_model?: string;
  openai_base_url?: string;
}

export async function getSettings(): Promise<SettingsView> {
  return call<SettingsView>("/settings");
}

export async function patchSettings(body: SettingsPatchBody): Promise<SettingsView> {
  return call<SettingsView>("/settings", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export interface Meta {
  name: string;
  version: string;
  tagline: string;
  homepage: string;
  license: string;
  totals: { entities: number; relationships: number; fragments: number };
  entities_by_kind: Record<string, number>;
  fragments_by_lens: Record<string, number>;
}

export async function getMeta(): Promise<Meta> {
  return call<Meta>("/meta");
}
