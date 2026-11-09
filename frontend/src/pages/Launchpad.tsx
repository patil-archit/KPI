import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useApi } from "../lib/hooks";
import { Pill, StatusDot } from "../lib/ui";
import { useAuth } from "../lib/auth";

function Tile({ to, title, sub, value, tone }: { to: string; title: string; sub: string; value?: string; tone?: string }) {
  return (
    <Link to={to} className="card p-4 hover:shadow-md hover:-translate-y-0.5 transition block">
      <div className="text-xs text-slate-500">{sub}</div>
      <div className="font-semibold text-slate-800 mt-0.5">{title}</div>
      {value && <div className="kpi text-brand-700 mt-3">{value}</div>}
      {tone && <div className="mt-3"><StatusDot tone={tone} /></div>}
    </Link>
  );
}

export default function Launchpad() {
  const { user } = useAuth();
  const orders = useApi<any[]>(() => api.get("/api/erp/orders"), []);
  const inv = useApi<any[]>(() => api.get("/api/erp/inventory"), []);
  const plant = useApi<any>(() => api.get("/api/plant/state"), [], 3000);

  const open = orders.data?.filter((o) => ["released", "in_progress", "created"].includes(o.status)).length ?? 0;
  const low = (inv.data as any[])?.filter((m) => m.below_reorder).length ?? 0;
  const activeAlarms = plant.data?.alarms?.length ?? 0;
  const temp = plant.data?.tags?.find((t: any) => t.key === "temperature");

  return (
    <div>
      <div className="flex items-end justify-between mb-5">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Welcome, {user?.full_name?.split(" ")[0]}</h1>
          <p className="text-slate-500 text-sm">Line 2 · Mango beverage filling · integrated operations overview</p>
        </div>
        <Pill tone={plant.data?.safety?.sis_tripped ? "high" : "ok"}>
          {plant.data?.safety?.sis_tripped ? "SIS TRIPPED" : "Process nominal"}
        </Pill>
      </div>

      <div className="mb-6">
        <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">Operations snapshot</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Tile to="/scada" title="Tank Temperature" sub="Live · TT101"
            value={temp ? `${temp.value} °C` : "—"} />
          <Tile to="/scada" title="Active Alarms" sub="SCADA" value={String(activeAlarms)}
            tone={activeAlarms ? "warn" : "ok"} />
          <Tile to="/scada" title="Bottles Produced" sub="This run" value={String(plant.data?.production?.bottles ?? "—")} />
          <Tile to="/orders" title="Open Orders" sub="Production" value={String(open)} />
        </div>
      </div>

      <div>
        <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">Applications</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Tile to="/orders" title="Production Orders" sub="Manage & release" />
          <Tile to="/inventory" title="Inventory" sub={low ? `${low} below reorder` : "Materials"} tone={low ? "warn" : "ok"} />
          <Tile to="/maintenance" title="Plant Maintenance" sub="Notifications & work orders" />
          <Tile to="/scada" title="SCADA / HMI" sub="Line 2 process control" />
          <Tile to="/engineering" title="Engineering Station" sub="PLC logic & setpoints" />
          <Tile to="/files" title="Document Share" sub="Policies & projects" />
          <Tile to="/users" title="Users & Roles" sub="Directory" />
        </div>
      </div>
    </div>
  );
}
