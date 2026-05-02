import { ALL_LENSES_LIST, useViewStore } from "../store/view";

export function LensPicker() {
  const lenses = useViewStore((s) => s.lenses);
  const toggle = useViewStore((s) => s.toggleLens);

  return (
    <div className="chip-group" role="group" aria-label="Lenses">
      {ALL_LENSES_LIST.map((lens) => {
        const active = lenses.includes(lens);
        return (
          <button
            key={lens}
            type="button"
            className={`lens-chip ${active ? "active" : ""}`}
            data-lens={lens}
            aria-pressed={active}
            onClick={() => toggle(lens)}
          >
            {lens}
          </button>
        );
      })}
    </div>
  );
}
