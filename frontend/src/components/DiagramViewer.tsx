import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  fontFamily: "ui-sans-serif, system-ui, sans-serif",
});

interface Props {
  source: string;
}

export function DiagramViewer({ source }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const id = `mermaid-${Math.random().toString(36).slice(2)}`;
    setError(null);
    if (!source.trim()) {
      if (ref.current) ref.current.innerHTML = "";
      return;
    }
    mermaid
      .render(id, source)
      .then(({ svg }) => {
        if (!cancelled && ref.current) {
          ref.current.innerHTML = svg;
        }
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [source]);

  if (error) {
    return (
      <div className="error">
        Failed to render diagram. <pre>{error}</pre>
      </div>
    );
  }
  return <div ref={ref} className="diagram" />;
}
