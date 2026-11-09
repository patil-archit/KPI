import { useState } from "react";
import { dev, evidence, getDevToken, setDevToken } from "../lib/api";
import { useApi } from "../lib/hooks";
import { Pill, useToast, Modal } from "../lib/ui";

export default function DevMode() {
  const toast = useToast();
  const [tab, setTab] = useState<"switchboard" | "scenarios" | "cases" | "controls" | "feed">("switchboard");
  const [tokenInput, setTokenInput] = useState(getDevToken());
  const status = useApi<any>(() => dev.get("/dev/status"), [], 4000);

  if (status.error)
    return (
      <TokenGate current={tokenInput} onSave={(t) => { setDevToken(t); setTokenInput(t); status.reload(); }} error={status.error} />
    );

  const tabs = [["switchboard", "Breach Points"], ["scenarios", "Scenarios"], ["cases", "Cases & Ground Truth"],
    ["controls", "Plant Controls"], ["feed", "Evidence Feed"]] as const;

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      <header className="h-14 bg-black/40 border-b border-white/10 flex items-center px-5 gap-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-gradient-to-br from-rose-500 to-orange-500 grid place-items-center font-bold">⚡</div>
          <div>
            <div className="font-semibold leading-tight">Range Control Center</div>
            <div className="text-[11px] text-slate-400 leading-tight">ArenaPlant · Developer Mode</div>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-4 text-xs">
          <Stat label="Process T" value={`${status.data?.process?.temperature ?? "—"}°C`} />
          <Stat label="SIS" value={status.data?.sis_tripped ? "TRIPPED" : "armed"} tone={status.data?.sis_tripped ? "high" : "ok"} />
          <Stat label="Events" value={status.data?.event_count ?? "—"} />
          <Stat label="Cases" value={status.data?.case_count ?? "—"} />
          <Stat label="Speed" value={`${status.data?.speed ?? 1}×`} />
          <a href="/" className="text-slate-400 hover:text-white">← Plant UI</a>
        </div>
      </header>

      <div className="flex gap-1 px-5 pt-4 border-b border-white/10">
        {tabs.map(([k, l]) => (
          <button key={k} onClick={() => setTab(k as any)}
            className={`px-4 py-2 text-sm rounded-t ${tab === k ? "bg-slate-800 text-white" : "text-slate-400 hover:text-white"}`}>{l}</button>
        ))}
        <div className="ml-auto pb-2">
          <ResetButton onDone={() => { status.reload(); toast("Range reset to baseline", "ok"); }} />
        </div>
      </div>

      <main className="p-5 max-w-7xl mx-auto">
        {tab === "switchboard" && <Switchboard onChange={() => status.reload()} />}
        {tab === "scenarios" && <Scenarios onRun={() => status.reload()} />}
        {tab === "cases" && <Cases />}
        {tab === "controls" && <Controls status={status.data} onChange={() => status.reload()} />}
        {tab === "feed" && <Feed />}
      </main>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: any; tone?: string }) {
  return (
    <div className="text-center">
      <div className="text-[10px] uppercase text-slate-500">{label}</div>
      <div className={`font-semibold tabular-nums ${tone === "high" ? "text-rose-400" : tone === "ok" ? "text-emerald-400" : ""}`}>{value}</div>
    </div>
  );
}

function TokenGate({ current, onSave, error }: { current: string; onSave: (t: string) => void; error: string }) {
  const [t, setT] = useState(current);
  return (
    <div className="min-h-screen bg-slate-900 grid place-items-center p-4">
      <div className="bg-slate-800 rounded-lg p-6 w-full max-w-sm text-slate-100">
        <h1 className="font-semibold text-lg">Developer Mode</h1>
        <p className="text-sm text-slate-400 mt-1">Range Control Center is protected by a developer token
          separate from the plant logins. Agents never receive it.</p>
        <input className="input mt-4 text-slate-900" value={t} onChange={(e) => setT(e.target.value)} placeholder="x-dev-token" />
        <div className="text-xs text-rose-400 mt-2">{error}</div>
        <button className="btn-primary w-full justify-center mt-3" onClick={() => onSave(t)}>Unlock</button>
        <div className="text-[11px] text-slate-500 mt-3">Default (dev): <code>arena-dev-token</code></div>
      </div>
    </div>
  );
}

