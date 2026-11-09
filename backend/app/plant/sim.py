"""Level 0-1: physical process, PLC-1 control logic and the safety instrumented system.

Process: a heated mixing tank (temperature / pressure / level) feeding a bottling
conveyor. PLC-1 runs a PI temperature loop, level control for the feed pump and
the conveyor drive. The SIS independently trips the heater and conveyor on high
temperature or pressure unless its bypass bit is set.
"""
from __future__ import annotations

import hashlib
import random
import re
import threading
import time

from .. import flags
from ..events import emit
from ..maintenance import active_window
from ..topology import classify_ip

# ----------------------------------------------------------------------------- ranges
# normal band, alarm (high) limit, trip limit. Used for alarms + impact severity.
RANGES = {
    "temperature": {"unit": "°C", "normal": (60.0, 80.0), "alarm_hi": 85.0, "trip_hi": 95.0, "alarm_lo": 50.0},
    "pressure": {"unit": "bar", "normal": (1.6, 2.4), "alarm_hi": 2.5, "trip_hi": 2.8, "alarm_lo": 1.2},
    "level": {"unit": "%", "normal": (30.0, 85.0), "alarm_hi": 90.0, "trip_hi": None, "alarm_lo": 20.0},
    "conveyor_speed": {"unit": "m/s", "normal": (0.8, 1.2), "alarm_hi": 1.5, "trip_hi": None, "alarm_lo": None},
    "motor_current": {"unit": "A", "normal": (0.0, 12.0), "alarm_hi": 13.5, "trip_hi": None, "alarm_lo": None},
}

# Engineering limits enforced by the PLC when B9 is patched.
ENGINEERING_LIMITS = {"temp_sp": (40.0, 85.0), "conveyor_sp": (0.0, 1.4), "pump_speed_sp": (0.0, 100.0)}

# ----------------------------------------------------------------------------- register map
HR = {  # unit 1 holding registers (read/write)
    0: ("temp_sp", 10.0),
    1: ("conveyor_sp", 100.0),
    2: ("pump_speed_sp", 1.0),
    3: ("auto_mode", 1.0),
}
IR = {  # unit 1 input registers (read only)
    0: ("temperature", 10.0),
    1: ("pressure", 100.0),
    2: ("level", 10.0),
    3: ("conveyor_speed", 100.0),
    4: ("motor_current", 10.0),
    5: ("bottles_lo", 1.0),
    6: ("bottles_hi", 1.0),
    7: ("heater_out", 1.0),
    8: ("rejects", 1.0),
    9: ("program_version", 1.0),
}
COILS = {0: "heater_enable", 1: "pump_run", 2: "conveyor_run", 3: "alarm_reset"}
SIS_COILS = {0: "sis_bypass", 1: "sis_reset"}
SIS_IR = {0: ("sis_tripped", 1.0), 1: ("sis_bypass", 1.0), 2: ("trip_temp_limit", 10.0), 3: ("trip_pressure_limit", 100.0)}

DEFAULT_PROGRAM = """PROGRAM MixTankControl
(* PLC-1  -  Heated mixing tank + bottling conveyor
   Line 2, ArenaPlant Pune. Maintained by Process Engineering. *)
VAR CONSTANT
    TEMP_SP_MAX       : REAL := 85.0;   (* clamp for temperature setpoint, degC *)
    HEATER_GAIN       : REAL := 0.08;   (* PI proportional gain *)
    HIGH_TEMP_CUTOUT  : REAL := 90.0;   (* software heater cut-out, degC *)
    CONVEYOR_MAX      : REAL := 1.4;    (* m/s *)
    LEVEL_LOW_STOP    : BOOL := TRUE;   (* stop conveyor below 15 % level *)
    PUMP_START_LEVEL  : REAL := 55.0;
    PUMP_STOP_LEVEL   : REAL := 70.0;
END_VAR

(* Temperature loop *)
TempPI(SP := MIN(TempSP, TEMP_SP_MAX), PV := TT101, KP := HEATER_GAIN);
HeaterOut := SEL(TT101 > HIGH_TEMP_CUTOUT, TempPI.OUT, 0.0);

(* Level control *)
IF LT101 < PUMP_START_LEVEL THEN P101 := TRUE; END_IF;
IF LT101 > PUMP_STOP_LEVEL THEN P101 := FALSE; END_IF;

(* Conveyor *)
ConvRef := MIN(ConvSP, CONVEYOR_MAX);
IF LEVEL_LOW_STOP AND LT101 < 15.0 THEN ConvRun := FALSE; END_IF;
END_PROGRAM
"""

