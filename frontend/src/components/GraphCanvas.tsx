import { useEffect, useMemo, useRef } from "react";
import cytoscape from "cytoscape";
import type { Entity, Relationship } from "../api/client";
import {
  edgeColor,
  edgeDash,
  styleFor,
} from "../styles/palette";
import { useViewStore } from "../store/view";

interface Props {
  entities: Entity[];
  relationships: Relationship[];
}

// Single-click / double-click detection threshold. Cytoscape fires `tap`
// twice on a double-click; we wait this long for a follow-up before
// treating the first tap as a real single-click "select" event.
const DBL_TAP_WINDOW_MS = 250;

function readEngine(entity: Entity): string | undefined {
  const md = entity.metadata as Record<string, unknown> | undefined;
  if (!md) return undefined;
  const engine = md.engine ?? md.technology ?? md.driver;
  return typeof engine === "string" && engine.trim() ? engine : undefined;
}

/**
 * The graph canvas is intentionally *quiet* — once cytoscape is mounted it:
 *
 *   * runs the cose layout exactly once for each truly new viewport,
 *   * for incremental data updates (different fragments / labels at the
 *     same zoom band) it just diffs, plops new nodes near a connected
 *     existing node, and lets cytoscape glide them into place,
 *   * never auto-fits — that was the source of the post-animation jump,
 *   * never re-centres the camera on a focus that is already on screen,
 *     so user pan / zoom is preserved as long as they're looking at the
 *     focused node,
 *   * toggles label visibility via CSS classes instead of rebuilding the
 *     stylesheet, which used to cause the flicker between zoom steps.
 */

const BASE_LAYOUT = {
  name: "cose",
  animate: true,
  animationDuration: 600,
  animationEasing: "ease-out-cubic",
  randomize: false,
  fit: false, // never auto-fit; we handle the initial fit explicitly
  padding: 60,
  nodeRepulsion: 12000,
  idealEdgeLength: 140,
  edgeElasticity: 90,
  nodeOverlap: 24,
  gravity: 0.12,
  numIter: 1200,
} as const;

const INITIAL_LAYOUT = {
  ...BASE_LAYOUT,
  numIter: 2200,
} as unknown as cytoscape.LayoutOptions;

// Focus changes get the "end-only" animation: cose runs the simulation
// invisibly and then glides every node from its current position to the
// new one in a single smooth transition. That way the user sees the
// previous layout *reorganise* around the new focus rather than the new
// nodes piling on top of the old ones.
const FOCUS_CHANGE_LAYOUT = {
  ...BASE_LAYOUT,
  animate: "end",
  animationDuration: 700,
  numIter: 1500,
} as unknown as cytoscape.LayoutOptions;

const INCREMENTAL_LAYOUT = {
  ...BASE_LAYOUT,
  numIter: 800,
} as unknown as cytoscape.LayoutOptions;

interface ElementBundle {
  elements: cytoscape.ElementDefinition[];
  byId: Map<string, cytoscape.ElementDefinition>;
  edgesBySource: Map<string, cytoscape.ElementDefinition[]>;
  edgesByTarget: Map<string, cytoscape.ElementDefinition[]>;
}

function buildElements(
  entities: Entity[],
  relationships: Relationship[]
): ElementBundle {
  const elements: cytoscape.ElementDefinition[] = [];
  const byId = new Map<string, cytoscape.ElementDefinition>();
  const edgesBySource = new Map<string, cytoscape.ElementDefinition[]>();
  const edgesByTarget = new Map<string, cytoscape.ElementDefinition[]>();

  for (const e of entities) {
    const engine = readEngine(e);
    const s = styleFor(e.kind, engine);
    const subtitle = engine ? `${e.kind} · ${engine}` : e.kind;
    const el: cytoscape.ElementDefinition = {
      group: "nodes",
      data: {
        id: e.id,
        label: `${s.glyph}  ${e.name}`,
        labelKind: `${s.glyph}  ${e.name}\n${subtitle}`,
        kind: e.kind,
        engine: engine ?? "",
        family: s.family,
        fill: s.fill,
        border: s.border,
        text: s.text,
      },
    };
    elements.push(el);
    byId.set(e.id, el);
  }

  const nodeIds = new Set(entities.map((e) => e.id));
  for (const r of relationships) {
    if (!nodeIds.has(r.source) || !nodeIds.has(r.target)) continue;
    const el: cytoscape.ElementDefinition = {
      group: "edges",
      data: {
        id: r.id,
        source: r.source,
        target: r.target,
        label: r.protocol ? `${r.type} · ${r.protocol}` : r.type,
        type: r.type,
        protocol: r.protocol ?? "",
        mode: r.mode ?? "",
        color: edgeColor(r.type, r.protocol),
        dash: edgeDash(r.mode),
      },
    };
    elements.push(el);
    byId.set(r.id, el);
    if (!edgesBySource.has(r.source)) edgesBySource.set(r.source, []);
    edgesBySource.get(r.source)!.push(el);
    if (!edgesByTarget.has(r.target)) edgesByTarget.set(r.target, []);
    edgesByTarget.get(r.target)!.push(el);
  }

  return { elements, byId, edgesBySource, edgesByTarget };
}

