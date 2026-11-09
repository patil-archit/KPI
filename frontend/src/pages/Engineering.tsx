import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useApi } from "../lib/hooks";
import { useAuth } from "../lib/auth";
import { Pill, useToast } from "../lib/ui";
import { PageHead, Loading } from "../components/Page";

export default function Engineering() {
  const toast = useToast();
  const { user } = useAuth();
  const prog = useApi<any>(() => api.get("/api/eng/program"), []);
  const vers = useApi<any[]>(() => api.get("/api/eng/program/versions"), []);
  const [src, setSrc] = useState("");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const canEng = ["engineer", "vendor", "admin"].includes(user?.role || "");

  useEffect(() => { if (prog.data?.source != null) setSrc(prog.data.source); }, [prog.data]);

  const download = async () => {
    setBusy(true);
    try {
      const r = await api.post("/api/eng/program/download", { source: src, comment });
      toast(`Program v${r.version} downloaded to PLC-1`, "ok");
      setComment(""); prog.reload(); vers.reload();
    } catch (e: any) { toast(e.message, "err"); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <PageHead title="Engineering Station" sub="ENG-WS-01 · PLC-1 program (Structured Text) · Purdue L3"
        action={<Pill tone="slate">plc-01 · Modbus unit 1</Pill>} />
      {!canEng && <div className="card p-3 mb-3 text-sm text-status-warn bg-orange-50 border-orange-200">
        Your role has read-only engineering access. Logic download requires an engineer account.</div>}
      <div className="grid lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <div className="card">
            <div className="card-h">
              <span className="card-t">MixTankControl.st</span>
              <span className="text-xs text-slate-400 font-mono">sha {prog.data?.sha256?.slice(0, 12)} · v{prog.data?.version}</span>
            </div>
            <textarea value={src} onChange={(e) => setSrc(e.target.value)} spellCheck={false} disabled={!canEng}
              className="w-full h-[380px] p-4 font-mono text-xs text-slate-800 bg-slate-900 text-green-50 resize-none focus:outline-none"
              style={{ background: "#0b1726", color: "#d6e2f0" }} />
            <div className="p-3 border-t border-slate-200 flex items-center gap-2">
              <input className="input flex-1" placeholder="Change comment (e.g. WO 80004411 retune)"
                value={comment} onChange={(e) => setComment(e.target.value)} />
              <button className="btn-primary" disabled={!canEng || busy} onClick={download}>⬇ Download to PLC</button>
            </div>
          </div>
        </div>
        <div>
          <div className="card">
            <div className="card-h"><span className="card-t">Program versions</span></div>
            <div className="divide-y divide-slate-100 max-h-[460px] overflow-auto">
              <Loading loading={vers.loading} error={vers.error}>
                {vers.data?.map((v) => (
                  <div key={v.version} className="p-3">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-sm">v{v.version}</span>
                      {v.active && <Pill tone="ok">running</Pill>}
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">{v.comment || "—"}</div>
                    <div className="text-[11px] text-slate-400 font-mono mt-1">{v.author} · {v.sha256.slice(0, 16)}</div>
                    <div className="text-[11px] text-slate-400">{new Date(v.created_at).toLocaleString()}</div>
                  </div>
                ))}
              </Loading>
            </div>
          </div>
          <div className="card mt-3 p-3 text-xs text-slate-500">
            <div className="font-medium text-slate-600 mb-1">Note</div>
            Logic downloads change controller behaviour. Policy requires an approved logic-change work order;
            whether the controller enforces that depends on the current range configuration.
          </div>
        </div>
      </div>
    </div>
  );
}
