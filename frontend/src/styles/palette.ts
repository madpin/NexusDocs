/**
 * Visual palette shared between the graph canvas, legend and badges.
 * Colors are grouped into entity "families" so related kinds are
 * visually clustered without becoming indistinguishable.
 */

export type EntityFamily =
  | "people"
  | "architecture"
  | "code"
  | "datastore"
  | "messaging"
  | "infra"
  | "other";

export interface KindStyle {
  family: EntityFamily;
  fill: string;
  border: string;
  text: string;
  glyph: string;
}

const PEOPLE: Pick<KindStyle, "family" | "fill" | "border" | "text"> = {
  family: "people",
  fill: "#2f2547",
  border: "#a98ce0",
  text: "#efe1ff",
};
const ARCH: Pick<KindStyle, "family" | "fill" | "border" | "text"> = {
  family: "architecture",
  fill: "#162e44",
  border: "#6cb1ff",
  text: "#dfeaff",
};
const CODE: Pick<KindStyle, "family" | "fill" | "border" | "text"> = {
  family: "code",
  fill: "#173a35",
  border: "#5fcfa3",
  text: "#dcf6ec",
};
const STORE: Pick<KindStyle, "family" | "fill" | "border" | "text"> = {
  family: "datastore",
  fill: "#1d3a1d",
  border: "#7ec57e",
  text: "#defce0",
};
const MSG: Pick<KindStyle, "family" | "fill" | "border" | "text"> = {
  family: "messaging",
  fill: "#3a2a13",
  border: "#f1a13b",
  text: "#fff0d6",
};
const INFRA: Pick<KindStyle, "family" | "fill" | "border" | "text"> = {
  family: "infra",
  fill: "#2a2f3a",
  border: "#a0a8b8",
  text: "#e8eaf0",
};
const OTHER: Pick<KindStyle, "family" | "fill" | "border" | "text"> = {
  family: "other",
  fill: "#1d2230",
  border: "#3a4254",
  text: "#cfd5e2",
};

export const KIND_STYLE: Record<string, KindStyle> = {
  company: { ...PEOPLE, glyph: "🏢" },
  division: { ...PEOPLE, glyph: "🏛" },
  tribe: { ...PEOPLE, glyph: "🪶" },
  team: { ...PEOPLE, glyph: "👥" },
  person: { ...PEOPLE, glyph: "👤" },

  system: { ...ARCH, glyph: "🌐" },
  service: { ...ARCH, glyph: "⚙️" },
  component: { ...ARCH, glyph: "🧩" },
  api_endpoint: { ...ARCH, glyph: "🔌" },
  contract: { ...ARCH, glyph: "📜" },

  class: { ...CODE, glyph: "🅒" },
  function: { ...CODE, glyph: "ƒ" },
  module: { ...CODE, glyph: "📦" },
  package: { ...CODE, glyph: "📦" },

  database: { ...STORE, glyph: "🗄️" },
  table: { ...STORE, glyph: "▦" },
  cache: { ...STORE, glyph: "⚡" },

  kafka_cluster: { ...MSG, glyph: "🐙" },
  kafka_topic: { ...MSG, glyph: "📨" },
  queue: { ...MSG, glyph: "📥" },

  repository: { ...INFRA, glyph: "📁" },
  environment: { ...INFRA, glyph: "🌎" },
  feature_flag: { ...INFRA, glyph: "🚩" },
};

/**
 * Engine / protocol icons used to specialise generic kinds.
 *
 * A `database` entity is just "any database" until you also know its
 * `metadata.engine`; once you do, the elephant for postgres or the
 * dolphin for mysql is much more recognisable than the generic 🗄 icon.
 *
 * This map is consulted by `styleFor(kind, engine)`. When no specific
 * engine icon is found we fall back to the kind-level glyph.
 */
