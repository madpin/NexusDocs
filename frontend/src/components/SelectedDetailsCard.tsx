import { useMemo } from "react";
import type { Entity, Relationship, RenderedView } from "../api/client";
import { FAMILY_LABEL, edgeColor, styleFor } from "../styles/palette";
import { useViewStore } from "../store/view";

interface Props {
  view: RenderedView;
}

/**
 * Renders metadata for the entity the user has *single-clicked* on.
 *
 * The selected state is intentionally distinct from `focus`:
 *   * single click  → preview here without rerendering the graph,
 *   * double click  → promote to focus and re-extract the viewport.
 *
 * If nothing is selected (or the selection is the focus itself), the card
 * collapses so the rest of the right pane keeps its layout. Selecting the
 * focus would just duplicate the existing summary, so we treat that as
 * "nothing selected".
 */
export function SelectedDetailsCard({ view }: Props) {
  const selected = useViewStore((s) => s.selected);
  const focus = useViewStore((s) => s.focus);
  const setFocus = useViewStore((s) => s.setFocus);
  const setSelected = useViewStore((s) => s.setSelected);

  const entity = useMemo(() => {
    if (!selected || selected === focus) return null;
    return view.entities.find((e) => e.id === selected) ?? null;
  }, [view.entities, selected, focus]);

  const neighbours = useMemo(() => {
    if (!entity) return [] as Array<{ rel: Relationship; other: Entity }>;
    const byId = new Map(view.entities.map((e) => [e.id, e]));
    const result: Array<{ rel: Relationship; other: Entity }> = [];
    for (const rel of view.relationships) {
      const otherId =
        rel.source === entity.id
          ? rel.target
          : rel.target === entity.id
            ? rel.source
            : null;
      if (!otherId) continue;
      const other = byId.get(otherId);
      if (!other) continue;
      result.push({ rel, other });
    }
    return result.slice(0, 8);
  }, [entity, view.entities, view.relationships]);

  if (!entity) return null;

  const engine = readEngine(entity);
  const style = styleFor(entity.kind, engine);
  const md = (entity.metadata ?? {}) as Record<string, unknown>;
  const metadataEntries = Object.entries(md)
    .filter(([k, v]) => v != null && v !== "" && !["engine"].includes(k))
    .slice(0, 6);

  return (
    <div
      className="selected-card"
      style={{
        borderColor: style.border,
        background: `linear-gradient(180deg, ${style.fill}cc, #0f1115ee)`,
      }}
    >
      <div className="selected-card-head">
        <div className="selected-glyph" style={{ color: style.border }}>
          {style.glyph}
        </div>
        <div className="selected-title">
          <div className="selected-name">{entity.name}</div>
          <div className="selected-meta">
            <span className="kind-pill" style={{ borderColor: style.border, color: style.text }}>
              {entity.kind}
            </span>
            {engine && (
              <span className="engine-pill" style={{ color: style.border }}>
                {engine}
              </span>
            )}
            <span className="family-pill">{FAMILY_LABEL[style.family]}</span>
          </div>
        </div>
      </div>

      <div className="selected-id">
        <code>{entity.id}</code>
      </div>

      {metadataEntries.length > 0 && (
        <dl className="selected-md">
          {metadataEntries.map(([k, v]) => (
            <div key={k} className="selected-md-row">
              <dt>{k}</dt>
              <dd>{String(v)}</dd>
            </div>
          ))}
        </dl>
      )}

      {entity.labels && entity.labels.length > 0 && (
        <div className="selected-labels">
          {entity.labels.map((label) => (
            <span key={label} className="selected-label">
              {label}
            </span>
          ))}
        </div>
      )}

      {neighbours.length > 0 && (
        <div className="selected-neighbours">
          <div className="muted selected-section-title">
            {neighbours.length === 8 ? "First 8 connections" : "Connections"}
          </div>
          <ul>
            {neighbours.map(({ rel, other }) => {
              const out = rel.source === entity.id;
              const otherStyle = styleFor(other.kind, readEngine(other));
              return (
                <li key={rel.id}>
                  <span
                    className="selected-edge-dot"
                    style={{ background: edgeColor(rel.type, rel.protocol) }}
                  />
                  <span className="selected-rel-type">
                    {out ? "→" : "←"} {rel.type}
                  </span>
                  <button
                    type="button"
                    className="selected-other"
                    onClick={() => setSelected(other.id)}
                    title={`Select ${other.name}`}
                  >
                    <span className="selected-other-glyph">{otherStyle.glyph}</span>
                    {other.name}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="selected-actions">
        <button
          type="button"
          className="primary"
          onClick={() => setFocus(entity.id)}
          title="Open this entity's relationships in the main graph (same as double-click)"
        >
          Focus on {entity.name}
        </button>
        <button
          type="button"
          className="ghost"
          onClick={() => setSelected(null)}
          title="Dismiss the selection"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

function readEngine(entity: Entity): string | undefined {
  const md = entity.metadata as Record<string, unknown> | undefined;
  if (!md) return undefined;
  const engine = md.engine ?? md.technology ?? md.driver;
  return typeof engine === "string" && engine.trim() ? engine : undefined;
}
