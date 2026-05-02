import type { RouteId } from "../router";
import { useRoute } from "../router";

interface Item {
  id: RouteId;
  label: string;
  glyph: string;
  hint: string;
}

const TOP_ITEMS: Item[] = [
  { id: "view", label: "View", glyph: "◎", hint: "Continuous-zoom graph" },
  {
    id: "ingest",
    label: "Ingest",
    glyph: "⤴",
    hint: "Add docs from markdown / git / Confluence / Jira",
  },
  { id: "search", label: "Search", glyph: "⌕", hint: "Find any entity, edge, or fragment" },
];

const BOTTOM_ITEMS: Item[] = [
  { id: "settings", label: "Settings", glyph: "⚙", hint: "LLM + repository config" },
  { id: "help", label: "Help", glyph: "?", hint: "Concepts cheat-sheet" },
  { id: "about", label: "About", glyph: "ⓘ", hint: "Version + repo links" },
];

export function NavRail() {
  const { route, navigate } = useRoute();
  return (
    <nav className="nav-rail" aria-label="Primary navigation">
      <div className="nav-rail-logo" title="NexusDocs">
        <span className="nav-rail-dot" />
        <span className="nav-rail-mark">N</span>
      </div>

      <div className="nav-rail-group">
        {TOP_ITEMS.map((item) => (
          <NavButton key={item.id} item={item} active={item.id === route} onClick={navigate} />
        ))}
      </div>

      <div className="nav-rail-group" style={{ marginTop: "auto" }}>
        {BOTTOM_ITEMS.map((item) => (
          <NavButton key={item.id} item={item} active={item.id === route} onClick={navigate} />
        ))}
      </div>
    </nav>
  );
}

function NavButton({
  item,
  active,
  onClick,
}: {
  item: Item;
  active: boolean;
  onClick: (id: RouteId) => void;
}) {
  return (
    <button
      type="button"
      className={`nav-rail-button ${active ? "active" : ""}`}
      aria-pressed={active}
      title={`${item.label} — ${item.hint}`}
      onClick={() => onClick(item.id)}
    >
      <span className="nav-rail-glyph" aria-hidden="true">
        {item.glyph}
      </span>
      <span className="nav-rail-label">{item.label}</span>
    </button>
  );
}
