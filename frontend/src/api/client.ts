const BASE_URL = "/api";

export interface Model {
  id: string;
  name: string;
  created_at: string;
}

export interface ModelVersion {
  id: string;
  model_id: string;
  version_label: string;
  created_at: string;
}

export interface Feature {
  id: string;
  model_version_id: string;
  name: string;
  data_type: "numeric" | "categorical";
  created_at: string;
}

export interface ReferenceSnapshot {
  id: string;
  model_version_id: string;
  label: string;
  created_at: string;
  source_metadata: Record<string, unknown> | null;
  stats: { feature_id: string; statistics: Record<string, unknown>; n_valid: number; n_missing: number }[];
}

export interface FeatureDriftMetric {
  metric_name: string;
  metric_value: number;
  p_value: number | null;
  threshold_used: number;
  status: string;
}

export interface FeatureDriftResult {
  feature_id: string;
  rows_received: number;
  n_valid: number;
  n_missing: number;
  n_invalid: number;
  n_unseen_category: number;
  n_usable: number;
  feature_status: string;
  metrics: FeatureDriftMetric[];
}

export interface DriftRun {
  id: string;
  model_version_id: string;
  reference_snapshot_id: string;
  window_start: string;
  window_end: string;
  status: string;
  triggered_by: string;
  created_at: string;
  overall_status?: string;
  feature_results?: FeatureDriftResult[];
}

export interface Alert {
  id: string;
  model_version_id: string;
  feature_id: string | null;
  drift_run_id: string;
  severity: string;
  message: string;
  created_at: string;
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let apiKey: string | null = localStorage.getItem("modelwatch_api_key");

export function setApiKey(key: string | null) {
  apiKey = key;
  if (key) localStorage.setItem("modelwatch_api_key", key);
  else localStorage.removeItem("modelwatch_api_key");
}

export function getApiKey(): string | null {
  return apiKey;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (apiKey) headers["X-API-Key"] = apiKey;

  const resp = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ? JSON.stringify(body.detail) : detail;
    } catch {
      /* ignore parse errors */
    }
    throw new ApiError(resp.status, detail);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export const api = {
  signup: (email: string, password: string) =>
    request<{ user: { id: string; email: string }; api_key: { api_key: string } }>("/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  listModels: () => request<Model[]>("/models"),
  createModel: (name: string) => request<Model>("/models", { method: "POST", body: JSON.stringify({ name }) }),

  listVersions: (modelId: string) => request<ModelVersion[]>(`/models/${modelId}/versions`),
  createVersion: (modelId: string, versionLabel: string) =>
    request<ModelVersion>(`/models/${modelId}/versions`, {
      method: "POST",
      body: JSON.stringify({ version_label: versionLabel }),
    }),

  listFeatures: (versionId: string) => request<Feature[]>(`/versions/${versionId}/features`),
  createFeature: (versionId: string, name: string, dataType: "numeric" | "categorical") =>
    request<Feature>(`/versions/${versionId}/features`, {
      method: "POST",
      body: JSON.stringify({ name, data_type: dataType }),
    }),

  listSnapshots: (versionId: string) => request<ReferenceSnapshot[]>(`/versions/${versionId}/reference-snapshots`),

  listDriftRuns: (versionId: string) => request<DriftRun[]>(`/versions/${versionId}/drift-runs`),
  getDriftRun: (runId: string) => request<DriftRun>(`/drift-runs/${runId}`),
  triggerDriftRun: (versionId: string) =>
    request<DriftRun>(`/versions/${versionId}/drift-runs`, { method: "POST", body: JSON.stringify({}) }),

  listAlerts: (versionId: string) => request<Alert[]>(`/versions/${versionId}/alerts`),
};

export { ApiError };
