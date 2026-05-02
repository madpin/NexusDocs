import { NavRail } from "./components/NavRail";
import { AboutPage } from "./pages/AboutPage";
import { HelpPage } from "./pages/HelpPage";
import { IngestPage } from "./pages/IngestPage";
import { SearchPage } from "./pages/SearchPage";
import { SettingsPage } from "./pages/SettingsPage";
import { ViewPage } from "./pages/ViewPage";
import { RouterProvider, useRoute } from "./router";

export function App() {
  return (
    <RouterProvider>
      <div className="app-shell">
        <NavRail />
        <RouteContent />
      </div>
    </RouterProvider>
  );
}

function RouteContent() {
  const { route } = useRoute();
  switch (route) {
    case "view":
      return <ViewPage />;
    case "ingest":
      return <IngestPage />;
    case "search":
      return <SearchPage />;
    case "settings":
      return <SettingsPage />;
    case "help":
      return <HelpPage />;
    case "about":
      return <AboutPage />;
    default:
      return <ViewPage />;
  }
}
