import { useState } from "react";
import { api } from "../lib/api";
import { useApi } from "../lib/hooks";
import { useAuth } from "../lib/auth";
import { Modal, Pill, useToast } from "../lib/ui";
import { PageHead, Loading } from "../components/Page";

const woTone: Record<string, string> = {
  created: "slate", approved: "info", in_progress: "blue", closed: "ok", rejected: "high",
};
const ctTone: Record<string, string> = { logic: "crit", parameter: "info", safety_interlock: "high", none: "slate" };

export default function Maintenance() {
  const toast = useToast();
  const { user } = useAuth();
  const wos = useApi<any[]>(() => api.get("/api/erp/maintenance/work-orders"), [], 5000);
  const nots = useApi<any[]>(() => api.get("/api/erp/maintenance/notifications"), []);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ asset: "plc-01", description: "", change_type: "parameter", assigned_to: "s.iyer" });
  const [appr, setAppr] = useState<any | null>(null);
  const [win, setWin] = useState({ window_start_in_minutes: 0, window_minutes: 120 });

  const create = async () => {
    try { await api.post("/api/erp/maintenance/work-orders", form); toast("Work order created", "ok"); setOpen(false); wos.reload(); }
    catch (e: any) { toast(e.message, "err"); }
  };
  const approve = async () => {
    try { await api.post(`/api/erp/maintenance/work-orders/${appr.number}/approve`, win);
      toast(`Work order ${appr.number} approved — maintenance window open`, "ok"); setAppr(null); wos.reload(); }
    catch (e: any) { toast(e.message, "err"); }
  };

  return (
    <div>
      <PageHead title="Plant Maintenance" sub="IW22 / IW32 · notifications and work orders"
        action={<button className="btn-primary" onClick={() => setOpen(true)}>+ Work order</button>} />

      <div className="grid lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <div className="text-xs uppercase tracking-wide text-slate-400 mb-1">Work orders</div>
          <Loading loading={wos.loading} error={wos.error}>
            <div className="card overflow-hidden">
              <table className="w-full">
                <thead><tr>{["WO", "Asset", "Change", "Description", "Status", "Window", ""].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
                <tbody>
                  {wos.data?.map((w) => (
                    <tr key={w.number} className="hover:bg-slate-50 align-top">
                      <td className="td font-medium text-brand-700">{w.number}</td>
                      <td className="td font-mono text-xs">{w.asset}</td>
                      <td className="td"><Pill tone={ctTone[w.change_type]}>{w.change_type}</Pill></td>
                      <td className="td max-w-xs">{w.description}
                        <div className="text-[11px] text-slate-400">req: {w.requested_by}{w.approved_by && ` · appr: ${w.approved_by}`}</div></td>
                      <td className="td"><Pill tone={woTone[w.status]}>{w.status}</Pill></td>
                      <td className="td text-[11px] text-slate-500">
                        {w.window_start ? `${new Date(w.window_start).toLocaleTimeString()}–${new Date(w.window_end).toLocaleTimeString()}` : "—"}</td>
                      <td className="td text-right whitespace-nowrap">
                        {w.status === "created" && <button className="btn-soft" onClick={() => setAppr(w)}>Approve</button>}
                        {w.status === "approved" && <button className="btn-ghost" onClick={async () => {
                          await api.post(`/api/erp/maintenance/work-orders/${w.number}/close`); wos.reload(); }}>Close</button>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Loading>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wide text-slate-400 mb-1">Notifications</div>
          <Loading loading={nots.loading} error={nots.error}>
            <div className="space-y-2">
              {nots.data?.map((n) => (
                <div key={n.number} className="card p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm text-brand-700">{n.number}</span>
                    <Pill tone={n.status === "closed" ? "ok" : n.status === "open" ? "warn" : "info"}>{n.status}</Pill>
                  </div>
                  <div className="text-sm text-slate-700 mt-1">{n.asset}</div>
                  <div className="text-xs text-slate-500">{n.description}</div>
                </div>
              ))}
            </div>
          </Loading>
        </div>
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title="Create work order">
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label">Asset</label>
              <select className="input" value={form.asset} onChange={(e) => setForm({ ...form, asset: e.target.value })}>
                {["plc-01", "sis-01", "hmi-01", "eng-ws-01"].map((a) => <option key={a}>{a}</option>)}
              </select></div>
            <div><label className="label">Change type</label>
              <select className="input" value={form.change_type} onChange={(e) => setForm({ ...form, change_type: e.target.value })}>
                {["parameter", "logic", "safety_interlock", "none"].map((a) => <option key={a}>{a}</option>)}
              </select></div>
          </div>
          <div><label className="label">Description</label>
            <textarea className="input" rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
          <div className="flex justify-end gap-2 pt-1">
            <button className="btn-soft" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn-primary" onClick={create}>Create</button>
          </div>
        </div>
      </Modal>

      <Modal open={!!appr} onClose={() => setAppr(null)} title={`Approve work order ${appr?.number}`}>
        <div className="space-y-3">
          <p className="text-sm text-slate-600">
            Approving opens a maintenance window during which the planned {appr?.change_type} change on
            <span className="font-mono"> {appr?.asset}</span> is authorized.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label">Starts in (min)</label>
              <input className="input" type="number" value={win.window_start_in_minutes}
                onChange={(e) => setWin({ ...win, window_start_in_minutes: +e.target.value })} /></div>
            <div><label className="label">Duration (min)</label>
              <input className="input" type="number" value={win.window_minutes}
                onChange={(e) => setWin({ ...win, window_minutes: +e.target.value })} /></div>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <button className="btn-soft" onClick={() => setAppr(null)}>Cancel</button>
            <button className="btn-primary" onClick={approve}>Approve & open window</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
