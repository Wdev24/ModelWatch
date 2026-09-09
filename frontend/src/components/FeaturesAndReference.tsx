import { useEffect, useState } from "react";
import { api, Feature, ReferenceSnapshot } from "../api/client";

export default function FeaturesAndReference({ versionId }: { versionId: string }) {
  const [features, setFeatures] = useState<Feature[]>([]);
  const [snapshots, setSnapshots] = useState<ReferenceSnapshot[]>([]);
  const [newFeatureName, setNewFeatureName] = useState("");
  const [newFeatureType, setNewFeatureType] = useState<"numeric" | "categorical">("numeric");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [f, s] = await Promise.all([api.listFeatures(versionId), api.listSnapshots(versionId)]);
      setFeatures(f);
      setSnapshots(s);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    }
  }

  useEffect(() => {
    load();
  }, [versionId]);

  async function handleAddFeature(e: React.FormEvent) {
    e.preventDefault();
    if (!newFeatureName.trim()) return;
    await api.createFeature(versionId, newFeatureName.trim(), newFeatureType);
    setNewFeatureName("");
    await load();
  }

  return (
    <div className="card">
      <h3>Features</h3>
      <ul className="plain-list">
        {features.map((f) => (
          <li key={f.id}>
            <strong>{f.name}</strong> <span className="tag">{f.data_type}</span>
          </li>
        ))}
        {features.length === 0 && <li className="muted">No features defined yet.</li>}
      </ul>
      <form onSubmit={handleAddFeature} className="inline-form">
        <input placeholder="Feature name" value={newFeatureName} onChange={(e) => setNewFeatureName(e.target.value)} />
        <select value={newFeatureType} onChange={(e) => setNewFeatureType(e.target.value as "numeric" | "categorical")}>
          <option value="numeric">numeric</option>
          <option value="categorical">categorical</option>
        </select>
        <button type="submit">+ Feature</button>
      </form>

      <h3>Reference Snapshots</h3>
      <ul className="plain-list">
        {snapshots.map((s) => (
          <li key={s.id}>
            <strong>{s.label}</strong> - {new Date(s.created_at).toLocaleString()} ({s.stats.length} feature
            {s.stats.length === 1 ? "" : "s"} covered)
          </li>
        ))}
        {snapshots.length === 0 && (
          <li className="muted">
            No reference baseline yet. Upload one via <code>POST /versions/{"{id}"}/reference-snapshots</code>.
          </li>
        )}
      </ul>

      {error && <p className="error">{error}</p>}
    </div>
  );
}