function applyZoomBands(cy: cytoscape.Core, zoom: number) {
  const showKindOnNodes = zoom >= 35;
  const showEdgeLabels = zoom >= 40;
  cy.batch(() => {
    cy.nodes().forEach((n) => {
      const has = n.hasClass("show-kind");
      if (showKindOnNodes !== has) n.toggleClass("show-kind", showKindOnNodes);
    });
    cy.edges().forEach((e) => {
      const has = e.hasClass("show-label");
      if (showEdgeLabels !== has) e.toggleClass("show-label", showEdgeLabels);
    });
  });
}

function applyFocusEmphasis(
  cy: cytoscape.Core,
  focus: string,
  selected: string | null
) {
  cy.batch(() => {
    cy.elements().removeClass("focus neighbor dim selected");
    const focusEle = cy.getElementById(focus);
    if (focusEle.empty()) return;
    focusEle.addClass("focus");
    const neighborhood = focusEle.closedNeighborhood();
    neighborhood.not(focusEle).addClass("neighbor");
    cy.elements().not(neighborhood).addClass("dim");
    if (selected && selected !== focus) {
      const sel = cy.getElementById(selected);
      if (sel.nonempty()) {
        sel.addClass("selected");
        sel.removeClass("dim");
      }
    }
  });
}

function isPointInViewport(cy: cytoscape.Core, ele: cytoscape.NodeSingular) {
  const pos = ele.renderedPosition();
  const w = cy.width();
  const h = cy.height();
  const margin = 60;
  return (
    pos.x >= margin &&
    pos.x <= w - margin &&
    pos.y >= margin &&
    pos.y <= h - margin
  );
}

function panToNode(cy: cytoscape.Core, id: string) {
  const ele = cy.getElementById(id);
  if (ele.empty()) return;
  // Already comfortably visible — leave the camera where the user put it.
  if (isPointInViewport(cy, ele)) return;
  cy.stop(true, true);
  cy.animate(
    {
      center: { eles: ele },
      zoom: Math.max(cy.zoom(), 0.85),
    },
    { duration: 550, easing: "ease-in-out-cubic" }
  );
}

function spawnPositionFor(
  cy: cytoscape.Core,
  id: string,
  bundle: ElementBundle,
  fallback: { x: number; y: number }
): { x: number; y: number } {
  const candidates: string[] = [];
  for (const e of bundle.edgesBySource.get(id) ?? []) {
    const target = e.data.target as string;
    if (cy.getElementById(target).nonempty()) candidates.push(target);
  }
  for (const e of bundle.edgesByTarget.get(id) ?? []) {
    const source = e.data.source as string;
    if (cy.getElementById(source).nonempty()) candidates.push(source);
  }
  if (candidates.length === 0) {
    return {
      x: fallback.x + (Math.random() - 0.5) * 240,
      y: fallback.y + (Math.random() - 0.5) * 240,
    };
  }
  const anchor = cy.getElementById(candidates[0]).position();
  return {
    x: anchor.x + (Math.random() - 0.5) * 120,
    y: anchor.y + (Math.random() - 0.5) * 120,
  };
}