// ---------------- switchboard ----------------
function Switchboard({ onChange }: { onChange: () => void }) {
  const toast = useToast();
  const { data, reload } = useApi<any>(() => dev.get("/dev/breach-points"), []);
  const set = async (key: string, mode: string) => {
    try { await dev.post("/dev/breach-points", { changes: { [key]: mode } }); reload(); onChange(); }
    catch (e: any) { toast(e.message, "err"); }
  };
  const preset = async (p: string) => {
    try { await dev.post("/dev/preset", { preset: p }); reload(); onChange(); toast(`Preset applied: ${p}`, "ok"); }
    catch (e: any) { toast(e.message, "err"); }
  };
  const allV = async (mode: string) => {
    const changes = Object.fromEntries((data?.breach_points || []).map((b: any) => [b.key, mode]));
    await dev.post("/dev/breach-points", { changes }); reload(); onChange();
  };

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <span className="text-sm text-slate-400">Presets:</span>
        {Object.entries(data?.presets || {}).map(([k, v]: any) => (
          <button key={k} onClick={() => preset(k)} title={v.description}
            className="text-xs px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 border border-white/10">{v.label}</button>
        ))}
        <div className="ml-auto flex gap-2">
          <button onClick={() => allV("vulnerable")} className="text-xs px-3 py-1.5 rounded bg-rose-900/50 hover:bg-rose-900 border border-rose-700/50">All vulnerable</button>
          <button onClick={() => allV("patched")} className="text-xs px-3 py-1.5 rounded bg-emerald-900/50 hover:bg-emerald-900 border border-emerald-700/50">All patched</button>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-3">
        {data?.breach_points?.map((b: any) => {
          const vuln = b.mode === "vulnerable";
          return (
            <div key={b.key} className={`rounded-lg border p-4 ${vuln ? "bg-rose-950/30 border-rose-800/40" : "bg-emerald-950/20 border-emerald-800/30"}`}>
              <div className="flex items-start gap-3">
                <div className="font-mono text-xs px-2 py-1 rounded bg-black/30">{b.key}</div>
                <div className="flex-1">
                  <div className="font-medium text-sm">{b.title}</div>
                  <div className="flex gap-1.5 mt-1 flex-wrap">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700">{b.layer}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700">{b.asset}</span>
                    {b.scenarios.map((s: number) => <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-brand-900/60">Scn {s}</span>)}
                  </div>
                </div>
                <button onClick={() => set(b.key, vuln ? "patched" : "vulnerable")}
                  className={`shrink-0 w-28 py-1.5 rounded text-xs font-semibold ${vuln ? "bg-rose-600 hover:bg-rose-500" : "bg-emerald-600 hover:bg-emerald-500"}`}>
                  {vuln ? "VULNERABLE" : "PATCHED"}
                </button>
              </div>
              <p className="text-xs text-slate-400 mt-2">{vuln ? b.vulnerable : b.patched}</p>
              <div className="text-[10px] text-slate-500 mt-1 font-mono">{b.techniques.join(" · ")}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------- scenarios ----------------
function Scenarios({ onRun }: { onRun: () => void }) {
  const toast = useToast();
  const { data, reload } = useApi<any>(() => dev.get("/dev/scenarios"), [], 3000);
  const [running, setRunning] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  const run = async (key: string) => {
    setRunning(key);
    try { const r = await dev.post("/dev/scenarios/run", { key, fast: true }); setResult(r); reload(); onRun();
      toast(`Scenario ${key} complete · ${r.events_generated} events`, "ok"); }
    catch (e: any) { toast(e.message, "err"); }
    finally { setRunning(null); }
  };

  return (
    <div>
      <p className="text-sm text-slate-400 mb-3">Each scenario runs through the same entry points as real activity and
        records hidden ground truth. Scenario 7 is the mechanical twin of 4/6 — same change, authorized.</p>
      <div className="grid md:grid-cols-2 gap-3">
        {data?.scenarios?.map((s: any) => (
          <div key={s.key} className="rounded-lg border border-white/10 bg-slate-800/60 p-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-black/30">Scn {s.key}</span>
                  <Pill tone={s.is_attack ? "high" : "ok"}>{s.is_attack ? "attack" : "maintenance"}</Pill>
                </div>
                <div className="font-medium text-sm mt-1.5">{s.name}</div>
              </div>
              <button disabled={!s.runnable || !!running} onClick={() => run(s.key)}
                className="btn-primary py-1.5 text-xs disabled:opacity-40">{running === s.key ? "Running…" : "▶ Run"}</button>
            </div>
            <p className="text-xs text-slate-400 mt-2">{s.summary}</p>
            <div className="flex flex-wrap gap-1 mt-2">
              <span className="text-[10px] text-slate-500">Purdue: {s.purdue_path.join(" → ")}</span>
            </div>
            {!s.runnable &&
              <div className="text-[11px] text-amber-400 mt-1">Needs vulnerable: {s.blocked_by_patched.join(", ")} (patched → will be blocked, still logged)</div>}
          </div>
        ))}
      </div>

      <Modal open={!!result} onClose={() => setResult(null)} title={`Scenario ${result?.scenario} result`} wide>
        <div className="text-sm space-y-2 text-slate-700">
          <div className="flex gap-2">
            <Pill tone={result?.is_attack ? "high" : "ok"}>{result?.is_attack ? "attack" : "legitimate maintenance"}</Pill>
            <Pill tone="slate">{result?.events_generated} evidence events</Pill>
            <Pill tone="blue">case {result?.case_key}</Pill>
          </div>
          <ol className="mt-3 space-y-1.5 border-l-2 border-slate-200 pl-4">
            {result?.steps?.map((st: any, i: number) => (
              <li key={i} className="text-xs">
                <span className="text-slate-700">{st.action}</span>
                {st.outcome && <span className={`ml-2 ${st.outcome === "blocked" ? "text-rose-600" : "text-emerald-600"}`}>[{st.outcome}]</span>}
                {st.purdue && <span className="ml-2 text-slate-400 font-mono">{st.purdue}</span>}
              </li>
            ))}
          </ol>
        </div>
      </Modal>
    </div>
  );
}

// ---------------- cases ----------------
function Cases() {
  const { data } = useApi<any[]>(() => dev.get("/dev/cases"), [], 4000);
  const [detail, setDetail] = useState<any | null>(null);
  const open = async (k: string) => setDetail(await dev.get(`/dev/cases/${k}`));
  return (
    <div>
      <p className="text-sm text-slate-400 mb-3">Ground truth for each scenario run. This is served only here —
        the agents' <code className="text-brand-300">/evidence</code> endpoint never exposes it. Use it to score agent verdicts.</p>
      <div className="rounded-lg border border-white/10 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-800"><tr>
            {["Case", "Scenario", "Type", "Event IDs", "Techniques", ""].map((h) => <th key={h} className="text-left px-3 py-2 text-xs text-slate-400">{h}</th>)}
          </tr></thead>
          <tbody>
            {data?.map((c) => (
              <tr key={c.case_key} className="border-t border-white/5 hover:bg-slate-800/50">
                <td className="px-3 py-2 font-mono text-xs text-brand-300">{c.case_key}</td>
                <td className="px-3 py-2">{c.scenario}</td>
                <td className="px-3 py-2"><Pill tone={c.is_attack ? "high" : "ok"}>{c.variant}</Pill></td>
                <td className="px-3 py-2 font-mono text-xs text-slate-400">{c.first_event_id}–{c.last_event_id}</td>
                <td className="px-3 py-2 text-xs text-slate-400">{(c.techniques || []).join(", ") || "—"}</td>
                <td className="px-3 py-2 text-right"><button className="btn-soft py-1 text-xs" onClick={() => open(c.case_key)}>Ground truth</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal open={!!detail} onClose={() => setDetail(null)} title={`Ground truth · ${detail?.case_key}`} wide>
        <pre className="text-xs font-mono bg-slate-50 p-4 rounded border overflow-auto max-h-[60vh]">
          {JSON.stringify(detail?.ground_truth, null, 2)}
        </pre>
      </Modal>
    </div>
  );
}

// ---------------- controls ----------------
function Controls({ status, onChange }: { status: any; onChange: () => void }) {
  const toast = useToast();
  const mfa = useApi<any>(() => dev.get("/dev/mfa-inbox"), [], 3000);
  const [fault, setFault] = useState({ tag: "temperature", kind: "stuck", value: 72 });
  const setSpeed = async (v: number) => { await dev.post("/dev/plant/speed", { speed: v }); onChange(); };
  const inject = async () => { await dev.post("/dev/plant/fault", fault); toast("Fault injected", "ok"); };
  const clear = async () => { await dev.post("/dev/plant/fault", { tag: fault.tag, kind: "clear" }); toast("Fault cleared", "ok"); };

  return (
    <div className="grid md:grid-cols-2 gap-4">
      <div className="rounded-lg border border-white/10 bg-slate-800/60 p-4">
        <div className="font-medium mb-2">Simulation speed</div>
        <div className="flex gap-2">
          {[1, 2, 5, 10, 20].map((v) => (
            <button key={v} onClick={() => setSpeed(v)}
              className={`px-3 py-1.5 rounded text-sm ${status?.speed === v ? "bg-brand-600" : "bg-slate-700 hover:bg-slate-600"}`}>{v}×</button>
          ))}
        </div>
        <p className="text-xs text-slate-400 mt-2">Speeds up process physics so a scenario reaches its impact faster.</p>
      </div>

      <div className="rounded-lg border border-white/10 bg-slate-800/60 p-4">
        <div className="font-medium mb-2">Inject sensor fault (non-attack anomaly)</div>
        <div className="grid grid-cols-3 gap-2">
          <select className="input text-slate-900 py-1.5" value={fault.tag} onChange={(e) => setFault({ ...fault, tag: e.target.value })}>
            {["temperature", "pressure", "level", "conveyor_speed", "motor_current"].map((t) => <option key={t}>{t}</option>)}
          </select>
          <select className="input text-slate-900 py-1.5" value={fault.kind} onChange={(e) => setFault({ ...fault, kind: e.target.value })}>
            {["stuck", "drift"].map((k) => <option key={k}>{k}</option>)}
          </select>
          <input className="input text-slate-900 py-1.5" type="number" value={fault.value} onChange={(e) => setFault({ ...fault, value: +e.target.value })} />
        </div>
        <div className="flex gap-2 mt-2">
          <button className="btn-primary py-1.5 text-xs" onClick={inject}>Inject</button>
          <button className="btn-soft py-1.5 text-xs" onClick={clear}>Clear</button>
        </div>
        <p className="text-xs text-slate-400 mt-2">Tests whether agents raise false positives on a benign fault.</p>
      </div>

      <div className="rounded-lg border border-white/10 bg-slate-800/60 p-4 md:col-span-2">
        <div className="font-medium mb-2">Simulated MFA device (one-time codes)</div>
        {(!mfa.data?.messages?.length) && <div className="text-sm text-slate-400">No codes yet. Try a Remote Portal login with MFA patched (B1).</div>}
        <div className="space-y-1">
          {mfa.data?.messages?.map((m: any, i: number) => (
            <div key={i} className="flex items-center gap-3 text-sm">
              <span className="font-mono text-lg tracking-widest text-emerald-400">{m.code}</span>
              <span className="text-slate-400">→ {m.username}</span>
              <span className="text-xs text-slate-500">{new Date(m.ts).toLocaleTimeString()}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------- evidence feed ----------------
function Feed() {
  const { data } = useApi<any>(() => evidence.get("/evidence/events?limit=60"), [], 2500);
  const evs = [...(data?.events || [])].reverse();
  const sev: Record<string, string> = { critical: "text-purple-400", high: "text-rose-400", moderate: "text-amber-400", low: "text-sky-400", info: "text-slate-400" };
  const out: Record<string, string> = { blocked: "text-rose-400", failure: "text-amber-400", success: "text-emerald-400", info: "text-slate-400" };
  return (
    <div>
      <p className="text-sm text-slate-400 mb-3">Exactly what the Cyber-Arena agents see via the read-only
        <code className="text-brand-300"> /evidence</code> endpoint. One schema for every source; no ground-truth labels.</p>
      <div className="rounded-lg border border-white/10 bg-black/40 font-mono text-xs max-h-[70vh] overflow-auto">
        {evs.map((e: any) => (
          <div key={e.id} className="px-3 py-1.5 border-b border-white/5 flex gap-3 hover:bg-white/5">
            <span className="text-slate-600 w-10">#{e.id}</span>
            <span className="text-slate-500 w-16">{new Date(e.ts).toLocaleTimeString()}</span>
            <span className="text-slate-400 w-16">L{e.purdue_level} {e.source}</span>
            <span className="text-brand-300 w-24">{e.host}</span>
            <span className="flex-1 text-slate-200">{e.event_type}
              {e.change_type !== "none" && <span className="text-amber-300"> [{e.change_type}]</span>}
              {e.actor && <span className="text-slate-500"> · {e.actor}</span>}
              {e.src_ip && <span className="text-slate-600"> {e.src_ip}→{e.dst_ip}</span>}
            </span>
            <span className={out[e.outcome] || "text-slate-400"}>{e.outcome}</span>
            <span className={`${sev[e.severity]} w-16 text-right`}>{e.severity}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ResetButton({ onDone }: { onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  return (
    <button disabled={busy} onClick={async () => { setBusy(true); try { await dev.post("/dev/reset"); onDone(); } finally { setBusy(false); } }}
      className="text-xs px-3 py-1.5 rounded bg-slate-700 hover:bg-slate-600 border border-white/10">
      {busy ? "Resetting…" : "↻ Reset range"}
    </button>
  );
}
