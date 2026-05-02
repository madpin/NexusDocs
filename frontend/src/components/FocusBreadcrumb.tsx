import { useViewStore } from "../store/view";

export function FocusBreadcrumb() {
  const focus = useViewStore((s) => s.focus);
  const path = useViewStore((s) => s.navigationPath);
  const setFocus = useViewStore((s) => s.setFocus);

  const trail = [focus, ...path.filter((p) => p !== focus)].slice(0, 6);

  return (
    <nav className="breadcrumb" aria-label="Focus history">
      <span className="breadcrumb-label">Focus</span>
      {trail.map((id, idx) => (
        <span key={id + idx} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
          <button
            type="button"
            className={`breadcrumb-chip ${idx === 0 ? "current" : ""}`}
            onClick={() => setFocus(id)}
            title={idx === 0 ? "Current focus" : "Jump back here"}
          >
            {id}
          </button>
          {idx < trail.length - 1 && <span className="breadcrumb-arrow">‹</span>}
        </span>
      ))}
    </nav>
  );
}
