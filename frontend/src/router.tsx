/**
 * Tiny hash-router. We avoid pulling in react-router since the app only
 * needs a handful of named routes — a hash + reactive state via a
 * subscription does the job in <50 lines.
 */
import { createContext, useContext, useEffect, useState } from "react";

export type RouteId = "view" | "ingest" | "search" | "settings" | "help" | "about";

const VALID: RouteId[] = ["view", "ingest", "search", "settings", "help", "about"];

function parseHash(): RouteId {
  const raw = window.location.hash.replace(/^#\/?/, "").split("?")[0];
  return (VALID as string[]).includes(raw) ? (raw as RouteId) : "view";
}

interface RouterCtx {
  route: RouteId;
  navigate: (route: RouteId) => void;
}

const Ctx = createContext<RouterCtx>({
  route: "view",
  navigate: () => undefined,
});

export function RouterProvider({ children }: { children: React.ReactNode }) {
  const [route, setRoute] = useState<RouteId>(parseHash());

  useEffect(() => {
    const onChange = () => setRoute(parseHash());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const navigate = (r: RouteId) => {
    if (r === route) return;
    window.location.hash = `#/${r}`;
  };

  return <Ctx.Provider value={{ route, navigate }}>{children}</Ctx.Provider>;
}

export function useRoute(): RouterCtx {
  return useContext(Ctx);
}