export const ENGINE_GLYPH: Record<string, string> = {
  // Relational
  postgres: "🐘",
  postgresql: "🐘",
  mysql: "🐬",
  mariadb: "🐬",
  sqlite: "📒",
  oracle: "🅾️",
  mssql: "🟥",

  // NoSQL / wide-column / document
  mongodb: "🍃",
  cassandra: "✦",
  scylla: "✦",
  couchdb: "🛋",
  dynamodb: "🪐",
  bigtable: "🪐",
  cosmos: "✨",

  // KV / cache
  redis: "🟥",
  memcached: "🟨",
  elasticache: "🟥",

  // Search / analytics
  elastic: "🔎",
  elasticsearch: "🔎",
  opensearch: "🔎",
  snowflake: "❄️",
  bigquery: "📊",
  redshift: "📊",
  clickhouse: "📊",

  // Streams / queues / pubsub
  kafka: "🐙",
  rabbitmq: "🐰",
  amqp: "🐰",
  sqs: "📨",
  sns: "📡",
  pubsub: "📡",
  nats: "🛰",
  pulsar: "🛰",
  kinesis: "🌊",

  // Object storage / artifacts
  s3: "🪣",
  gcs: "🪣",
  azureblob: "🪣",
  minio: "🪣",
};

/**
 * Some entity kinds only make sense with their engine. For others the
 * engine is a nice-to-have. This helper picks the most specific glyph
 * available, falling back to the kind-level glyph.
 */
export function styleFor(kind: string, engine?: string | null): KindStyle {
  const base = KIND_STYLE[kind] ?? { ...OTHER, glyph: "•" };
  if (!engine) return base;
  const key = engine.toLowerCase().replace(/[\s_-]/g, "");
  const enriched = ENGINE_GLYPH[key];
  if (!enriched) return base;
  return { ...base, glyph: enriched };
}

/** Stable color per entity family — used in the legend. */
export const FAMILY_LABEL: Record<EntityFamily, string> = {
  people: "People & Org",
  architecture: "Systems & Services",
  code: "Code",
  datastore: "Data Stores",
  messaging: "Messaging",
  infra: "Infra & Repos",
  other: "Other",
};

export const FAMILY_ACCENT: Record<EntityFamily, string> = {
  people: "#a98ce0",
  architecture: "#6cb1ff",
  code: "#5fcfa3",
  datastore: "#7ec57e",
  messaging: "#f1a13b",
  infra: "#a0a8b8",
  other: "#5d6878",
};

/** Edge color resolution. Protocol wins, otherwise relationship-type. */
export const PROTOCOL_COLOR: Record<string, string> = {
  rest: "#6cb1ff",
  grpc: "#7ed4ff",
  graphql: "#ff77c4",
  websocket: "#aab2ff",
  kafka: "#f1a13b",
  amqp: "#f1a13b",
  postgres: "#7ec57e",
  mysql: "#7ec57e",
  mongodb: "#7ec57e",
  redis: "#ef6075",
};

export const REL_TYPE_COLOR: Record<string, string> = {
  member_of: "#a98ce0",
  leads: "#a98ce0",
  manages: "#a98ce0",
  reports_to: "#a98ce0",
  owns: "#c2a8f0",
  belongs_to: "#5d6878",
  depends_on: "#6cb1ff",
  calls_api: "#6cb1ff",
  provides_api: "#7ed4ff",
  publishes_to: "#f1a13b",
  subscribes_to: "#f1a13b",
  writes_to: "#7ec57e",
  reads_from: "#7ec57e",
};

export function edgeColor(type: string, protocol?: string | null): string {
  if (protocol && PROTOCOL_COLOR[protocol]) return PROTOCOL_COLOR[protocol];
  if (REL_TYPE_COLOR[type]) return REL_TYPE_COLOR[type];
  return "#5d6878";
}

/** Edge style hint for sync vs async traffic. */
export function edgeDash(mode?: string | null): string {
  if (mode === "async") return "6 4";
  return "solid";
}
