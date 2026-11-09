"""Scenario engine: the seven templates and their maintenance twins.

Each scenario runs as a short sequence of steps through the SAME entry points an
operator, engineer or attacker would use, so the evidence it leaves is
indistinguishable in form from organic activity. Ground truth (what really
happened) is recorded on the Case row and only ever served by the Developer Mode
API - never by /evidence.

Scenario 7 is a deliberate mechanical twin of Scenario 4: same asset, same
change type, same register. It differs only in authorization context (an approved
maintenance work order and a known engineer), which is exactly the discrimination
the Cyber-Arena Critic Agent must make.
"""
from __future__ import annotations

import secrets
import threading
import time
from datetime import timedelta

from . import auth, flags
from .db import session_scope
from .events import capture, emit
from .models import Case, WorkOrder, utcnow
from .plant.sim import DEFAULT_PROGRAM, plant
from .topology import EXTERNAL_IPS, ip_of

_lock = threading.Lock()
_running: dict | None = None


SCENARIOS = {
    "1": {"name": "Unauthorized authentication", "is_attack": True,
          "techniques": ["T0886 Remote Services", "T0859 Valid Accounts"],
          "purdue_path": ["L4/L3", "L2"], "needs": ["B1"],
          "summary": "Remote login into the OT side using reused vendor credentials, without MFA."},
    "2": {"name": "Suspicious process / engineering access", "is_attack": True,
          "techniques": ["T0853 Scripting", "T0843 Program Download"],
          "purdue_path": ["L3", "L2"], "needs": ["B6"],
          "summary": "Credentials read from an engineering project file and used to connect to the controller."},
    "3": {"name": "Network anomaly (IT-OT pivot)", "is_attack": True,
          "techniques": ["T0840 Network Connection Enumeration"],
          "purdue_path": ["L4", "L3", "L2"], "needs": ["B5", "B8"],
          "summary": "Pivot from the office network through the dual-homed historian toward the control zone."},
    "4": {"name": "Unauthorized configuration change", "is_attack": True,
          "techniques": ["T0889 Modify Program", "T0821 Modify Controller Tasking"],
          "purdue_path": ["L2", "L1"], "needs": ["B7"],
          "summary": "Unapproved PLC logic download altering a control constant."},
    "5": {"name": "Lateral movement (IT to control)", "is_attack": True,
          "techniques": ["T0859 Valid Accounts", "T0886 Remote Services"],
          "purdue_path": ["L4", "L3", "L2", "L1"], "needs": ["B1", "B5", "B8", "B9"],
          "summary": "Full traversal from remote access down to a control-network write."},
    "6": {"name": "Process manipulation", "is_attack": True,
          "techniques": ["T0836 Modify Parameter", "T0831 Manipulation of Control"],
          "purdue_path": ["L1", "L0"], "needs": ["B9"],
          "summary": "Direct setpoint write driving a process value out of its normal range."},
    "7": {"name": "Legitimate maintenance (false positive)", "is_attack": False,
          "techniques": [], "purdue_path": ["L3", "L2"], "needs": [],
          "summary": "A scheduled parameter change by a known engineer under an approved work order - the twin of Scenario 4/6."},
    "6c": {"name": "Safety interlock attack", "is_attack": True,
           "techniques": ["T0831 Manipulation of Control", "T0880 Loss of Safety"],
           "purdue_path": ["L2", "L1"], "needs": ["B11"],
           "summary": "Safety-trip bypass set over the network, then the process pushed past its trip limit."},
}


def catalogue() -> list[dict]:
    out = []
    for key, sc in SCENARIOS.items():
        missing = [b for b in sc["needs"] if not flags.vulnerable(b)]
        out.append({"key": key, "name": sc["name"], "is_attack": sc["is_attack"],
                    "techniques": sc["techniques"], "purdue_path": sc["purdue_path"],
                    "summary": sc["summary"], "requires": sc["needs"], "blocked_by_patched": missing,
                    "runnable": not missing})
    return out


def status() -> dict | None:
    with _lock:
        return dict(_running) if _running else None


def _ext_ip(seed: str) -> str:
    return EXTERNAL_IPS[sum(map(ord, seed)) % len(EXTERNAL_IPS)]


def _slow(fast: bool, seconds: float):
    time.sleep(0.05 if fast else seconds)


