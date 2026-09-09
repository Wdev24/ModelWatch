import { useEffect, useState } from "react";
import { api, Model, ModelVersion } from "../api/client";

interface Props {
  selectedModelId: string | null;
  selectedVersionId: string | null;
  onSelectModel: (id: string | null) => void;
  onSelectVersion: (id: string | null) => void;
}

export default function ModelSelector({ selectedModelId, selectedVersionId, onSelectModel, onSelectVersion }: Props) {
  const [models, setModels] = useState<Model[]>([]);
  const [versions, setVersions] = useState<ModelVersion[]>([]);
  const [newModelName, setNewModelName] = useState("");
  const [newVersionLabel, setNewVersionLabel] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function loadModels() {
    try {
      setModels(await api.listModels());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load models.");
    }
  }

  async function loadVersions(modelId: string) {
    try {
      setVersions(await api.listVersions(modelId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load versions.");
    }
  }

  useEffect(() => {
    loadModels();
  }, []);

  useEffect(() => {
    if (selectedModelId) {
      loadVersions(selectedModelId);
    } else {
      setVersions([]);
    }
  }, [selectedModelId]);

  async function handleCreateModel(e: React.FormEvent) {
    e.preventDefault();
    if (!newModelName.trim()) return;
    const model = await api.createModel(newModelName.trim());
    setNewModelName("");
    await loadModels();
    onSelectModel(model.id);
  }

  async function handleCreateVersion(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedModelId || !newVersionLabel.trim()) return;
    const version = await api.createVersion(selectedModelId, newVersionLabel.trim());
    setNewVersionLabel("");
    await loadVersions(selectedModelId);
    onSelectVersion(version.id);
  }

  return (
    <div className="card">
      <h3>Model</h3>
      <select
        value={selectedModelId ?? ""}
        onChange={(e) => {
          onSelectModel(e.target.value || null);
          onSelectVersion(null);
        }}
      >
        <option value="">Select a model...</option>
        {models.map((m) => (
          <option key={m.id} value={m.id}>
            {m.name}
          </option>
        ))}
      </select>
      <form onSubmit={handleCreateModel} className="inline-form">
        <input
          placeholder="New model name"
          value={newModelName}
          onChange={(e) => setNewModelName(e.target.value)}
        />
        <button type="submit">+ Model</button>
      </form>

      {selectedModelId && (
        <>
          <h3>Version</h3>
          <select value={selectedVersionId ?? ""} onChange={(e) => onSelectVersion(e.target.value || null)}>
            <option value="">Select a version...</option>
            {versions.map((v) => (
              <option key={v.id} value={v.id}>
                {v.version_label}
              </option>
            ))}
          </select>
          <form onSubmit={handleCreateVersion} className="inline-form">
            <input
              placeholder="New version label"
              value={newVersionLabel}
              onChange={(e) => setNewVersionLabel(e.target.value)}
            />
            <button type="submit">+ Version</button>
          </form>
        </>
      )}

      {error && <p className="error">{error}</p>}
    </div>
  );
}
