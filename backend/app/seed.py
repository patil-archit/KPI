"""Initial data for the fictional company: Kaveri Process Industries, Bengaluru plant, Line 2."""
import secrets
from datetime import timedelta

from . import flags
from .auth import hash_password
from .db import Base, engine, session_scope
from .models import (Document, MaintenanceNotification, Material, PlcProgram, ProductionOrder, User,
                     WorkOrder, utcnow)
from .plant.sim import DEFAULT_PROGRAM, sha256

# Demo credentials. Shown in Developer Mode so testers can log in.
USERS = [
    # username, full name, role, password, department, remote, breach point
    ("admin", "SAP-style Default Admin", "admin", "admin", "IT", False, "B2"),
    ("operator", "Shared Operator Console", "operator", "operator", "Production", False, "B10"),
    ("vendor.svc", "Vendor Service Account (Automation Integrator)", "vendor", "Vend0r@2024", "External", True, "B3"),
    ("eng.svc", "Engineering Service Account", "engineer", "EngSvc!2023", "Process Engineering", False, "B6"),
    ("a.kulkarni", "Ananya Kulkarni", "planner", "Plan#2025a", "Production Planning", False, None),
    ("r.mehta", "Rohan Mehta", "supervisor", "Super#2025r", "Maintenance", False, None),
    ("s.iyer", "Sneha Iyer", "engineer", "Eng#2025s", "Process Engineering", True, None),
    ("p.nair", "Pranav Nair", "operator", "Oper#2025p", "Production", False, None),
    ("k.desai", "Karthik Desai", "maintenance", "Main#2025k", "Maintenance", False, None),
    ("m.rao", "Meera Rao", "admin", "Admin#2025m", "IT", False, None),
]

DEMO_PASSWORDS = {u[0]: u[3] for u in USERS}

MATERIALS = [
    ("RM-1001", "Mango pulp concentrate", "Raw", "kg", 4200, 1500, "WH-A-01"),
    ("RM-1002", "Sugar syrup 65 Brix", "Raw", "L", 9800, 3000, "Tank Farm T3"),
    ("RM-1003", "Process water (RO)", "Utility", "kL", 120, 40, "Utility"),
    ("RM-1004", "Citric acid", "Raw", "kg", 310, 100, "WH-A-04"),
    ("PK-2001", "PET bottle 500 ml", "Packaging", "pcs", 84000, 30000, "WH-B-02"),
    ("PK-2002", "Cap 28 mm tamper-evident", "Packaging", "pcs", 91000, 30000, "WH-B-03"),
    ("PK-2003", "Label - Mango 500 ml", "Packaging", "pcs", 62000, 25000, "WH-B-05"),
    ("FG-3001", "Kaveri Mango Drink 500 ml", "Finished", "pcs", 18240, 5000, "WH-FG-01"),
    ("FG-3002", "Kaveri Mango Lite 500 ml", "Finished", "pcs", 6420, 3000, "WH-FG-02"),
    ("SP-4001", "Heater element 6 kW (spare)", "Spare", "pcs", 2, 1, "Stores"),
    ("SP-4002", "Conveyor drive belt", "Spare", "pcs", 3, 2, "Stores"),
]


def _docs():
    return [
        ("corp", "/Policies", "Information_Security_Policy_v3.pdf.txt", "r.mehta", None,
         "Kaveri Process Industries - Information Security Policy (v3)\n\n"
         "1. Passwords must be at least 12 characters and unique per system.\n"
         "2. Remote vendor access must use the portal; sessions are logged.\n"
         "3. Changes to PLC logic require an approved work order (change type: logic).\n"
         "4. SIS bypass requires plant manager sign-off and the physical key switch.\n"),
        ("corp", "/Production/Shift Reports", "Shift_Report_Line2_A.txt", "p.nair", None,
         "Line 2 - Shift A\nOutput: 41,200 bottles. Rejects: 0.4%.\nNotes: brief level alarm at 06:40 (pump P-101 slow start), cleared.\n"),
        ("corp", "/Production/Shift Reports", "Shift_Report_Line2_B.txt", "p.nair", None,
         "Line 2 - Shift B\nOutput: 39,870 bottles. Rejects: 0.6%.\nNotes: conveyor belt tension checked by maintenance.\n"),
        ("corp", "/Maintenance", "PM_Schedule_Q4.txt", "k.desai", None,
         "Planned maintenance Q4\n- Heater E-101 inspection (monthly)\n- Conveyor CV-201 belt (quarterly)\n- PLC-1 firmware review (annual, needs logic WO)\n"),
        ("corp", "/IT/Handover", "IT_handover_notes_vendor_access.txt", "m.rao", "B3",
         "IT handover - notes for new admin\n\n"
         "Automation integrator still needs access for warranty support.\n"
         "Portal account: vendor.svc\nPassword: Vend0r@2024   (same as their old VPN login, they asked us not to change it)\n"
         "Lands on eng-ws-01 (engineering workstation).\n"),
        ("eng-ws", "/Projects/Line2_MixTank", "project_config.ini", "s.iyer", "B6",
         "[target]\nplc = 10.10.0.11\nunit = 1\nprotocol = modbus-tcp\n\n[service_account]\n"
         "user = eng.svc\npassword = EngSvc!2023\n; TODO move to vault\n"),
        ("eng-ws", "/Projects/Line2_MixTank", "MixTankControl_v1.st", "s.iyer", None, DEFAULT_PROGRAM),
        ("eng-ws", "/Projects/Line2_MixTank", "IO_list.csv", "s.iyer", None,
         "tag,address,description\nTT101,IR0,Tank temperature x10\nPT101,IR1,Tank pressure x100\nLT101,IR2,Tank level x10\n"
         "SC201,IR3,Conveyor speed x100\nTempSP,HR0,Temperature setpoint x10\nConvSP,HR1,Conveyor setpoint x100\n"
         "SIS_BYPASS,unit2/coil0,Safety trip bypass\n"),
        ("eng-ws", "/Notes", "network_notes.txt", "s.iyer", None,
         "historian-01 has a second NIC on the office LAN (10.40.0.30) so management can see trends.\n"
         "fw-02 rule 140 opened for the integrator during commissioning - remove after handover.\n"),
    ]


