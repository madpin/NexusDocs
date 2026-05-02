import { create } from "zustand";
import type { RenderedView } from "../api/client";

interface ViewState {
  focus: string;
  // The "selected" entity is what the user has tapped to inspect — it
  // populates the right-side details card without changing the graph
  // viewport. Clearing it (or setting it to focus) hides the details card.
  selected: string | null;
  zoom: number;
  lenses: string[];
  radius: number;
  navigationPath: string[];
  view: RenderedView | null;
  loading: boolean;
  error: string | null;

  setFocus: (id: string) => void;
  setSelected: (id: string | null) => void;
  setZoom: (z: number) => void;
  toggleLens: (lens: string) => void;
  setRadius: (r: number) => void;
  pushNav: (id: string) => void;
  setView: (v: RenderedView | null) => void;
  setLoading: (b: boolean) => void;
  setError: (e: string | null) => void;
}

const ALL_LENSES = ["product", "technical", "operations", "debug", "client", "onboarding"];

export const useViewStore = create<ViewState>((set, get) => ({
  focus: "company.acme",
  selected: null,
  zoom: 25,
  lenses: ["technical"],
  radius: 2,
  navigationPath: [],
  view: null,
  loading: false,
  error: null,

  setFocus: (id) => {
    const { navigationPath } = get();
    const next = [id, ...navigationPath.filter((x) => x !== id)].slice(0, 6);
    set({ focus: id, navigationPath: next, selected: null });
  },
  setSelected: (id) => set({ selected: id }),
  setZoom: (z) => set({ zoom: Math.max(0, Math.min(100, z)) }),
  toggleLens: (lens) => {
    const { lenses } = get();
    if (lenses.includes(lens)) {
      if (lenses.length === 1) return;
      set({ lenses: lenses.filter((l) => l !== lens) });
    } else {
      set({ lenses: [...lenses, lens] });
    }
  },
  setRadius: (r) => set({ radius: Math.max(0, r) }),
  pushNav: (id) => {
    const { navigationPath } = get();
    const filtered = navigationPath.filter((x) => x !== id);
    set({ navigationPath: [id, ...filtered].slice(0, 6) });
  },
  setView: (v) => set({ view: v }),
  setLoading: (b) => set({ loading: b }),
  setError: (e) => set({ error: e }),
}));

export const ALL_LENSES_LIST = ALL_LENSES;
