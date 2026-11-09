"""Logical asset inventory of the simulated plant, organised by Purdue level.

The whole plant runs inside one backend in v1, so these addresses are the
*simulated* addresses that appear in evidence. Real TCP clients (e.g. a Modbus
client from the Cyber-Arena Tool Gateway) show up with their real IP and are
classified as `external` unless they match an entry here.
"""

ASSETS = [
    # Level 4/5: enterprise
    {"host": "erp-01", "ip": "10.40.0.10", "level": 4, "zone": "corp", "role": "ERP application server", "services": ["https/443"]},
    {"host": "portal-01", "ip": "10.40.0.5", "level": 4, "zone": "corp-dmz", "role": "Remote access gateway (vendor VPN portal)", "services": ["https/443"]},
    {"host": "files-01", "ip": "10.40.0.20", "level": 4, "zone": "corp", "role": "Corporate file share", "services": ["smb/445", "https/443"]},
    {"host": "corp-ws-01", "ip": "10.40.1.11", "level": 4, "zone": "corp", "role": "Office workstation (planning)", "services": []},
    {"host": "corp-ws-02", "ip": "10.40.1.12", "level": 4, "zone": "corp", "role": "Office workstation (maintenance office)", "services": []},
    # Level 3: operations
    {"host": "historian-01", "ip": "10.30.0.10", "level": 3, "zone": "ops", "role": "Process historian (dual-homed: also 10.40.0.30)", "services": ["https/443", "modbus-client"], "secondary_ip": "10.40.0.30"},
    {"host": "mes-01", "ip": "10.30.0.15", "level": 3, "zone": "ops", "role": "Manufacturing execution system", "services": ["https/443"]},
    {"host": "eng-ws-01", "ip": "10.30.0.21", "level": 3, "zone": "ops", "role": "Engineering workstation", "services": ["ssh/22", "rdp/3389"]},
    {"host": "fw-01", "ip": "10.35.0.1", "level": 3, "zone": "boundary", "role": "IT/OT boundary firewall (L4 ↔ L3)", "services": []},
    {"host": "fw-02", "ip": "10.25.0.1", "level": 2, "zone": "boundary", "role": "Control-zone firewall (L3 ↔ L2/L1)", "services": []},
    # Level 2: supervisory
    {"host": "hmi-01", "ip": "10.20.0.10", "level": 2, "zone": "supervisory", "role": "SCADA / HMI server", "services": ["https/443", "modbus-client"]},
    # Level 1: control
    {"host": "plc-01", "ip": "10.10.0.11", "level": 1, "zone": "control", "role": "PLC-1 mixing tank + conveyor (Modbus/TCP unit 1)", "services": ["modbus/502"]},
    {"host": "sis-01", "ip": "10.10.0.12", "level": 1, "zone": "control", "role": "Safety instrumented system (Modbus/TCP unit 2)", "services": ["modbus/502"]},
    # Level 0: process
    {"host": "process", "ip": "-", "level": 0, "zone": "field", "role": "Heated mixing tank, feed pump, bottling conveyor", "services": []},
]

BY_HOST = {a["host"]: a for a in ASSETS}
BY_IP = {a["ip"]: a for a in ASSETS}
for _a in ASSETS:
    if "secondary_ip" in _a:
        BY_IP[_a["secondary_ip"]] = _a

EXTERNAL_IPS = ["203.0.113.47", "198.51.100.23", "185.220.101.9", "45.155.205.233"]


def ip_of(host: str) -> str:
    return BY_HOST[host]["ip"]


def level_of(host: str) -> int:
    a = BY_HOST.get(host)
    return a["level"] if a else 5


def classify_ip(ip: str | None) -> dict:
    if ip and ip in BY_IP:
        return BY_IP[ip]
    return {"host": "unknown", "ip": ip, "level": 5, "zone": "external", "role": "Unknown / external"}


def topology() -> dict:
    links = [
        {"from": "portal-01", "to": "eng-ws-01", "via": "fw-01", "note": "Vendor remote sessions"},
        {"from": "erp-01", "to": "mes-01", "via": "fw-01", "note": "Production orders"},
        {"from": "historian-01", "to": "corp", "via": "dual-homed NIC", "note": "Reporting access from office network"},
        {"from": "mes-01", "to": "hmi-01", "via": "fw-02", "note": "Recipe download"},
        {"from": "eng-ws-01", "to": "plc-01", "via": "fw-02", "note": "Engineering access"},
        {"from": "hmi-01", "to": "plc-01", "via": "control LAN", "note": "Modbus/TCP polling + writes"},
        {"from": "hmi-01", "to": "sis-01", "via": "control LAN", "note": "SIS status"},
        {"from": "historian-01", "to": "plc-01", "via": "fw-02", "note": "Modbus/TCP polling"},
        {"from": "plc-01", "to": "process", "via": "field I/O", "note": "Sensors / actuators"},
        {"from": "sis-01", "to": "process", "via": "hardwired", "note": "Trip outputs"},
    ]
    return {
        "levels": {
            "4": "Enterprise (corporate IT)",
            "3": "Operations (historian, MES, engineering)",
            "2": "Supervisory (HMI / SCADA)",
            "1": "Control (PLC, SIS)",
            "0": "Physical process",
        },
        "assets": ASSETS,
        "links": links,
    }