def run(key: str, *, fast: bool = True, actor: str = "attacker") -> dict:
    global _running
    sc = SCENARIOS.get(key)
    if not sc:
        raise ValueError("unknown scenario")
    with _lock:
        if _running:
            raise RuntimeError("a scenario is already running")
        _running = {"key": key, "name": sc["name"], "started": utcnow().isoformat(), "steps": []}

    steps: list[dict] = []
    captured: list[int] = []
    token = capture.set(captured)
    try:
        runner = _RUNNERS[key]
        runner(steps, fast, actor)
    finally:
        capture.reset(token)

    with session_scope() as s:
        case_key = f"{key}-{int(time.time())}-{secrets.token_hex(2)}"
        first = min(captured) if captured else None
        last = max(captured) if captured else None
        case = Case(case_key=case_key, scenario=key, variant="attack" if sc["is_attack"] else "maintenance",
                    is_attack=sc["is_attack"], status="finished", finished_at=utcnow(),
                    first_event_id=first, last_event_id=last, flags_snapshot=flags.snapshot(),
                    ground_truth={"scenario": key, "name": sc["name"], "is_attack": sc["is_attack"],
                                  "techniques": sc["techniques"], "purdue_path": sc["purdue_path"],
                                  "steps": steps, "event_ids": captured})
        s.add(case)
        s.flush()
        cid = case.id
    with _lock:
        _running = None
    return {"case_key": case_key, "case_id": cid, "scenario": key, "is_attack": sc["is_attack"],
            "events_generated": len(captured), "steps": steps}


def _step(steps, text, **extra):
    steps.append({"t": utcnow().isoformat(), "action": text, **extra})


# --------------------------------------------------------------------- runners
def _s1(steps, fast, actor):
    ip = _ext_ip("vendor.svc")
    emit(source="network", host="portal-01", event_type="port_scan", src_ip=ip, protocol="tcp",
         outcome="info", severity="low", ports=[443], note="probe of remote access portal")
    _step(steps, "Recon against the remote access portal", host="portal-01", src_ip=ip)
    _slow(fast, 1)
    try:
        auth.login("vendor.svc", "Vend0r@2024", "remote", "0.0.0.0", src_ip_override=ip)
        _step(steps, "Remote login as vendor.svc without MFA", host="portal-01", src_ip=ip,
              technique="T0886", purdue="L4->L3")
    except Exception as e:
        _step(steps, f"Login attempt failed: {e}", host="portal-01", src_ip=ip)


def _s2(steps, fast, actor):
    emit(source="host", host="eng-ws-01", event_type="file_read", actor="eng.svc", src_ip=ip_of("eng-ws-01"),
         protocol="ssh", path="/Projects/Line2_MixTank/project_config.ini", note="credentials file accessed")
    _step(steps, "Read engineering project config containing plain-text PLC credentials", host="eng-ws-01",
          technique="T0853")
    _slow(fast, 1)
    emit(source="host", host="eng-ws-01", event_type="process_exec", actor="eng.svc", src_ip=ip_of("eng-ws-01"),
         protocol=None, outcome="success", severity="low", process="python plc_connect.py",
         note="unexpected engineering script execution")
    _step(steps, "Unauthorized engineering script connects to the controller", host="eng-ws-01")


def _s3(steps, fast, actor):
    office = "10.40.1.80"
    emit(source="auth", host="historian-01", event_type="login_success", actor="historian.local", src_ip=office,
         protocol="https", method="historian-local", note="default local login from office LAN side")
    _step(steps, "Reach dual-homed historian from the office network and log in locally", host="historian-01",
          src_ip=office, technique="T0840", purdue="L4->L3")
    _slow(fast, 1)
    for dst in ("plc-01",):
        plant.read(1, "ir", 0, 5, {"src_ip": ip_of("historian-01"), "actor": "historian.local",
                   "protocol": "modbus/tcp", "force_fw_log": True})
    emit(source="network", host="fw-02", event_type="network_enumeration", src_ip=ip_of("historian-01"),
         protocol="modbus/tcp", outcome="info", severity="moderate", note="scan of control subnet from historian")
    _step(steps, "Enumerate the control subnet from the historian", host="historian-01", purdue="L3->L2")


def _s4(steps, fast, actor, approved=False):
    src = ip_of("eng-ws-01")
    modified = DEFAULT_PROGRAM.replace("HEATER_GAIN       : REAL := 0.08;", "HEATER_GAIN       : REAL := 0.22;")
    ctx = {"src_ip": src, "actor": actor, "comment": "unscheduled change" if not approved else "WO retune"}
    ok, msg = plant.download_program(modified, ctx)
    _step(steps, f"PLC logic download (HEATER_GAIN 0.08 -> 0.22): {'accepted' if ok else 'refused'}",
          host="plc-01", technique="T0889", purdue="L2->L1", outcome="success" if ok else "blocked")