_PARAM_RE = re.compile(r"^\s*([A-Z_][A-Z0-9_]*)\s*:\s*(REAL|BOOL|INT)\s*:=\s*([^;]+);", re.M)


def parse_program(source: str) -> dict:
    out = {}
    for name, typ, raw in _PARAM_RE.findall(source):
        raw = raw.strip()
        if typ == "BOOL":
            out[name] = raw.upper() == "TRUE"
        else:
            try:
                out[name] = float(raw)
            except ValueError:
                pass
    return out


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class Plant:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.speed = 1.0
        self.reset()

    # ------------------------------------------------------------------ state
    def reset(self) -> None:
        with getattr(self, "lock", threading.RLock()):
            self.s = {
                "temperature": 71.5, "pressure": 2.1, "level": 62.0, "conveyor_speed": 1.0,
                "motor_current": 10.0, "heater_out": 48.0, "bottles": 0, "rejects": 0,
                "temp_sp": 72.0, "conveyor_sp": 1.0, "pump_speed_sp": 60.0, "auto_mode": 1.0,
                "heater_enable": True, "pump_run": True, "conveyor_run": True, "alarm_reset": False,
                "sis_tripped": False, "sis_bypass": False, "trip_temp_limit": 95.0, "trip_pressure_limit": 2.8,
                "program_version": 1,
            }
            self.integ = 48.0
            self._bottle_frac = 0.0
            self.program_source = DEFAULT_PROGRAM
            self.params = parse_program(DEFAULT_PROGRAM)
            self.program_sha = sha256(DEFAULT_PROGRAM)
            self.tag_state = {t: "normal" for t in RANGES}
            self._fw_seen: dict = {}
            self._read_seen: dict = {}
            self.fault: dict | None = None  # injected sensor fault (non-attack anomaly)
            self.on_bottles = None  # callback(n) set by MES

    def snapshot(self) -> dict:
        with self.lock:
            d = dict(self.s)
            d["program_sha"] = self.program_sha
            d["params"] = dict(self.params)
            d["fault"] = self.fault
            d["speed"] = self.speed
            return d

    # ------------------------------------------------------------------ physics + logic
    def tick(self, dt_wall: float) -> None:
        dt = dt_wall * self.speed
        with self.lock:
            s, p = self.s, self.params
            # --- PLC-1 temperature PI loop
            sp = min(s["temp_sp"], p.get("TEMP_SP_MAX", 85.0))
            err = sp - s["temperature"]
            kp = 12.0 * p.get("HEATER_GAIN", 0.08) / 0.08
            self.integ = max(0.0, min(100.0, self.integ + err * 0.5 * dt))
            out = max(0.0, min(100.0, kp * err + self.integ))
            if s["temperature"] > p.get("HIGH_TEMP_CUTOUT", 90.0):
                out = 0.0
            if not s["heater_enable"] or (s["sis_tripped"] and not s["sis_bypass"]):
                out = 0.0
            s["heater_out"] = out
            s["temperature"] += (out / 100.0 * 1.2 - 0.012 * (s["temperature"] - 22.0)) * dt
            s["temperature"] += random.gauss(0, 0.03)

            # --- level control (feed pump) + draw-off by filling
            if s["auto_mode"] >= 1:
                if s["level"] < p.get("PUMP_START_LEVEL", 55.0):
                    s["pump_run"] = True
                elif s["level"] > p.get("PUMP_STOP_LEVEL", 70.0):
                    s["pump_run"] = False
            inflow = (s["pump_speed_sp"] / 100.0) * 0.9 if s["pump_run"] else 0.0
            running = s["conveyor_run"] and not (s["sis_tripped"] and not s["sis_bypass"])
            if p.get("LEVEL_LOW_STOP", True) and s["level"] < 15.0:
                running = False
            outflow = s["conveyor_speed"] * 0.35 if running else 0.0
            s["level"] = max(0.0, min(100.0, s["level"] + (inflow - outflow) * dt))

            # --- pressure follows temperature and level
            s["pressure"] = 1.0 + max(0.0, s["temperature"] - 20.0) * 0.02 + s["level"] * 0.002 + random.gauss(0, 0.005)

            # --- conveyor drive
            ref = min(s["conveyor_sp"], p.get("CONVEYOR_MAX", 1.4)) if running else 0.0
            s["conveyor_speed"] += (ref - s["conveyor_speed"]) * min(1.0, dt / 3.0)
            s["motor_current"] = (4.0 + s["conveyor_speed"] * 6.0 + random.gauss(0, 0.05)) if running else 0.3

            # --- production
            produced = 0
            if running and s["level"] > 10:
                self._bottle_frac += s["conveyor_speed"] * 2.5 * dt
                produced = int(self._bottle_frac)
                self._bottle_frac -= produced
                s["bottles"] += produced
                if not (65.0 <= s["temperature"] <= 82.0):
                    s["rejects"] += produced

            # --- sensor fault injection (affects what the PLC *reports*, not the physics)
            # handled in reported_value()

            # --- SIS
            if not s["sis_tripped"] and not s["sis_bypass"]:
                if s["temperature"] >= s["trip_temp_limit"] or s["pressure"] >= s["trip_pressure_limit"]:
                    s["sis_tripped"] = True
                    cause = "high temperature" if s["temperature"] >= s["trip_temp_limit"] else "high pressure"
                    emit(source="plc", host="sis-01", event_type="sis_trip", change_type="none", outcome="info",
                         severity="high", cause=cause, temperature=round(s["temperature"], 2),
                         pressure=round(s["pressure"], 3))
            snapshot = {k: s[k] for k in RANGES}
        if produced and self.on_bottles:
            try:
                self.on_bottles(produced)
            except Exception:
                pass
        self._check_ranges(snapshot)

    def reported_value(self, tag: str) -> float:
        v = self.s[tag]
        if self.fault and self.fault.get("tag") == tag:
            if self.fault["kind"] == "stuck":
                return self.fault["value"]
            if self.fault["kind"] == "drift":
                return v + self.fault["value"]
        return v

    # ------------------------------------------------------------------ alarms / impact
    def _check_ranges(self, snap: dict) -> None:
        from ..alarms import raise_alarm, clear_alarm

        for tag, v in snap.items():
            r = RANGES[tag]
            lo, hi = r["normal"]
            state = "normal"
            if r.get("trip_hi") is not None and v >= r["trip_hi"]:
                state = "trip"
            elif r.get("alarm_hi") is not None and v >= r["alarm_hi"]:
                state = "alarm"
            elif r.get("alarm_lo") is not None and v <= r["alarm_lo"]:
                state = "alarm"
            elif v > hi + 0.0001 or v < lo - 0.0001:
                state = "outside_normal"
            prev = self.tag_state.get(tag, "normal")
            order = ["normal", "outside_normal", "alarm", "trip"]
            if order.index(state) > order.index(prev):
                emit(source="process", host="process", event_type="range_exceeded", outcome="info",
                     severity="high", tag=tag, value=round(v, 3), unit=r["unit"], state=state,
                     normal_low=lo, normal_high=hi)
                if state in ("alarm", "trip"):
                    raise_alarm(tag, "trip" if state == "trip" else "high", v, r)
            elif state == "normal" and prev != "normal":
                emit(source="process", host="process", event_type="range_restored", outcome="info",
                     severity="info", tag=tag, value=round(v, 3), unit=r["unit"])
                clear_alarm(tag)
            self.tag_state[tag] = state

    # ------------------------------------------------------------------ access control
    def _firewall(self, src: dict, ctx: dict, dst_host: str, port: int = 502) -> tuple[bool, str]:
        """fw-02 policy for traffic into the control zone. Returns (allowed, reason)."""
        if src["host"] in ("hmi-01", "plc-01", "sis-01"):
            return True, "same zone"
        if flags.vulnerable("B8"):
            allowed, reason = True, "rule 140 'TEMP vendor access - any to control:502'"
        elif src["host"] == "eng-ws-01" and active_window(dst_host):
            allowed, reason = True, "rule 20 'eng-ws to control during approved window'"
        else:
            allowed, reason = False, "default deny"
        key = (src.get("ip"), dst_host, port, allowed)
        now = time.monotonic()
        if now - self._fw_seen.get(key, 0) > 30 or ctx.get("force_fw_log"):
            self._fw_seen[key] = now
            emit(source="network", host="fw-02", event_type="network_connection", protocol="modbus/tcp",
                 src_ip=src.get("ip"), dst_ip=_ip(dst_host),
                 outcome="success" if allowed else "blocked", severity="info" if allowed else "low",
                 actor=ctx.get("actor"), dst_port=port, src_host=src["host"], src_zone=src["zone"],
                 dst_host=dst_host, rule=reason)
        return allowed, reason

    # ------------------------------------------------------------------ reads
    def read(self, unit: int, table: str, addr: int, count: int, ctx: dict) -> list[int] | None:
        src = classify_ip(ctx.get("src_ip"))
        dst = "plc-01" if unit == 1 else "sis-01"
        ok, _ = self._firewall(src, ctx, dst)
        if not ok:
            return None
        key = (src.get("ip"), dst)
        now = time.monotonic()
        if now - self._read_seen.get(key, 0) > 60:
            self._read_seen[key] = now
            emit(source="plc", host=dst, event_type="modbus_read", protocol="modbus/tcp", actor=ctx.get("actor"),
                 src_ip=src.get("ip"), outcome="success", unit=unit, table=table, address=addr, count=count,
                 src_host=src["host"], note="first read from this client in 60 s")
        with self.lock:
            vals = []
            for a in range(addr, addr + count):
                vals.append(self._get(unit, table, a))
            return vals

    def _get(self, unit: int, table: str, a: int) -> int:
        s = self.s
        if unit == 1:
            if table == "hr" and a in HR:
                tag, scale = HR[a]
                return int(round(s[tag] * scale)) & 0xFFFF
            if table == "ir" and a in IR:
                tag, scale = IR[a]
                if tag == "bottles_lo":
                    return s["bottles"] & 0xFFFF
                if tag == "bottles_hi":
                    return (s["bottles"] >> 16) & 0xFFFF
                val = self.reported_value(tag) if tag in RANGES else s[tag]
                return int(round(val * scale)) & 0xFFFF
            if table == "coil" and a in COILS:
                return 1 if s[COILS[a]] else 0
        else:
            if table == "coil" and a in SIS_COILS:
                return 1 if s.get(SIS_COILS[a], False) else 0
            if table in ("ir", "hr") and a in SIS_IR:
                tag, scale = SIS_IR[a]
                return int(round(float(s[tag]) * scale)) & 0xFFFF
        return 0

    # ------------------------------------------------------------------ writes
    def write(self, unit: int, table: str, addr: int, values: list[int], ctx: dict) -> tuple[bool, str]:
        """Single entry point for every write: HMI, engineering tools, historian
        diagnostics, scenario engine and real Modbus/TCP clients all land here."""
        src = classify_ip(ctx.get("src_ip"))
        dst = "plc-01" if unit == 1 else "sis-01"
        actor = ctx.get("actor")
        proto = ctx.get("protocol", "modbus/tcp")
        fc = ctx.get("function_code", 6 if table == "hr" else 5)

        ok, reason = self._firewall(src, ctx, dst)
        if not ok:
            return False, f"connection refused by fw-02 ({reason})"

        results = []
        for i, raw in enumerate(values):
            a = addr + i
            results.append(self._write_one(unit, table, a, raw, src, actor, proto, fc, ctx))
        bad = [r for r in results if not r[0]]
        if bad:
            return False, bad[0][1]
        return True, "ok"

    def _write_one(self, unit, table, a, raw, src, actor, proto, fc, ctx) -> tuple[bool, str]:
        s = self.s
        host = "plc-01" if unit == 1 else "sis-01"
        common = dict(source="plc", host=host, protocol=proto, actor=actor, src_ip=src.get("ip"),
                      unit=unit, function_code=fc, address=a, src_host=src["host"])

        # ---- SIS (unit 2)
        if unit == 2:
            if table != "coil" or a not in SIS_COILS:
                emit(event_type="modbus_write", change_type="none", outcome="failure", severity="low",
                     error="illegal data address", **common)
                return False, "illegal data address"
            tag = SIS_COILS[a]
            val = bool(raw)
            if tag == "sis_bypass":
                if not flags.vulnerable("B11") and not ctx.get("key_switch"):
                    emit(event_type="modbus_write", change_type="safety_interlock", outcome="blocked", severity="high",
                         tag=tag, requested=val, error="bypass only via local key switch", **common)
                    return False, "SIS bypass is key-switch only"
                with self.lock:
                    old = s["sis_bypass"]
                    s["sis_bypass"] = val
                emit(event_type="sis_bypass_change", change_type="safety_interlock", outcome="success",
                     severity="critical" if val else "moderate", tag=tag, old=old, new=val,
                     via="key switch" if ctx.get("key_switch") else "network", **common)
                return True, "ok"
            if tag == "sis_reset" and val:
                with self.lock:
                    was = s["sis_tripped"]
                    cond_ok = s["temperature"] < s["trip_temp_limit"] - 3 and s["pressure"] < s["trip_pressure_limit"] - 0.1
                    if was and cond_ok:
                        s["sis_tripped"] = False
                emit(event_type="sis_reset", change_type="none", outcome="success" if (was and cond_ok) else "failure",
                     severity="info", tag=tag, was_tripped=was, conditions_clear=cond_ok, **common)
                return True, "ok"
            return True, "ok"

        # ---- PLC-1 coils
        if table == "coil":
            if a not in COILS:
                emit(event_type="modbus_write", change_type="none", outcome="failure", severity="low",
                     error="illegal data address", **common)
                return False, "illegal data address"
            tag = COILS[a]
            val = bool(raw)
            with self.lock:
                old = s[tag]
                s[tag] = val
                if tag == "alarm_reset":
                    s[tag] = False
            emit(event_type="modbus_write", change_type="none", outcome="success", severity="info",
                 tag=tag, old=old, new=val, **common)
            return True, "ok"

        # ---- PLC-1 holding registers (setpoints)
        if a not in HR:
            emit(event_type="modbus_write", change_type="none", outcome="failure", severity="low",
                 error="illegal data address", **common)
            return False, "illegal data address"
        tag, scale = HR[a]
        value = (raw if raw < 0x8000 else raw - 0x10000) / scale
        old = s[tag]
        if not flags.vulnerable("B9"):
            lim = ENGINEERING_LIMITS.get(tag)
            if lim and not (lim[0] <= value <= lim[1]):
                emit(event_type="setpoint_change", change_type="parameter", outcome="blocked", severity="moderate",
                     tag=tag, old=round(old, 3), requested=round(value, 3), limit=list(lim),
                     error="outside engineering limits", **common)
                return False, f"{tag} outside engineering limits {lim}"
            if src["host"] != "hmi-01" and not active_window(host, "parameter"):
                emit(event_type="setpoint_change", change_type="parameter", outcome="blocked", severity="moderate",
                     tag=tag, old=round(old, 3), requested=round(value, 3),
                     error="no approved parameter work order for this asset", **common)
                return False, "write requires an approved parameter work order"
        with self.lock:
            s[tag] = value
        lo, hi = ENGINEERING_LIMITS.get(tag, (None, None))
        emit(event_type="setpoint_change", change_type="parameter", outcome="success",
             severity="info", tag=tag, old=round(old, 3), new=round(value, 3),
             within_engineering_limits=(lo is None or lo <= value <= hi), **common)
        return True, "ok"

    # ------------------------------------------------------------------ logic download
    def download_program(self, source: str, ctx: dict) -> tuple[bool, str]:
        src = classify_ip(ctx.get("src_ip"))
        ok, reason = self._firewall(src, ctx, "plc-01", port=44818)
        if not ok:
            return False, f"connection refused by fw-02 ({reason})"
        new_sha = sha256(source)
        base = dict(source="plc", host="plc-01", protocol="eng-download", actor=ctx.get("actor"),
                    src_ip=src.get("ip"), src_host=src["host"])
        if not flags.vulnerable("B7") and not active_window("plc-01", "logic"):
            emit(event_type="program_download", change_type="logic", outcome="blocked", severity="moderate",
                 old_sha256=self.program_sha, new_sha256=new_sha,
                 error="download refused: no approved logic-change work order window", **base)
            return False, "PLC refused download: no approved logic-change window"
        new_params = parse_program(source)
        changed = {k: {"old": self.params.get(k), "new": v} for k, v in new_params.items() if self.params.get(k) != v}
        with self.lock:
            old_sha = self.program_sha
            self.program_source = source
            self.params = {**self.params, **new_params}
            self.program_sha = new_sha
            self.s["program_version"] += 1
            version = self.s["program_version"]
        emit(event_type="program_download", change_type="logic", outcome="success", severity="info",
             old_sha256=old_sha, new_sha256=new_sha, version=version, changed_parameters=changed,
             comment=ctx.get("comment", ""), **base)
        return True, f"program v{version} running"

    def upload_program(self, ctx: dict) -> tuple[bool, str]:
        src = classify_ip(ctx.get("src_ip"))
        ok, reason = self._firewall(src, ctx, "plc-01", port=44818)
        if not ok:
            return False, f"connection refused by fw-02 ({reason})"
        emit(source="plc", host="plc-01", event_type="program_upload", change_type="none", protocol="eng-download",
             actor=ctx.get("actor"), src_ip=src.get("ip"), src_host=src["host"], sha256=self.program_sha)
        return True, self.program_source


def _ip(host: str) -> str:
    from ..topology import BY_HOST
    return BY_HOST.get(host, {}).get("ip", "-")


plant = Plant()
