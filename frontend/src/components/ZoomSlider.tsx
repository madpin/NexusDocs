import { useViewStore } from "../store/view";

const BANDS: { max: number; label: string; description: string }[] = [
  { max: 19, label: "Galaxy", description: "Top-level systems and orgs" },
  { max: 39, label: "Country", description: "Teams and major systems" },
  { max: 59, label: "City", description: "Services and components" },
  { max: 79, label: "Street", description: "Endpoints and classes" },
  { max: 100, label: "Door", description: "Functions and lines" },
];

function bandFor(zoom: number) {
  return BANDS.find((b) => zoom <= b.max) ?? BANDS[BANDS.length - 1];
}

export function ZoomSlider() {
  const zoom = useViewStore((s) => s.zoom);
  const setZoom = useViewStore((s) => s.setZoom);
  const band = bandFor(zoom);

  return (
    <div className="zoom-slider">
      <div className="row">
        <input
          type="range"
          min={0}
          max={100}
          value={zoom}
          onChange={(e) => setZoom(Number(e.target.value))}
          aria-label="Zoom level"
        />
        <span className="value">{zoom}</span>
      </div>
      <div className="band-label">
        {band.label}
        <span className="muted" style={{ textTransform: "none", marginLeft: 6, letterSpacing: 0 }}>
          · {band.description}
        </span>
      </div>
      <div className="ticks">
        {BANDS.map((b) => (
          <span key={b.label}>{b.label}</span>
        ))}
      </div>
    </div>
  );
}
