import type { RankedFragment } from "../api/client";

interface Props {
  fragment: RankedFragment;
}

export function FragmentCard({ fragment }: Props) {
  const conf =
    fragment.confidence >= 0.85
      ? "confidence-high"
      : fragment.confidence < 0.6
      ? "confidence-low"
      : "";

  return (
    <article className="fragment-card">
      <div className="badges">
        <span className="badge rank">#{fragment.rank}</span>
        {fragment.lifted && (
          <span className="badge lifted" title="Lifted into view due to topology / path">
            lifted
          </span>
        )}
        {fragment.reviewed && (
          <span className="badge reviewed" title="Reviewed by a human">
            reviewed
          </span>
        )}
        <span className={`badge ${conf}`} title="Source confidence">
          conf {fragment.confidence.toFixed(2)}
        </span>
        {fragment.lenses.map((l) => (
          <span key={l} className="badge lens" data-lens={l}>
            {l}
          </span>
        ))}
      </div>
      <h4>{fragment.title}</h4>
      <div className="body">{fragment.body}</div>
      {fragment.source_path && <div className="source">{fragment.source_path}</div>}
    </article>
  );
}
