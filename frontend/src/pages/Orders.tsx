import { useState } from "react";
import { api } from "../lib/api";
import { useApi } from "../lib/hooks";
import { useAuth } from "../lib/auth";
import { Modal, Pill, useToast } from "../lib/ui";
import { PageHead, Loading } from "../components/Page";

const statusTone: Record<string, string> = {
  created: "slate", released: "info", in_progress: "blue", completed: "ok", cancelled: "high",
};

export default function Orders() {
  const toast = useToast();
  const { user } = useAuth();
  const { data, loading, error, reload } = useApi<any[]>(() => api.get("/api/erp/orders"), [], 5000);
  const mats = useApi<any[]>(() => api.get("/api/erp/inventory"), []);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ material_code: "FG-3001", quantity: 12000, temp_sp: 72, conveyor_sp: 1.0 });
  const canPlan = ["planner", "admin"].includes(user?.role || "");

  const create = async () => {
    try { await api.post("/api/erp/orders", form); toast("Production order created", "ok"); setOpen(false); reload(); }
    catch (e: any) { toast(e.message, "err"); }
  };
  const release = async (num: string) => {
    try { await api.post(`/api/erp/orders/${num}/release`); toast(`Order ${num} released`, "ok"); reload(); }
    catch (e: any) { toast(e.message, "err"); }
  };

  return (
    <div>
      <PageHead title="Production Orders" sub="COOIS · Line 2 discrete filling"
        action={canPlan && <button className="btn-primary" onClick={() => setOpen(true)}>+ Create order</button>} />
      <Loading loading={loading} error={error}>
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead><tr>
              {["Order", "Material", "Product", "Qty", "Done", "Recipe", "Status", ""].map((h) => <th key={h} className="th">{h}</th>)}
            </tr></thead>
            <tbody>
              {data?.map((o) => (
                <tr key={o.number} className="hover:bg-slate-50">
                  <td className="td font-medium text-brand-700">{o.number}</td>
                  <td className="td font-mono text-xs">{o.material_code}</td>
                  <td className="td">{o.product}</td>
                  <td className="td tabular-nums">{o.quantity.toLocaleString()}</td>
                  <td className="td tabular-nums">{o.completed_qty.toLocaleString()}</td>
                  <td className="td text-xs text-slate-500">{o.recipe.temp_sp}°C · {o.recipe.conveyor_sp} m/s</td>
                  <td className="td"><Pill tone={statusTone[o.status]}>{o.status}</Pill></td>
                  <td className="td text-right">
                    {o.status === "created" && canPlan &&
                      <button className="btn-soft" onClick={() => release(o.number)}>Release</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Loading>

      <Modal open={open} onClose={() => setOpen(false)} title="Create production order">
        <div className="space-y-3">
          <div>
            <label className="label">Material</label>
            <select className="input" value={form.material_code} onChange={(e) => setForm({ ...form, material_code: e.target.value })}>
              {mats.data?.filter((m) => m.category === "Finished").map((m) => (
                <option key={m.code} value={m.code}>{m.code} · {m.name}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div><label className="label">Quantity</label>
              <input className="input" type="number" value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: +e.target.value })} /></div>
            <div><label className="label">Temp SP (°C)</label>
              <input className="input" type="number" value={form.temp_sp}
                onChange={(e) => setForm({ ...form, temp_sp: +e.target.value })} /></div>
            <div><label className="label">Conveyor (m/s)</label>
              <input className="input" type="number" step="0.1" value={form.conveyor_sp}
                onChange={(e) => setForm({ ...form, conveyor_sp: +e.target.value })} /></div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button className="btn-soft" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn-primary" onClick={create}>Create</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