def _s6(steps, fast, actor, extreme=True):
    src = ip_of("hmi-01") if actor == "p.nair" else ip_of("eng-ws-01")
    target = 93.0 if extreme else 80.0
    ok, msg = plant.write(1, "hr", 0, [int(target * 10)], {"src_ip": src, "actor": actor,
                          "protocol": "modbus/tcp", "function_code": 6})
    _step(steps, f"Setpoint write temp_sp -> {target} degC: {'accepted' if ok else 'refused'} ({msg})",
          host="plc-01", technique="T0836", purdue="L1->L0", outcome="success" if ok else "blocked")
    if ok and extreme:
        _slow(fast, 2)
        _step(steps, "Process temperature driven toward its alarm/trip band", host="process", purdue="L0")


def _s5(steps, fast, actor):
    _s1(steps, fast, actor)
    _slow(fast, 0.5)
    _s3(steps, fast, actor)
    _slow(fast, 0.5)
    src = ip_of("historian-01")
    ok, msg = plant.write(1, "hr", 0, [int(90 * 10)], {"src_ip": src, "actor": "vendor.svc",
                          "protocol": "modbus/tcp", "function_code": 6, "force_fw_log": True})
    _step(steps, f"Control-network setpoint write from historian: {'accepted' if ok else 'refused'}",
          host="plc-01", technique="T0831", purdue="L4->L1", outcome="success" if ok else "blocked")


def _s6c(steps, fast, actor):
    src = ip_of("hmi-01")
    ok, msg = plant.write(2, "coil", 0, [1], {"src_ip": src, "actor": actor, "protocol": "modbus/tcp",
                          "function_code": 5})
    _step(steps, f"Set SIS bypass bit over the network: {'accepted' if ok else 'refused'} ({msg})",
          host="sis-01", technique="T0880", purdue="L2->L1", outcome="success" if ok else "blocked")
    if ok:
        _slow(fast, 0.5)
        _s6(steps, fast, actor, extreme=True)


def _s7(steps, fast, actor):
    """Maintenance twin of Scenario 4/6: SAME parameter change, but authorized.

    Creates an approved parameter work order for plc-01, then a known engineer
    makes the change from the HMI inside the window. Mechanically identical to a
    small Scenario 6; differs only in authorization context.
    """
    now = utcnow()
    with session_scope() as s:
        last = s.query(WorkOrder).order_by(WorkOrder.id.desc()).first()
        num = str(int(last.number) + 1) if last else "80004420"
        s.add(WorkOrder(number=num, asset="plc-01", description="Scheduled temperature setpoint trim (seasonal)",
                        change_type="parameter", planned_change={"tag": "temp_sp", "from": 72, "to": 74},
                        status="approved", requested_by="k.desai", assigned_to="s.iyer", approved_by="r.mehta",
                        window_start=now - timedelta(minutes=5), window_end=now + timedelta(minutes=60)))
    emit(source="erp", host="erp-01", event_type="work_order_approved", actor="r.mehta", src_ip="10.40.1.12",
         protocol="https", number=num, asset="plc-01", change_type="parameter",
         window_start=(now - timedelta(minutes=5)).isoformat(), window_end=(now + timedelta(minutes=60)).isoformat())
    _step(steps, f"Approved parameter work order {num} opened for plc-01 (engineer s.iyer)", host="erp-01")
    _slow(fast, 1)
    ok, msg = plant.write(1, "hr", 0, [int(74 * 10)], {"src_ip": ip_of("hmi-01"), "actor": "s.iyer",
                          "protocol": "modbus/tcp", "function_code": 6})
    _step(steps, f"Engineer writes temp_sp -> 74 degC under the work order: {'accepted' if ok else 'refused'}",
          host="plc-01", change_type="parameter", outcome="success" if ok else "blocked",
          work_order=num, note="same register/asset as Scenario 4/6; authorized")


_RUNNERS = {
    "1": _s1, "2": _s2, "3": _s3, "4": lambda st, f, a: _s4(st, f, a, approved=False),
    "5": _s5, "6": lambda st, f, a: _s6(st, f, a, extreme=True), "6c": _s6c, "7": _s7,
}
