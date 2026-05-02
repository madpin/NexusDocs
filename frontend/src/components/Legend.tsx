import {
  ENGINE_GLYPH,
  FAMILY_ACCENT,
  FAMILY_LABEL,
  KIND_STYLE,
  type EntityFamily,
} from "../styles/palette";

const FAMILY_ORDER: EntityFamily[] = [
  "people",
  "architecture",
  "code",
  "datastore",
  "messaging",
  "infra",
];

/** What each family contains, in user-facing terms.
 *
 * The first item in `kinds` is the "headline" kind shown next to the
 * swatch; the rest follow as a small comma-separated list. We deliberately
 * mention specific data-store engines (postgres, redis, …) and queue
 * protocols (kafka, rabbitmq, …) because those are the icons that
 * actually appear on the canvas — the family-level glyph is just a
 * fallback when no engine is configured.
 */
const FAMILY_KINDS: Record<EntityFamily, string[]> = {
  people: ["person", "team", "division"],
  architecture: ["system", "service", "api_endpoint"],
  code: ["class", "function"],
  datastore: ["database", "cache"],
  messaging: ["kafka_cluster", "kafka_topic", "queue"],
  infra: ["repository", "environment"],
  other: ["fallback"],
};

const FAMILY_ENGINES: Partial<Record<EntityFamily, string[]>> = {
  datastore: ["postgres", "mysql", "mongodb", "cassandra", "redis"],
  messaging: ["kafka", "rabbitmq", "sqs", "nats"],
};

interface Props {
  highlight?: Set<EntityFamily>;
}

export function Legend({ highlight }: Props) {
  return (
    <div className="legend" aria-label="Entity color legend">
      {FAMILY_ORDER.map((fam) => {
        const dim = highlight && !highlight.has(fam);
        const kinds = FAMILY_KINDS[fam] ?? [];
        const engines = FAMILY_ENGINES[fam] ?? [];
        return (
          <div
            key={fam}
            className="legend-row"
            style={{ opacity: dim ? 0.45 : 1, transition: "opacity 200ms ease" }}
          >
            <span className="swatch" style={{ background: FAMILY_ACCENT[fam] }} />
            <span className="label">{FAMILY_LABEL[fam]}</span>
            <span className="legend-glyphs" aria-hidden>
              {kinds.map((k) => {
                const glyph = KIND_STYLE[k]?.glyph;
                if (!glyph) return null;
                return (
                  <span key={k} className="legend-glyph" title={k}>
                    {glyph}
                  </span>
                );
              })}
              {engines.map((eng) => (
                <span key={eng} className="legend-glyph engine" title={eng}>
                  {ENGINE_GLYPH[eng]}
                </span>
              ))}
            </span>
          </div>
        );
      })}
    </div>
  );
}