def seed_all() -> None:
    now = utcnow()
    with session_scope() as s:
        for uname, full, role, pw, dept, remote, bp in USERS:
            s.add(User(username=uname, full_name=full, role=role, password_hash=hash_password(pw),
                       department=dept, email=f"{uname}@kaveri-process.example", remote_access=remote,
                       breach_point=bp))
        for code, name, cat, uom, stock, rop, loc in MATERIALS:
            s.add(Material(code=code, name=name, category=cat, uom=uom, stock=stock, reorder_point=rop, location=loc))
        orders = [
            ("1000231", "FG-3001", "Kaveri Mango Drink 500 ml", 24000, 24000, "completed", 72.0, 1.0, -2),
            ("1000232", "FG-3002", "Kaveri Mango Lite 500 ml", 12000, 12000, "completed", 70.0, 1.0, -1),
            ("1000233", "FG-3001", "Kaveri Mango Drink 500 ml", 30000, 0, "in_progress", 72.0, 1.0, 0),
            ("1000234", "FG-3001", "Kaveri Mango Drink 500 ml", 18000, 0, "released", 72.0, 1.0, 1),
            ("1000235", "FG-3002", "Kaveri Mango Lite 500 ml", 15000, 0, "created", 70.0, 0.9, 2),
        ]
        for num, mat, prod, qty, done, st, tsp, csp, day in orders:
            s.add(ProductionOrder(number=num, material_code=mat, product=prod, quantity=qty, completed_qty=done,
                                  status=st, recipe_temp_sp=tsp, recipe_conveyor_sp=csp, created_by="a.kulkarni",
                                  due_date=(now + timedelta(days=day)).date().isoformat(),
                                  released_at=now if st != "created" else None))
        s.add(MaintenanceNotification(number="40001102", asset="E-101 Heater", priority="medium", status="closed",
                                      description="Heater element resistance drift", created_by="p.nair"))
        s.add(MaintenanceNotification(number="40001103", asset="CV-201 Conveyor", priority="low", status="open",
                                      description="Belt squeal at high speed", created_by="p.nair"))
        s.add(MaintenanceNotification(number="40001104", asset="PLC-1", priority="medium", status="in_process",
                                      description="Temperature loop slightly oscillating; retune requested", created_by="s.iyer"))
        s.add(WorkOrder(number="80004410", notification_number="40001102", asset="plc-01",
                        description="Heater element replaced; verify temperature setpoint loop",
                        change_type="parameter", planned_change={"tag": "temp_sp", "from": 72, "to": 72},
                        status="closed", requested_by="k.desai", assigned_to="s.iyer", approved_by="r.mehta",
                        window_start=now - timedelta(days=3, hours=2), window_end=now - timedelta(days=3),
                        closed_at=now - timedelta(days=3)))
        s.add(WorkOrder(number="80004411", notification_number="40001104", asset="plc-01",
                        description="Retune temperature PI gain (logic constant HEATER_GAIN)",
                        change_type="logic", planned_change={"parameter": "HEATER_GAIN", "from": 0.08, "to": 0.07},
                        status="created", requested_by="s.iyer", assigned_to="s.iyer"))
        for share, folder, name, owner, bp, content in _docs():
            s.add(Document(share=share, folder=folder, name=name, owner=owner, breach_point=bp, content=content))
        s.add(PlcProgram(plc="plc-01", version=1, source=DEFAULT_PROGRAM, sha256=sha256(DEFAULT_PROGRAM),
                         author="s.iyer", comment="Commissioning baseline", active=True))


def apply_flag_side_effects() -> None:
    """Make data match the switchboard (accounts, leaked files, rotated passwords)."""
    with session_scope() as s:
        def user(n):
            return s.query(User).filter(User.username == n).first()

        if (u := user("admin")):
            u.enabled = flags.vulnerable("B2")
        if (u := user("operator")):
            u.enabled = flags.vulnerable("B10")
        if (u := user("vendor.svc")):
            u.password_hash = hash_password("Vend0r@2024" if flags.vulnerable("B3") else secrets.token_urlsafe(18))
        if (u := user("eng.svc")):
            u.password_hash = hash_password("EngSvc!2023" if flags.vulnerable("B6") else secrets.token_urlsafe(18))
        for d in s.query(Document).filter(Document.breach_point.isnot(None)).all():
            if d.breach_point == "B3":
                d.share = "corp" if flags.vulnerable("B3") else "archived"
            if d.breach_point == "B6":
                d.content = (
                    "[target]\nplc = 10.10.0.11\nunit = 1\nprotocol = modbus-tcp\n\n[service_account]\n"
                    + ("user = eng.svc\npassword = EngSvc!2023\n; TODO move to vault\n" if flags.vulnerable("B6")
                       else "user = eng.svc\npassword_ref = vault://ot/eng.svc\n")
                )


def reset_database() -> None:
    keep = flags.snapshot()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    seed_all()
    flags.ensure_defaults()
    if keep:
        flags.set_modes(keep)
    else:
        apply_flag_side_effects()


def init_database() -> None:
    Base.metadata.create_all(engine)
    with session_scope() as s:
        empty = s.query(User).count() == 0
    if empty:
        seed_all()
    flags.ensure_defaults()
    apply_flag_side_effects()
