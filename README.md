# ArenaPlant — target system for Cyber-Arena

A professional-looking, SAP-style simulated manufacturing company (**Kaveri Process
Industries**, Line 2 beverage filling) that spans **Purdue levels L4 → L0**, carries
**11 switchable breach points**, logs all activity to one evidence schema, and plays
**8 attack / maintenance scenarios** with hidden ground truth.

It is the *target* that the Cyber-Arena multi-agent system is tested against. One platform
tests the whole pipeline: the agents investigate the plant's evidence; Developer Mode
provides the ground truth to score them.

> Deliberately vulnerable. Run only on an isolated machine / internal Docker networks.

## What it simulates

| Purdue | Component | In the UI |
|--------|-----------|-----------|
| L4 Enterprise | ERP (orders, inventory, plant maintenance, users), remote portal, file share | Production Orders, Inventory, Plant Maintenance, Users, Document Share |
| L3 Operations | Historian, MES recipes, engineering workstation | Engineering Station |
| L2 Supervisory | SCADA / HMI with animated P&ID, setpoints, alarms, trends | SCADA / HMI |
| L1 Control | PLC-1 (mixing tank + conveyor, Modbus/TCP), SIS (safety trips) | — |
| L0 Process | Heated mixing-tank physics (temp/pressure/level/conveyor) | live on SCADA |

A real end-to-end flow runs: ERP order → MES recipe → PLC setpoints → physics → historian →
alarms. Background "noise" bots perform routine operator/engineer activity so detection is non-trivial.

## Tech stack
- **Frontend:** React 18 + TypeScript + Tailwind CSS + Vite + Recharts (SAP Fiori-inspired, original branding).
- **Backend:** Python + FastAPI (two apps: plant on `:8000`, Developer Mode on `:8100`), SQLAlchemy.
- **Database:** SQLite by default (zero-setup); set `DATABASE_URL` to use PostgreSQL.
- **Protocol:** hand-written Modbus/TCP server (`:5020`) so every request is access-controlled and logged.
- **Runs on Windows + macOS** via Docker Desktop — no Linux host required.

## Run it

### Docker (recommended)
```bash
docker compose up --build
```
- Plant UI: http://localhost:8080
- Developer Mode: http://localhost:8080/dev  (token `arena-dev-token`)

### Local dev (no Docker)
```bash
# terminal 1 — backend
cd backend && python -m venv .venv && ./.venv/bin/pip install -r requirements.txt && ./.venv/bin/python run.py
```
```bash
# terminal 2 — frontend
cd frontend && npm install && npm run dev
```
- Plant UI: http://localhost:5173  ·  Developer Mode: http://localhost:5173/dev

### CLI
```bash
python arena.py status
python arena.py scenario 5
python arena.py preset poland_2025
python arena.py reset
```

## Demo accounts
| User | Password | Role |
|------|----------|------|
| a.kulkarni | Plan#2025a | Planner |
| p.nair | Oper#2025p | Operator |
| s.iyer | Eng#2025s | Engineer (remote-enabled) |
| r.mehta | Super#2025r | Maintenance supervisor |
| m.rao | Admin#2025m | IT admin |

(Plus the deliberately weak accounts `admin/admin`, `operator/operator`, `vendor.svc`, `eng.svc` — see BREACH_POINTS.md.)

## How Cyber-Arena connects

Two HTTP surfaces, kept separate so the evaluation stays honest:

| Surface | For | Auth | Exposes ground truth? |
|---------|-----|------|-----------------------|
| `/evidence/*` (port 8000) | Blue / Forensics / Critic agents (read-only) | `X-Evidence-Token` | **No** |
| `/dev/*` (port 8100) | Developer Mode + evaluation harness only | `X-Dev-Token` | Yes |

Agents reach the plant through the **Tool Gateway** over the shared `arena-entry`
(attack surface) and `arena-evidence` (read-only) Docker networks. The Developer Mode /
ground-truth surface is **not** on those networks.

### Agent-facing endpoints (read-only)
- `GET /evidence/events?since_id=&source=&host=&event_type=&purdue_level=` — the evidence stream (one schema).
- `GET /evidence/topology` — asset inventory with Purdue levels.
- `GET /evidence/health` — plant status.
- Modbus/TCP on `:5020` — the Red Agent / Tool Gateway can send real protocol requests
  (unit 1 = PLC-1, unit 2 = SIS). Writes are accepted or refused per the current breach-point config.

### Evidence schema (every event)
```
ts, source, host, purdue_level, event_type,
change_type (logic|parameter|safety_interlock|none),
actor, src_ip, dst_ip, protocol, outcome, severity, detail{}
```
`severity` carries the **impact tier** (low/moderate/high/critical) driven by the process
simulator — e.g. a setpoint change that pushes temperature past its range emits a
`range_exceeded` event at `high`; an SIS bypass is `critical`.

## Scenarios (ground truth in Developer Mode)
1 Unauthorized authentication · 2 Suspicious process · 3 Network anomaly ·
4 Unauthorized config change · 5 Lateral movement (L4→L1) · 6 Process manipulation ·
**7 Legitimate maintenance (false-positive twin of 4/6)** · 6c Safety-interlock attack.

Scenario 7 is the mechanical twin of 4/6 — same asset, same register, same change type —
differing only in authorization (approved work order, known engineer). This is the
discrimination the Critic Agent must make.

See **BREACH_POINTS.md** for the full weakness register and **ADDENDUM** mapping.
