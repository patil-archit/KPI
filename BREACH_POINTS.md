# ArenaPlant — Breach Point Register

Each breach point is a weakness in the simulated plant's own configuration, switchable
in Developer Mode between **Vulnerable** (weakness present) and **Patched** (proper control;
attempts are refused and logged with `outcome: blocked`). Every scenario records which flags
were set, so a patched run is still useful evidence ("attempted but stopped").

| ID | Weakness | Asset / Layer | Scenarios | ATT&CK for ICS | Expected evidence (sources) |
|----|----------|---------------|-----------|----------------|-----------------------------|
| B1 | Remote access portal without MFA | portal-01 / L4 | 1, 5 | T0886, T0859 | `auth` login_success via remote, no `mfa_challenge`; `host` remote_session_start on eng-ws-01 |
| B2 | Default ERP admin account active | erp-01 / L4 | 1 | T0859 | `auth` login_success actor=admin |
| B3 | Vendor credentials on corporate share | files-01 / L4 | 1, 5 | T0859 | `host` file_read of IT handover note; later reuse on portal |
| B4 | Work-order approval missing auth check | erp-01 / L4 | 7-variant | T0859 | `erp` work_order_approved with `self_approved: true` |
| B5 | Dual-homed historian, default local login | historian-01 / L3 | 3, 5 | T0840, T0859 | `auth` login_success via historian-local from office IP |
| B6 | Plain-text creds in engineering files | eng-ws-01 / L3 | 2, 5 | T0859 | `host` file_read project_config.ini; `process_exec` |
| B7 | Unsigned PLC logic download | plc-01 / L3→L1 | 4 | T0843, T0889 | `plc` program_download, `change_type: logic`, sha change |
| B8 | Temporary vendor firewall rule open | fw-02 / L3→L1 | 3, 5 | T0886 | `network` network_connection allowed, rule 140 |
| B9 | Unauthenticated Modbus writes | plc-01 / L1→L0 | 4, 6 | T0836, T0831 | `plc` setpoint_change, `change_type: parameter`; `process` range_exceeded |
| B10 | Shared operator account, no timeout | hmi-01 / L2 | 1, 6 | T0859 | `auth` login_success actor=operator; long-lived session |
| B11 | SIS bypass writable over network | sis-01 / L1 | 6c | T0831, T0880 | `plc` sis_bypass_change, `change_type: safety_interlock`, severity critical |

## Definition of done (per breach point)
1. Toggles live between Vulnerable / Patched with no restart.
2. Exploitable by a scenario script when Vulnerable; refused (and logged `blocked`) when Patched.
3. Leaves evidence from **≥2 sources** (e.g. `network` + `plc`, or `auth` + `host`).
4. Its scenario records ground truth (techniques, Purdue path, event IDs).
5. `arena reset` fully clears it.

## Presets
- **all_vulnerable / hardened** — every point open / closed.
- **poland_2025** — remote access without MFA + reused vendor creds (B1, B3, B6, B7, B8).
- **oldsmar_2021** — remote access to HMI, shared account, unrestricted setpoints (B1, B3, B9, B10).
- **safety_bypass** — path to the SIS bypass bit (B5, B8, B9, B11).
