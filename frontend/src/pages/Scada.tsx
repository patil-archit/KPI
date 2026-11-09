import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, ReferenceLine } from "recharts";
import { api } from "../lib/api";
import { useApi } from "../lib/hooks";
import { useAuth } from "../lib/auth";
import { Pill, useToast } from "../lib/ui";
import Pid from "../components/Pid";

export default function Scada() {
  const toast = useToast();
  const { user } = useAuth();
  const { data: s, reload } = useApi<any>(() => api.get("/api/plant/state"), [], 1500);
  const canControl = ["operator", "supervisor", "engineer", "admin"].includes(user?.role || "");
  const [trendTag, setTrendTag] = useState("temperature");
  const trend = useApi<any>(() => api.get(`/api/historian/trend?tag=${trendTag}&minutes=15`), [trendTag], 3000);

  const setpoint = async (tag: string, value: number) => {
    try { await api.post("/api/hmi/setpoint", { tag, value }); reload(true); }
    catch (e: any) { toast(e.message, "err"); }
  };
  const coil = async (c: string, on: boolean) => {
    try { await api.post("/api/hmi/coil", { coil: c, on }); reload(true); }
    catch (e: any) { toast(e.message, "err"); }
  };
  const ack = async (id: number) => { try { await api.post(`/api/hmi/alarms/${id}/ack`); reload(true); } catch (e: any) { toast(e.message, "err"); } };

  if (!s) return null;
  const sp = s.setpoints;
  const pts = (trend.data?.points || []).map((p: any) => ({ t: new Date(p.ts).toLocaleTimeString().slice(0, 5), v: p.v }));

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">SCADA · Line 2</h1>
          <p className="text-sm text-slate-500">HMI-01 · Supervisory control (Purdue L2)</p>
        </div>
        <div className="flex items-center gap-2">
          <Pill tone={s.safety.sis_tripped ? "high" : "ok"}>{s.safety.sis_tripped ? "SIS TRIPPED" : "Running"}</Pill>
          <Pill tone="slate">Logic v{s.program.version}</Pill>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        {/* P&ID */}
        <div className="lg:col-span-2 card p-3">
          <div className="card-t px-1 pb-2">Process overview</div>
          <Pid s={s} />
        </div>

        {/* setpoints + actuators */}
        <div className="space-y-4">
          <div className="card">
            <div className="card-h"><span className="card-t">Setpoints</span></div>
            <div className="p-4 space-y-4">
              <Sp label="Temperature" unit="°C" value={sp.temp_sp} min={40} max={85} step={0.5}
                onSet={(v: number) => setpoint("temp_sp", v)} disabled={!canControl} />
              <Sp label="Conveyor speed" unit="m/s" value={sp.conveyor_sp} min={0} max={1.4} step={0.05}
                onSet={(v: number) => setpoint("conveyor_sp", v)} disabled={!canControl} />
              <Sp label="Pump speed" unit="%" value={sp.pump_speed_sp} min={0} max={100} step={5}
                onSet={(v: number) => setpoint("pump_speed_sp", v)} disabled={!canControl} />
            </div>
          </div>
          <div className="card">
            <div className="card-h"><span className="card-t">Actuators</span></div>
            <div className="p-4 grid grid-cols-3 gap-2">
              {[["heater_enable", "Heater", s.actuators.heater_enable],
                ["pump_run", "Pump", s.actuators.pump_run],
                ["conveyor_run", "Conveyor", s.actuators.conveyor_run]].map(([k, l, on]: any) => (
                <button key={k} disabled={!canControl} onClick={() => coil(k, !on)}
                  className={`py-2 rounded text-xs font-medium border ${on ? "bg-green-50 border-green-400 text-green-700" : "bg-slate-50 border-slate-300 text-slate-500"} disabled:opacity-50`}>
                  {l}<br /><span className="text-[10px]">{on ? "ON" : "OFF"}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* trend + alarms */}
      <div className="grid lg:grid-cols-3 gap-4 mt-4">
        <div className="lg:col-span-2 card">
          <div className="card-h">
            <span className="card-t">Historian trend</span>
            <select className="input w-40 py-1" value={trendTag} onChange={(e) => setTrendTag(e.target.value)}>
              {s.tags.map((t: any) => <option key={t.key} value={t.key}>{t.label}</option>)}
            </select>
          </div>
          <div className="p-3 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={pts}>
                <XAxis dataKey="t" fontSize={10} stroke="#94a3b8" minTickGap={30} />
                <YAxis fontSize={10} stroke="#94a3b8" domain={["auto", "auto"]} width={38} />
                <Tooltip />
                {(() => { const t = s.tags.find((x: any) => x.key === trendTag);
                  return <>
                    {t?.alarm_hi && <ReferenceLine y={t.alarm_hi} stroke="#ed6c02" strokeDasharray="4 4" />}
                    {t?.trip_hi && <ReferenceLine y={t.trip_hi} stroke="#d32f2f" strokeDasharray="4 4" />}
                  </>; })()}
                <Line type="monotone" dataKey="v" stroke="#0a5aad" strokeWidth={2} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-h"><span className="card-t">Active alarms</span>
            <Pill tone={s.alarms.length ? "warn" : "ok"}>{s.alarms.length}</Pill></div>
          <div className="divide-y divide-slate-100 max-h-56 overflow-auto">
            {s.alarms.length === 0 && <div className="p-4 text-sm text-slate-400">No active alarms</div>}
            {s.alarms.map((a: any) => (
              <div key={a.id} className="p-3 flex items-start gap-2">
                <span className={`mt-1 w-2 h-2 rounded-full ${a.level === "trip" ? "bg-status-high" : "bg-status-warn"}`} />
                <div className="flex-1">
                  <div className="text-sm text-slate-700">{a.message}</div>
                  <div className="text-[11px] text-slate-400">{new Date(a.ts).toLocaleTimeString()}{a.acked_by && ` · ack ${a.acked_by}`}</div>
                </div>
                {!a.acked_by && canControl && <button className="btn-soft py-1 text-xs" onClick={() => ack(a.id)}>Ack</button>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Sp({ label, unit, value, min, max, step, onSet, disabled }: any) {
  const [v, setV] = useState(value);
  // keep local in sync when not editing
  return (
    <div>
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-600">{label}</span>
        <span className="text-sm font-semibold tabular-nums text-brand-700">{value} {unit}</span>
      </div>
      <div className="flex items-center gap-2 mt-1">
        <input type="range" min={min} max={max} step={step} defaultValue={value}
          onChange={(e) => setV(+e.target.value)} disabled={disabled}
          className="flex-1 accent-brand-600" />
        <button className="btn-soft py-1 text-xs" disabled={disabled} onClick={() => onSet(v)}>Set {v}</button>
      </div>
    </div>
  );
}
