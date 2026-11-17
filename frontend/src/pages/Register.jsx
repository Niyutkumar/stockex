import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Wordmark } from "../components/Logo";

export default function Register() {
  const { register } = useAuth();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function onSubmit(event) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await register({ ...form, full_name: form.full_name || null });
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="center">
      <form className="auth-card" onSubmit={onSubmit}>
        <div className="auth-head">
          <Wordmark size={26} fontSize={19} />
          <p>Create an account</p>
        </div>

        {error ? <div className="alert error">{error}</div> : null}

        <div className="field">
          <label htmlFor="name">Name</label>
          <input id="name" type="text" autoComplete="name"
                 value={form.full_name} onChange={set("full_name")} />
        </div>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="username" required
                 value={form.email} onChange={set("email")} />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          {/* minLength matches the API's rule, so the browser catches it
              before a pointless round trip. The server still enforces it. */}
          <input id="password" type="password" autoComplete="new-password" required
                 minLength={8} value={form.password} onChange={set("password")} />
        </div>

        <button className="btn" type="submit" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
        <p className="auth-alt">Already registered? <Link to="/login">Sign in</Link></p>
      </form>
    </div>
  );
}
