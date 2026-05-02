export function HelpPage() {
  return (
    <div className="page">
      <header className="page-header">
        <h1>Help &amp; concepts</h1>
        <p className="page-subtitle">
          A one-page cheat-sheet of the vocabulary NexusDocs uses across every
          screen. Skim once and the rest of the UI clicks into place.
        </p>
      </header>

      <section className="page-body help-body">
        <ConceptCard
          title="Knowledge graph"
          glyph="◎"
          family="architecture"
          description={
            <>
              Everything you ingest becomes nodes (<strong>entities</strong>) and
              edges (<strong>relationships</strong>) in a single graph. A
              service, a team, a database, a person — all entities. A REST call,
              a Kafka topic, a team membership — all relationships.
            </>
          }
          examples={["service.payments-svc → calls → service.stripe", "team.payments → owns → service.payments-svc"]}
        />

        <ConceptCard
          title="DocFragment"
          glyph="✎"
          family="people"
          description={
            <>
              Documentation lives in chunks called <strong>fragments</strong>.
              Each fragment is anchored to entities/relationships, has a
              coverage range on the zoom axis and is tagged with one or more
              lenses. Fragments may be human-authored or LLM-extracted.
            </>
          }
          examples={[
            "title: 'Why payments-svc is sync to Stripe'",
            "subjects: [service.payments-svc] · zoom: 30–70 · lens: technical",
          ]}
        />

        <ConceptCard
          title="Zoom axis"
          glyph="↕"
          family="datastore"
          description={
            <>
              A continuous slider from <code>0</code> (galaxy view) to{" "}
              <code>100</code> (line of code). Each fragment declares the zoom
              range it is relevant for; the view engine only includes fragments
              whose <code>zoom_min ≤ z ≤ zoom_max</code>. <em>Lifting</em> can
              promote critical fragments to be visible at higher altitudes.
            </>
          }
          examples={[
            "z=10 → companies, divisions",
            "z=35 → teams, services",
            "z=80 → APIs, classes",
          ]}
        />

        <ConceptCard
          title="Lenses"
          glyph="⌖"
          family="messaging"
          description={
            <>
              Perspective filters. Each fragment lists the lenses it is useful
              under: <code>technical</code>, <code>product</code>,{" "}
              <code>operations</code>, <code>onboarding</code>,{" "}
              <code>debug</code>, <code>client</code>. The picker on the View
              page toggles which fragments are eligible for the current view.
            </>
          }
          examples={[
            "lens: technical → API contracts, sync vs async details",
            "lens: onboarding → glossary, ownership, on-call",
          ]}
        />

        <ConceptCard
          title="Topology-aware relevance"
          glyph="⌬"
          family="infra"
          description={
            <>
              Beyond text matching, the engine ranks fragments by graph
              centrality, the user&rsquo;s current focus, and how they navigated
              there. Fragments anchored to high-centrality entities or to nodes
              on the navigation path get a boost.
            </>
          }
          examples={[
            "Most central node automatically lifts its key fragments",
            "Navigation path = bread-crumb of recent focus changes",
          ]}
        />

        <ConceptCard
          title="Ingestion"
          glyph="⤴"
          family="code"
          description={
            <>
              Documents enter the graph through ingestion connectors. Markdown,
              git repos (GitHub, GitLab, …), Confluence pages and Jira issues
              all share the same pipeline: store the source as the parent
              fragment, then run the LLM extractor to derive entities,
              relationships and child fragments.
            </>
          }
          examples={[
            "POST /api/v1/ingest/markdown",
            "POST /api/v1/ingest/repository",
            "POST /api/v1/ingest/confluence",
            "POST /api/v1/ingest/jira",
          ]}
        />

        <ConceptCard
          title="Provenance"
          glyph="🛈"
          family="other"
          description={
            <>
              Every entity, relationship and fragment records where it came
              from: source type, path, hash, generator (human / LLM / hybrid)
              and a confidence score. Conflicts are resolved with a strict
              precedence: <strong>human &gt; reviewed-LLM &gt; unreviewed-LLM</strong>.
            </>
          }
          examples={[
            "source_type: confluence · source_path: …/pages/12345",
            "generated_by: llm · confidence: 0.78 · reviewed: false",
          ]}
        />

        <details className="help-details">
          <summary>Keyboard shortcuts</summary>
          <ul>
            <li>
              <code>?</code> — open this help page (from anywhere with focus on
              the navigation rail).
            </li>
            <li>
              <code>/</code> — jump to search.
            </li>
            <li>
              <code>Esc</code> — clear the current search query.
            </li>
          </ul>
        </details>
      </section>
    </div>
  );
}

interface CardProps {
  title: string;
  glyph: string;
  family:
    | "people"
    | "architecture"
    | "code"
    | "datastore"
    | "messaging"
    | "infra"
    | "other";
  description: React.ReactNode;
  examples: string[];
}

function ConceptCard({ title, glyph, family, description, examples }: CardProps) {
  return (
    <article className={`concept-card family-${family}`}>
      <header>
        <span className="concept-glyph" aria-hidden>
          {glyph}
        </span>
        <h2>{title}</h2>
      </header>
      <p>{description}</p>
      <ul className="concept-examples">
        {examples.map((e) => (
          <li key={e}>
            <code>{e}</code>
          </li>
        ))}
      </ul>
    </article>
  );
}
