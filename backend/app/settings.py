"""Runtime settings, read from environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'arenaplant.db'}")

# Plant API (what operators, the UI and the Cyber-Arena Tool Gateway talk to)
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Developer Mode API (range control + ground truth). Never expose to agents.
DEV_HOST = os.getenv("DEV_HOST", "0.0.0.0")
DEV_PORT = int(os.getenv("DEV_PORT", "8100"))
DEV_TOKEN = os.getenv("DEV_TOKEN", "arena-dev-token")

# Read-only evidence access for the Cyber-Arena agents.
EVIDENCE_TOKEN = os.getenv("EVIDENCE_TOKEN", "arena-evidence-token")

# Modbus/TCP server for PLC-1 (unit 1) and the SIS (unit 2).
MODBUS_HOST = os.getenv("MODBUS_HOST", "0.0.0.0")
MODBUS_PORT = int(os.getenv("MODBUS_PORT", "5020"))

SIM_TICK_SECONDS = float(os.getenv("SIM_TICK_SECONDS", "0.5"))
HISTORIAN_INTERVAL = float(os.getenv("HISTORIAN_INTERVAL", "2.0"))
HISTORIAN_RETENTION_HOURS = float(os.getenv("HISTORIAN_RETENTION_HOURS", "12"))
