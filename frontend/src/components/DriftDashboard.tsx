import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { api, Alert, DriftRun, Feature } from "../api/client";

const STATUS_COLORS: Record<string, string> = {
  ok: "#2e7d32",
  moderate: "#f9a825",
  drifted: "#c62828",
  insufficient_data: "#757575",
  completed: "#2e7d32",
  empty: "#757575",
  failed: "#c62828",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className="badge" style={{ backgroundColor: STATUS_COLORS[status] ?? "#555" }}>
      {status}
    </span>
  );
}

export default function DriftDashboard({ versionId, features }: { versionId: string; features: Feature[] }) {
  const [runs, setRuns] = useState<DriftRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<DriftRun | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [triggering, setTriggering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const featureName = (id: string) => features.find((f) => f.id === id)?.name ?? id.slice(0, 8);

  async function loadRuns() {
    try {
      const list = await api.listDriftRuns(versionId);
      setRuns(list.slice().reverse());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load drift runs.");
    }
  }

  async function loadAlerts() {
    try {
      setAlerts(await api.listAlerts(versionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load alerts.");
    }
  }

  useEffect(() => {
    loadRuns();
    loadAlerts();
    setSelectedRun(null);
  }, [versionId]);

  async function handleTrigger() {
    setTriggering(true);
    setError(null);
    try {
      const run = await api.triggerDriftRun(versionId);
      await loadRuns();
      await loadAlerts();
      setSelectedRun(run);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Drift check failed.");
    } finally {
      setTriggering(false);
    }
  }

  async function handleSelectRun(runId: string) {
    const detail = await api.getDriftRun(runId);
    setSelectedRun(detail);
  }

  const chartData =
    selectedRun?.feature_results?.flatMap((fr) =>
      fr.metrics.map((m) => ({
        value: m.metric_value,
        label: `${featureName(fr.feature_id)} / ${m.metric_name.toUpperCase()}`,
      }))
    ) ?? [];

  return (
    <div className="card">
      <div className="row-between">
        <h3>Drift Monitoring</h3>
        <button onClick={handleTrigger} disabled={triggering}>
          {triggering ? "Running..." : "Run Drift Check"}
        </button>
      </div>

      <h4>History</h4>
      <table className="table">
        <thead>
          <tr>
            <th>When</th>
            <th>Window</th>
            <th>Status</th>
            <th>Overall</th>
            <th>Triggered by</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr key={r.id} className="clickable" onClick={() => handleSelectRun(r.id)}>
              <td>{new Date(r.created_at).toLocaleString()}</td>
              <td>
                {new Date(r.window_start).toLocaleTimeString()} - {new Date(r.window_end).toLocaleTimeString()}
              </td>
              <td>
                <StatusBadge status={r.status} />
              </td>
              <td>{r.overall_status ? <StatusBadge status={r.overall_status} /> : "-"}</td>
              <td>{r.triggered_by}</td>
            </tr>
          ))}
          {runs.length === 0 && (
            <tr>
              <td colSpan={5} className="muted">
                No drift runs yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {selectedRun && (
        <>
          <h4>Feature Results - run {selectedRun.id.slice(0, 8)}</h4>
          <table className="table">
            <thead>
              <tr>
                <th>Feature</th>
                <th>Status</th>
                <th>Rows</th>
                <th>Valid</th>
                <th>Missing</th>
                <th>Invalid</th>
                <th>Unseen cat.</th>
                <th>Usable</th>
              </tr>
            </thead>
            <tbody>
              {selectedRun.feature_results?.map((fr) => (
                <tr key={fr.feature_id}>
                  <td>{featureName(fr.feature_id)}</td>
                  <td>
                    <StatusBadge status={fr.feature_status} />
                  </td>
                  <td>{fr.rows_received}</td>
                  <td>{fr.n_valid}</td>
                  <td>{fr.n_missing}</td>
                  <td>{fr.n_invalid}</td>
                  <td>{fr.n_unseen_category}</td>
                  <td>{fr.n_usable}</td>
                </tr>
              ))}
              {(!selectedRun.feature_results || selectedRun.feature_results.length === 0) && (
                <tr>
                  <td colSpan={8} className="muted">
                    Empty window - no observations were processed in this run.
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          {chartData.length > 0 && (
            <>
              <h4>PSI / KS / JS metric values</h4>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={0} angle={-25} textAnchor="end" height={80} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="value" name="Metric value" fill="#1976d2" />
                </BarChart>
              </ResponsiveContainer>
            </>
          )}
        </>
      )}

      <h4>Alerts</h4>
      <ul className="plain-list">
        {alerts.map((a) => (
          <li key={a.id}>
            <span className="badge" style={{ backgroundColor: STATUS_COLORS.drifted }}>
              {a.severity}
            </span>{" "}
            {a.message} <span className="muted">({new Date(a.created_at).toLocaleString()})</span>
          </li>
        ))}
        {alerts.length === 0 && <li className="muted">No alerts for this model version.</li>}
      </ul>

      {error && <p className="error">{error}</p>}
    </div>
  );
}