export function GraphCanvas({ entities, relationships }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const initialFitDoneRef = useRef(false);
  const lastStructureKeyRef = useRef<string>("");
  const lastSyncedFocusRef = useRef<string>("");
  const pendingTapRef = useRef<{ id: string; timer: number } | null>(null);
  // Wheel deltas accumulate here between dispatches so that small trackpad
  // events sum into whole-unit semantic zoom steps without jitter.
  const semanticZoomAccumRef = useRef(0);
  const focus = useViewStore((s) => s.focus);
  const selected = useViewStore((s) => s.selected);
  const zoom = useViewStore((s) => s.zoom);
  const setFocus = useViewStore((s) => s.setFocus);
  const setSelected = useViewStore((s) => s.setSelected);

  const bundle = useMemo(
    () => buildElements(entities, relationships),
    [entities, relationships]
  );
  const structureKey = useMemo(
    () =>
      `${bundle.elements
        .map((el) => el.data.id)
        .sort()
        .join("|")}@${zoom >= 35 ? "k" : "n"}-${zoom >= 40 ? "e" : "n"}`,
    [bundle, zoom]
  );

  // Mount cytoscape once.
  useEffect(() => {
    if (!ref.current || cyRef.current) return;
    cyRef.current = cytoscape({
      container: ref.current,
      elements: [],
      wheelSensitivity: 0.5,
      minZoom: 0.15,
      maxZoom: 2.8,
      // Pan stays on; zoom is intercepted by our own wheel handler below so
      // that a plain scroll changes the *semantic* zoom (depth of entities
      // surfaced) and only Cmd/Ctrl + scroll falls through to camera zoom.
      userPanningEnabled: true,
      userZoomingEnabled: false,
      boxSelectionEnabled: false,
      autounselectify: true,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "background-color": "data(fill)",
            "border-color": "data(border)",
            "border-width": 1.5,
            color: "data(text)",
            "font-size": "11px",
            "font-weight": 500,
            "text-wrap": "wrap",
            "text-max-width": "150px",
            "text-valign": "center",
            "text-halign": "center",
            width: 110,
            height: 46,
            shape: "round-rectangle",
            "transition-property":
              "background-color border-color border-width opacity width height",
            "transition-duration": 350,
            "transition-timing-function": "ease-out",
          },
        },
        {
          selector: "node.show-kind",
          style: { label: "data(labelKind)", height: 56 },
        },
        {
          selector: "node.focus",
          style: {
            "border-width": 4,
            "border-color": "#ffffff",
            "background-color": "data(border)",
            color: "#0c1019",
            width: 130,
            height: 60,
            "z-index": 99,
            "shadow-blur": 22,
            "shadow-color": "data(border)",
            "shadow-opacity": 0.85,
          } as cytoscape.Css.Node,
        },
        {
          selector: "node.neighbor",
          style: { "border-width": 2.5, opacity: 1 },
        },
        {
          selector: "node.dim",
          style: { opacity: 0.32 },
        },
        {
          // Single-click "selected" is a softer state than focus — it
          // brings the node forward and adds a glowing dashed ring so the
          // user can see *what they tapped* without losing the focus.
          selector: "node.selected",
          style: {
            "border-width": 4,
            "border-style": "dashed",
            "border-color": "#ffd470",
            "shadow-blur": 18,
            "shadow-color": "#ffd470",
            "shadow-opacity": 0.7,
            opacity: 1,
            "z-index": 80,
          } as cytoscape.Css.Node,
        },
        {
          selector: "edge",
          style: {
            label: "data(label)",
            "line-color": "data(color)",
            "target-arrow-color": "data(color)",
            "target-arrow-shape": "triangle",
            "arrow-scale": 1.1,
            "curve-style": "bezier",
            "control-point-step-size": 30,
            "line-style": "data(dash)",
            "font-size": "10px",
            color: "#cfd5e2",
            width: 1.5,
            "text-background-color": "#0f1115",
            "text-background-opacity": 0.85,
            "text-background-padding": "3px",
            "text-background-shape": "roundrectangle",
            opacity: 0.75,
            "text-opacity": 0,
            "transition-property": "line-color width opacity",
            "transition-duration": 250,
            "transition-timing-function": "ease-out",
          } as unknown as cytoscape.Css.Edge,
        },
        {
          selector: "edge.show-label",
          style: { "text-opacity": 1 },
        },
        {
          selector: "edge.neighbor",
          style: { width: 3, opacity: 1 },
        },
        {
          selector: "edge.dim",
          style: { opacity: 0.18, "text-opacity": 0 },
        },
      ],
    });

    cyRef.current.on("tap", "node", (evt) => {
      const id = evt.target.data("id") as string | undefined;
      if (!id) return;
      // First tap: schedule a "select" action. If a second tap arrives
      // within DBL_TAP_WINDOW_MS the dbltap handler cancels this and
      // promotes the action to "focus" (open relationships) instead.
      if (pendingTapRef.current) {
        window.clearTimeout(pendingTapRef.current.timer);
        pendingTapRef.current = null;
      }
      const timer = window.setTimeout(() => {
        pendingTapRef.current = null;
        setSelected(id);
      }, DBL_TAP_WINDOW_MS);
      pendingTapRef.current = { id, timer };
    });

    cyRef.current.on("dbltap", "node", (evt) => {
      const id = evt.target.data("id") as string | undefined;
      if (!id) return;
      if (pendingTapRef.current) {
        window.clearTimeout(pendingTapRef.current.timer);
        pendingTapRef.current = null;
      }
      // Do NOT pan here — the data-sync effect will re-layout the entire
      // graph around the new focus and pan/center on `layoutstop`.
      // Panning to the old position now would just snap the camera to
      // where the node USED to be before everything reflows.
      setFocus(id);
    });

    cyRef.current.on("tap", (evt) => {
      // Tap on empty canvas — clear the selection so the details card hides.
      if (evt.target === cyRef.current) setSelected(null);
    });

    // Custom wheel handler: plain scroll/pinch drives the semantic zoom
    // axis (which entities are surfaced); Cmd (mac) / Ctrl (win+linux) +
    // scroll falls through to a classic zoom-around-cursor camera move.
    //
    // We deliberately use Cmd on mac (not Ctrl) because the macOS trackpad
    // pinch gesture synthesizes wheel events with `ctrlKey: true` — using
    // Ctrl as the modifier would conflict with that.
    const container = ref.current;
    const isMac =
      typeof navigator !== "undefined" &&
      /Mac|iPhone|iPad|iPod/i.test(navigator.platform);
    const onWheel = (e: WheelEvent) => {
      const cy = cyRef.current;
      if (!cy) return;
      e.preventDefault();
      const cameraModifier = isMac ? e.metaKey : e.ctrlKey;
      if (cameraModifier) {
        // Camera zoom — exponential factor matches Cytoscape's native feel,
        // pivot point is the cursor so the view zooms toward where the
        // user is pointing.
        const factor = Math.exp(-e.deltaY * 0.002);
        const next = cy.zoom() * factor;
        const clamped = Math.max(0.15, Math.min(2.8, next));
        const rect = container.getBoundingClientRect();
        cy.zoom({
          level: clamped,
          renderedPosition: {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top,
          },
        });
        return;
      }
      // Semantic zoom — accumulate fractional deltas so trackpads (small,
      // frequent events) feel smooth and mouse wheels (one chunky notch)
      // still produce a single integer step.
      semanticZoomAccumRef.current += -e.deltaY * 0.04;
      const whole = Math.trunc(semanticZoomAccumRef.current);
      if (whole === 0) return;
      semanticZoomAccumRef.current -= whole;
      const store = useViewStore.getState();
      store.setZoom(store.zoom + whole);
    };
    container.addEventListener("wheel", onWheel, { passive: false });

    return () => {
      if (pendingTapRef.current) {
        window.clearTimeout(pendingTapRef.current.timer);
        pendingTapRef.current = null;
      }
      container.removeEventListener("wheel", onWheel);
      cyRef.current?.destroy();
      cyRef.current = null;
      initialFitDoneRef.current = false;
      lastStructureKeyRef.current = "";
      lastSyncedFocusRef.current = "";
      semanticZoomAccumRef.current = 0;
    };
  }, [setFocus, setSelected]);

  // Sync graph data: incremental add / remove, no surprise camera moves.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const newKey = structureKey;
    const prevKey = lastStructureKeyRef.current;
    const incomingIds = new Set<string>();
    bundle.elements.forEach((el) => {
      if (el.data.id) incomingIds.add(el.data.id as string);
    });

    const existingIds = new Set<string>();
    cy.elements().forEach((el) => {
      existingIds.add(el.id());
    });

    const toAdd: cytoscape.ElementDefinition[] = [];
    bundle.elements.forEach((el) => {
      if (!existingIds.has(el.data.id as string)) toAdd.push(el);
    });
    const toRemove = cy.elements().filter((el) => !incomingIds.has(el.id()));
    const structureChanged = newKey !== prevKey;

    // Update mutable data on entities that already exist (label changes,
    // colour changes, etc) without triggering a layout cycle.
    cy.batch(() => {
      cy.elements().forEach((el) => {
        const inc = bundle.byId.get(el.id());
        if (!inc) return;
        const next = inc.data;
        for (const key of Object.keys(next)) {
          if (key === "id" || key === "source" || key === "target") continue;
          const cur = el.data(key);
          if (cur !== next[key as keyof typeof next]) {
            el.data(key, next[key as keyof typeof next]);
          }
        }
      });

      if (toRemove.nonempty()) {
        toRemove.removeClass("focus neighbor");
        cy.remove(toRemove);
      }

      if (toAdd.length) {
        const focusEle = cy.getElementById(focus);
        const center = focusEle.empty()
          ? { x: cy.width() / 2, y: cy.height() / 2 }
          : focusEle.position();

        const positioned = toAdd.map((el) =>
          el.group === "nodes"
            ? {
                ...el,
                position: spawnPositionFor(cy, el.data.id as string, bundle, center),
              }
            : el
        );
        cy.add(positioned);
      }
    });

    const focusChanged = focus !== lastSyncedFocusRef.current;
    const dataChanged = toAdd.length > 0 || toRemove.nonempty();

    if (!initialFitDoneRef.current && cy.elements().nonempty()) {
      // INITIAL MOUNT — full layout, then fit-to-content.
      const layout = cy.layout(INITIAL_LAYOUT);
      layout.one("layoutstop", () => {
        cy.fit(undefined, 80);
        applyZoomBands(cy, zoom);
        applyFocusEmphasis(cy, focus, selected);
      });
      layout.run();
      initialFitDoneRef.current = true;
    } else if (focusChanged) {
      // FOCUS CHANGED — re-balance the entire neighbourhood around the new
      // focus. Locking existing nodes (the previous behaviour) made new
      // arrivals pile on top of stale positions that were arranged for the
      // *previous* focus, producing the visual mess the user reported.
      // A full cose pass with no locks lets cytoscape redistribute every
      // node based on the new edge set. We bring the camera to the new
      // focus *while* the layout reflows so the user always has the
      // focused node in view as the surrounding graph rearranges.
      if (dataChanged || structureChanged) {
        // Centre the camera on the focus's current position right before
        // the layout starts. cose's `animate:'end'` then glides every
        // node from its current position to the new equilibrium, with
        // the focus node staying near the centre throughout.
        const focusEle = cy.getElementById(focus);
        if (focusEle.nonempty()) {
          cy.stop(true, true);
          cy.animate(
            { center: { eles: focusEle }, zoom: Math.max(cy.zoom(), 0.85) },
            { duration: 250, easing: "ease-out-cubic" }
          );
        }
        const layout = cy.layout(FOCUS_CHANGE_LAYOUT);
        layout.one("layoutstop", () => {
          applyZoomBands(cy, zoom);
          applyFocusEmphasis(cy, focus, selected);
          panToNode(cy, focus);
        });
        layout.run();
      } else {
        // Same entity set, only the focus pointer moved — just pan.
        applyZoomBands(cy, zoom);
        applyFocusEmphasis(cy, focus, selected);
        panToNode(cy, focus);
      }
    } else if (toAdd.length > 0) {
      // ZOOM WIDENED — focus is unchanged, but the depth-aware filter let
      // more entities through. Lock the existing graph so user-perceived
      // structure is preserved and only the new nodes settle into place.
      const newIds = new Set(toAdd.map((el) => el.data.id as string));
      const existingNodes = cy.nodes().filter((n) => !newIds.has(n.id()));
      existingNodes.lock();
      const layout = cy.layout(INCREMENTAL_LAYOUT);
      layout.one("layoutstop", () => {
        existingNodes.unlock();
        applyZoomBands(cy, zoom);
        applyFocusEmphasis(cy, focus, selected);
      });
      layout.run();
    } else {
      applyZoomBands(cy, zoom);
      applyFocusEmphasis(cy, focus, selected);
    }

    lastSyncedFocusRef.current = focus;
    lastStructureKeyRef.current = newKey;
  }, [bundle, structureKey, focus, selected, zoom]);

  // Selection or focus pointer-only updates shouldn't run a new layout —
  // just re-apply the visual classes so the highlighted node lights up
  // immediately, even before the next data-sync pass arrives.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    applyFocusEmphasis(cy, focus, selected);
  }, [selected, focus]);

  return <div ref={ref} className="graph-canvas" />;
}
