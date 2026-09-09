import { useState } from "react";
import { api, setApiKey } from "../api/client";

export default function AuthGate({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [existingKey, setExistingKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result = await api.signup(email, password);
      setApiKey(result.api_key.api_key);
      onAuthenticated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed.");
    } finally {
      setLoading(false);
    }
  }

  function handleUseExistingKey(e: React.FormEvent) {
    e.preventDefault();
    if (!existingKey.trim()) return;
    setApiKey(existingKey.trim());
    onAuthenticated();
  }

  return (
    <div className="auth-gate">
      <h2>Welcome to ModelWatch</h2>

      <form onSubmit={handleSignup} className="card">
        <h3>Create an account</h3>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Creating..." : "Sign up"}
        </button>
      </form>

      <div className="divider">or</div>

      <form onSubmit={handleUseExistingKey} className="card">
        <h3>Use an existing API key</h3>
        <label>
          API key
          <input
            type="text"
            placeholder="mw_..."
            value={existingKey}
            onChange={(e) => setExistingKey(e.target.value)}
          />
        </label>
        <button type="submit">Continue</button>
      </form>

      {error && <p className="error">{error}</p>}
    </div>
  );
}
