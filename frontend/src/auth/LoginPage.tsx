import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { supabase } from "../supabaseClient";
import { useAuth } from "./AuthProvider";

export function LoginPage() {
  const { session, loading } = useAuth();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState<string | null>(null);

  if (loading) return <div className="p-8 text-slate-500">Loading…</div>;
  if (session) return <Navigate to="/" replace />;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setBusy(true);
    try {
      if (mode === "signup") {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        setInfo("Account created. Check your email if confirmation is required.");
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form
        onSubmit={onSubmit}
        className="bg-white p-8 rounded-xl shadow-sm border border-slate-200 w-full max-w-sm space-y-4"
      >
        <h1 className="text-xl font-bold">House Finder</h1>
        <div className="flex gap-2 text-sm">
          <button
            type="button"
            className={`flex-1 py-1.5 rounded ${mode === "signin" ? "bg-slate-900 text-white" : "bg-slate-100"}`}
            onClick={() => setMode("signin")}
          >
            Sign in
          </button>
          <button
            type="button"
            className={`flex-1 py-1.5 rounded ${mode === "signup" ? "bg-slate-900 text-white" : "bg-slate-100"}`}
            onClick={() => setMode("signup")}
          >
            Sign up
          </button>
        </div>
        <input
          type="email"
          required
          autoFocus
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="w-full px-3 py-2 border border-slate-300 rounded"
        />
        <input
          type="password"
          required
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="password"
          className="w-full px-3 py-2 border border-slate-300 rounded"
        />
        {error && <div className="text-sm text-red-600">{error}</div>}
        {info && <div className="text-sm text-emerald-700">{info}</div>}
        <button
          type="submit"
          disabled={busy}
          className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded disabled:opacity-50"
        >
          {busy ? "Working…" : mode === "signin" ? "Sign in" : "Create account"}
        </button>
      </form>
    </div>
  );
}
