// Animated P&ID of the mixing tank + conveyor line, driven by live plant state.
export default function Pid({ s }: { s: any }) {
  if (!s) return null;
  const tag = (k: string) => s.tags.find((t: any) => t.key === k);
  const temp = tag("temperature"), pres = tag("pressure"), lvl = tag("level"), conv = tag("conveyor_speed");
  const level = lvl?.value ?? 0;
  const heaterOn = s.actuators.heater_enable && s.actuators.heater_out > 1;
  const convRun = s.actuators.conveyor_run && (conv?.value ?? 0) > 0.05;
  const pumpRun = s.actuators.pump_run;
  const tripped = s.safety.sis_tripped;
  const col = (t: any) => (t?.state === "trip" ? "#d32f2f" : t?.state === "alarm" || t?.state === "outside_normal" ? "#ed6c02" : "#0a5aad");
  const liquidH = 120 * (level / 100);

  return (
    <svg viewBox="0 0 640 320" className="w-full">
      <defs>
        <linearGradient id="liq" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#f6b24a" /><stop offset="100%" stopColor="#e07b1a" />
        </linearGradient>
      </defs>

      {/* feed pump */}
      <g>
        <rect x="20" y="150" width="60" height="26" rx="4" fill="#fff" stroke="#94a3b8" />
        <text x="50" y="167" textAnchor="middle" className="fill-slate-600" fontSize="10">P-101</text>
        <circle cx="50" cy="140" r="9" fill={pumpRun ? "#2e7d32" : "#cbd5e1"}>
          {pumpRun && <animateTransform attributeName="transform" type="rotate" from="0 50 140" to="360 50 140" dur="1.2s" repeatCount="indefinite" />}
        </circle>
        <line x1="80" y1="163" x2="150" y2="163" stroke="#94a3b8" strokeWidth="6" />
      </g>

      {/* tank */}
      <g>
        <rect x="150" y="60" width="150" height="150" rx="8" fill="#eef2f7" stroke="#64748b" strokeWidth="2" />
        <rect x="152" y={208 - liquidH} width="146" height={liquidH} rx="2" fill="url(#liq)" opacity="0.9" />
        <rect x="152" y={208 - liquidH} width="146" height="4" fill="#fff" opacity="0.4" />
        <text x="225" y="50" textAnchor="middle" className="fill-slate-700" fontSize="12" fontWeight="600">Mixing Tank T-101</text>
        {/* agitator */}
        <line x1="225" y1="60" x2="225" y2="150" stroke="#475569" strokeWidth="3" />
        <g>
          <line x1="205" y1="150" x2="245" y2="150" stroke="#475569" strokeWidth="4" />
          <animateTransform attributeName="transform" type="rotate" from="0 225 150" to="360 225 150" dur="2s" repeatCount="indefinite" />
        </g>
        {/* heater */}
        <rect x="165" y="195" width="120" height="8" rx="3" fill={heaterOn ? "#ff5722" : "#94a3b8"}>
          {heaterOn && <animate attributeName="opacity" values="1;0.5;1" dur="1s" repeatCount="indefinite" />}
        </rect>
        <text x="225" y="225" textAnchor="middle" fontSize="9" className="fill-slate-500">E-101 heater {s.actuators.heater_out?.toFixed(0)}%</text>
      </g>

      {/* instrument badges */}
      <Badge x={330} y={70} label="TT101" value={`${temp?.value ?? "—"} °C`} color={col(temp)} />
      <Badge x={330} y={110} label="PT101" value={`${pres?.value ?? "—"} bar`} color={col(pres)} />
      <Badge x={330} y={150} label="LT101" value={`${lvl?.value ?? "—"} %`} color={col(lvl)} />

      {/* outflow to conveyor */}
      <line x1="300" y1="185" x2="430" y2="185" stroke="#94a3b8" strokeWidth="6" />
      <line x1="430" y1="185" x2="430" y2="245" stroke="#94a3b8" strokeWidth="6" />

      {/* conveyor */}
      <g>
        <rect x="430" y="250" width="180" height="12" rx="6" fill="#475569" />
        <circle cx="440" cy="256" r="10" fill="#64748b" />
        <circle cx="600" cy="256" r="10" fill="#64748b" />
        {convRun && [0, 1, 2, 3].map((i) => (
          <rect key={i} x={445 + i * 40} y="236" width="14" height="18" rx="2" fill="#e07b1a">
            <animate attributeName="x" values={`${445 + i * 40};${445 + i * 40 + 40}`} dur="1.5s" repeatCount="indefinite" />
          </rect>
        ))}
        <text x="520" y="285" textAnchor="middle" fontSize="10" className="fill-slate-600">
          Conveyor CV-201 · {conv?.value?.toFixed(2)} m/s</text>
      </g>

      {/* SIS */}
      <g>
        <rect x="470" y="60" width="150" height="56" rx="6" fill={tripped ? "#fde8e8" : s.safety.sis_bypass ? "#fef3c7" : "#e8f5e9"}
          stroke={tripped ? "#d32f2f" : s.safety.sis_bypass ? "#ed6c02" : "#2e7d32"} strokeWidth="1.5" />
        <text x="545" y="80" textAnchor="middle" fontSize="11" fontWeight="700"
          fill={tripped ? "#d32f2f" : s.safety.sis_bypass ? "#ed6c02" : "#2e7d32"}>
          SIS {tripped ? "TRIPPED" : s.safety.sis_bypass ? "BYPASSED" : "ARMED"}</text>
        <text x="545" y="98" textAnchor="middle" fontSize="9" className="fill-slate-500">Trip: {s.safety.trip_temp_limit}°C / {s.safety.trip_pressure_limit} bar</text>
        <text x="545" y="110" textAnchor="middle" fontSize="8" className="fill-slate-400">Safety Instrumented System</text>
      </g>
    </svg>
  );
}

function Badge({ x, y, label, value, color }: { x: number; y: number; label: string; value: string; color: string }) {
  return (
    <g>
      <circle cx={x} cy={y} r="15" fill="#fff" stroke={color} strokeWidth="2" />
      <text x={x} y={y + 3} textAnchor="middle" fontSize="8" fill={color} fontWeight="700">{label}</text>
      <text x={x + 22} y={y + 4} fontSize="12" fill={color} fontWeight="600">{value}</text>
    </g>
  );
}
