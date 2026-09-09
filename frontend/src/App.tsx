import { useEffect, useState } from "react";
import AuthGate from "./components/AuthGate";
import ModelSelector from "./components/ModelSelector";
import FeaturesAndReference from "./components/FeaturesAndReference";
import DriftDashboard from "./components/DriftDashboard";
import { api, Feature, getApiKey, setApiKey } from "./api/client";
import "./app.css";

export default function App() {
  const [authenticated, setAuthenticated] = useState<boolean>(!!getApiKey());
  const [modelId, setModelId] = useState<string | null>(null);
  const [versionId, setVersionId] = useState<string | null>(null);
  const [features, setFeatures] = useState<Feature[]>([]);

  useEffect(() => {
    if (versionId) {
      api.listFeatures(versionId).then(setFeatures).catch(() => setFeatures([]));
    } else {
      setFeatures([]);
    }
  }, [versionId]);

  function handleLogout() {
    setApiKey(null);
    setAuthenticated(false);
    setModelId(null);
    setVersionId(null);
  }

  if (!authenticated) {
    return (
      <div className="app-shell">
        <AuthGate onAuthenticated={() => setAuthenticated(true)} />
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>ModelWatch</h1>
        <button className="link-button" onClick={handleLogout}>
          Log out
        </button>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <ModelSelector
            selectedModelId={modelId}
            selectedVersionId={versionId}
            onSelectModel={setModelId}
            onSelectVersion={setVersionId}
          />
        </aside>

        <main className="main-content">
          {versionId ? (
            <>
              <FeaturesAndReference versionId={versionId} />
              <DriftDashboard versionId={versionId} features={features} />
            </>
          ) : (
            <div className="card">
              <p className="muted">Select or create a model and version to get started.</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
