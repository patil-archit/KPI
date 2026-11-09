import { useState } from "react";
import { useAuth } from "../lib/auth";
import { useToast } from "../lib/ui";

const DEMO = [
  { u: "a.kulkarni", p: "Plan#2025a", r: "Planner" },
  { u: "p.nair", p: "Oper#2025p", r: "Operator" },
  { u: "s.iyer", p: "Eng#2025s", r: "Engineer" },
  { u: "r.mehta", p: "Super#2025r", r: "Maint. Supervisor" },
  { u: "m.rao", p: "Admin#2025m", r: "IT Admin" },
];

export default function Login() {
  const { login, mfa } = useAuth();
  const toast = useToast();
  const [u, setU] = useState("a.kulkarni");
  const [p, setP] = useState("Plan#2025a");
  const [via, setVia] = useState("corp");
  const [busy, setBusy] = useState(false);
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [code, setCode] = useState("");

  const submit = async () => {
    setBusy(true);
    try {
      const r = await login(u, p, via);
      if (r.mfa) { setMfaToken(r.token); toast("MFA code required (see Developer Mode inbox)", "info"); }
    } catch (e: any) { toast(e.message, "err"); }
    finally { setBusy(false); }
  };
  const submitMfa = async () => {
    setBusy(true);
    try { await mfa(mfaToken!, code); } catch (e: any) { toast(e.message, "err"); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* brand side */}
      <div className="hidden lg:flex flex-col justify-between bg-shell-header text-white p-10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded bg-brand-500 grid place-items-center font-bold">K</div>
          <div className="font-semibold text-lg">Kaveri Process Industries</div>
        </div>
        <div>
          <div className="text-brand-300 text-sm font-medium tracking-wide">ArenaPlant S/4 · Integrated Operations</div>
          <h1 className="text-4xl font-bold mt-3 leading-tight">Enterprise to<br />factory floor,<br />one platform.</h1>
          <p className="text-brand-100 mt-4 max-w-md">
            Production planning, plant maintenance, SCADA and controller engineering for Line 2 beverage filling.
          </p>
        </div>
        <div className="text-xs text-brand-200">
          Sandboxed security test range · Purdue L4–L0 · deliberately includes known weaknesses.
        </div>
      </div>

      {/* form side */}
      <div className="flex items-center justify-center p-6 bg-slate-50">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded bg-brand-600 grid place-items-center text-white font-bold">K</div>
            <span className="font-semibold">Kaveri Process Industries</span>
          </div>
          <h2 className="text-xl font-semibold text-slate-800">{mfaToken ? "Two-step verification" : "Sign in"}</h2>
          <p className="text-sm text-slate-500 mt-1">
            {mfaToken ? "Enter the one-time code sent to your registered device." : "Use your corporate or remote credentials."}
          </p>

          {!mfaToken ? (
            <div className="mt-6 space-y-4">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <button onClick={() => setVia("corp")}
                  className={`py-2 rounded border ${via === "corp" ? "border-brand-500 bg-brand-50 text-brand-700 font-medium" : "border-slate-300 text-slate-600"}`}>
                  Corporate SSO
                </button>
                <button onClick={() => setVia("remote")}
                  className={`py-2 rounded border ${via === "remote" ? "border-brand-500 bg-brand-50 text-brand-700 font-medium" : "border-slate-300 text-slate-600"}`}>
                  Remote Portal
                </button>
              </div>
              <div>
                <label className="label">Username</label>
                <input className="input" value={u} onChange={(e) => setU(e.target.value)} />
              </div>
              <div>
                <label className="label">Password</label>
                <input className="input" type="password" value={p} onChange={(e) => setP(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && submit()} />
              </div>
              <button className="btn-primary w-full justify-center" disabled={busy} onClick={submit}>
                {busy ? "Signing in…" : "Sign in"}
              </button>
            </div>
          ) : (
            <div className="mt-6 space-y-4">
              <input className="input text-center tracking-[0.5em] text-lg" maxLength={6} placeholder="000000"
                value={code} onChange={(e) => setCode(e.target.value)} onKeyDown={(e) => e.key === "Enter" && submitMfa()} />
              <button className="btn-primary w-full justify-center" disabled={busy} onClick={submitMfa}>Verify</button>
              <button className="btn-ghost w-full justify-center" onClick={() => setMfaToken(null)}>Back</button>
            </div>
          )}

          <div className="mt-8 border-t border-slate-200 pt-4">
            <div className="text-xs font-medium text-slate-500 mb-2">Demo accounts (click to fill)</div>
            <div className="flex flex-wrap gap-1.5">
              {DEMO.map((d) => (
                <button key={d.u} onClick={() => { setU(d.u); setP(d.p); setVia("corp"); }}
                  className="text-xs px-2 py-1 rounded bg-white border border-slate-200 hover:border-brand-400 text-slate-600">
                  {d.r}
                </button>
              ))}
            </div>
            <a href="/dev" className="inline-block mt-4 text-xs text-brand-600 hover:underline">
              → Open Developer Mode (Range Control Center)
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
