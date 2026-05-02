import { useEffect, useMemo, useState } from "react";
import { renderView } from "../api/client";
import { DiagramViewer } from "../components/DiagramViewer";
import { FocusBreadcrumb } from "../components/FocusBreadcrumb";
import { FragmentCard } from "../components/FragmentCard";
import { GraphCanvas } from "../components/GraphCanvas";
import { Legend } from "../components/Legend";
import { LensPicker } from "../components/LensPicker";
import { SelectedDetailsCard } from "../components/SelectedDetailsCard";
import { ViewSummary } from "../components/ViewSummary";
import { ZoomSlider } from "../components/ZoomSlider";
import { styleFor, type EntityFamily } from "../styles/palette";
import { useViewStore } from "../store/view";

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(handle);
  }, [value, ms]);
  return debounced;
}

const IS_MAC =
  typeof navigator !== "undefined" &&
  /Mac|iPhone|iPad|iPod/i.test(navigator.platform);
const CAMERA_MODIFIER_LABEL = IS_MAC ? "⌘" : "Ctrl";

export function ViewPage() {
  const focus = useViewStore((s) => s.focus);
  const zoom = useViewStore((s) => s.zoom);
  const lenses = useViewStore((s) => s.lenses);
  const radius = useViewStore((s) => s.radius);
  const navigationPath = useViewStore((s) => s.navigationPath);
  const view = useViewStore((s) => s.view);
  const loading = useViewStore((s) => s.loading);
  const error = useViewStore((s) => s.error);
  const setFocus = useViewStore((s) => s.setFocus);
  const setView = useViewStore((s) => s.setView);
  const setLoading = useViewStore((s) => s.setLoading);
  const setError = useViewStore((s) => s.setError);
  const setRadius = useViewStore((s) => s.setRadius);

  const debouncedZoom = useDebounced(zoom, 300);

  const lensesKey = useMemo(() => lenses.join(","), [lenses]);
  const navKey = useMemo(() => navigationPath.join(","), [navigationPath]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    renderView({
      focus,
      zoom: debouncedZoom,
      lenses,
      radius,
      navigation_path: navigationPath,
    })
      .then((v) => {
        if (!cancelled) setView(v);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus, debouncedZoom, lensesKey, radius, navKey]);

  const familiesInView = useMemo(() => {
    const set = new Set<EntityFamily>();
    if (view) for (const e of view.entities) set.add(styleFor(e.kind).family);
    return set;
  }, [view]);

  const stats = useMemo(() => {
    if (!view) return { entities: 0, relationships: 0, fragments: 0 };
    return {
      entities: view.entities.length,
      relationships: view.relationships.length,
      fragments: view.fragments.length,
    };
  }, [view]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>
          <span className="dot" />
          NexusDocs
          <span className="tagline">— continuous-zoom architecture docs</span>
        </h1>
        <div className="spacer" />
        <FocusBreadcrumb />
        <div className="spacer" />
        {loading ? (
          <span className="header-status">
            <span className="pulse" />
            rendering view…
          </span>
        ) : (
          <span className="header-status">
            {stats.entities} entities · {stats.relationships} edges · {stats.fragments} docs
          </span>
        )}
      </header>

      <aside className="sidebar">
        <h3>
          Zoom
          <span className="hint">drag, or scroll on the graph</span>
        </h3>
        <ZoomSlider />

        <h3>
          Lenses
          <span className="hint">filter perspective</span>
        </h3>
        <LensPicker />

        <h3>
          Radius
          <span className="hint">graph hops from focus</span>
        </h3>
        <div className="section-card">
          <div className="kv-row">
            <span className="k">Hops</span>
            <input
              type="number"
              min={0}
              max={6}
              value={radius}
              onChange={(e) => setRadius(Number(e.target.value))}
              style={{ width: 70 }}
            />
          </div>
        </div>

        <h3>Legend</h3>
        <div className="section-card">
          <Legend highlight={familiesInView} />
        </div>

        <h3>Topology</h3>
        <div className="section-card">
          {view?.topology_highlights.most_central ? (
            <div className="topology-row">
              <span className="lhs">Most central</span>
              <code onClick={() => setFocus(view.topology_highlights.most_central!)}>
                {view.topology_highlights.most_central}
              </code>
            </div>
          ) : (
            <div className="muted">No data yet</div>
          )}
          {view && view.topology_highlights.structural_concerns.length > 0 && (
            <>
              <div className="muted" style={{ fontSize: 11, marginTop: 8 }}>
                Structural concerns
              </div>
              {view.topology_highlights.structural_concerns.map((c) => (
                <div key={c} className="topology-row">
                  <span className="lhs">⚠</span>
                  <code onClick={() => setFocus(c)}>{c}</code>
                </div>
              ))}
            </>
          )}
        </div>

        {view?.follow_up_suggestions.length ? (
          <>
            <h3>Suggestions</h3>
            <div>
              {view.follow_up_suggestions.map((s) => (
                <div key={s} className="suggestion">
                  {s}
                </div>
              ))}
            </div>
          </>
        ) : null}
      </aside>

      <main className="canvas-pane">
        {view && view.entities.length > 0 ? (
          <GraphCanvas entities={view.entities} relationships={view.relationships} />
        ) : (
          <div className="canvas-empty">
            {loading ? "Loading graph…" : "No entities at this zoom level."}
          </div>
        )}
        <div className="canvas-overlay">
          <span className="zoom-pill">
            <strong>z={zoom}</strong>
            click to inspect · double-click to focus · scroll to drill in/out
            · {CAMERA_MODIFIER_LABEL}+scroll to camera-zoom
          </span>
        </div>
      </main>

      <section className="summary-pane">
        {error && <div className="error">{error}</div>}
        {view && <SelectedDetailsCard view={view} />}
        {view && (
          <>
            <ViewSummary markdown={view.summary} />
            <div className="section-title">
              <h3>Diagram</h3>
              <span className="meta">mermaid render of viewport</span>
            </div>
            <DiagramViewer source={view.diagram} />
            <div className="section-title">
              <h3>Fragments</h3>
              <span className="meta">{view.fragments.length} matched</span>
            </div>
            {view.fragments.map((f) => (
              <FragmentCard key={f.id} fragment={f} />
            ))}
            {view.fragments.length === 0 && (
              <div className="muted" style={{ fontSize: 12 }}>
                No documentation fragments matched the current zoom and lens
                combination. Try zooming out or enabling another lens.
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
