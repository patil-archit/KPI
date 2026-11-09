#!/usr/bin/env python3
"""ArenaPlant control CLI - works on Windows, macOS and Linux.

Usage:
  python arena.py up            # start everything with Docker Compose
  python arena.py down          # stop
  python arena.py dev           # run backend + frontend locally (no Docker)
  python arena.py reset         # reset the range to baseline
  python arena.py scenario 5    # run a scenario
  python arena.py status        # range status
  python arena.py preset poland_2025
"""
import json
import subprocess
import sys
import urllib.request

DEV = "http://localhost:8100/dev"
DEV_TOKEN = "arena-dev-token"


def _call(path, body=None):
    url = DEV + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET",
                                 headers={"content-type": "application/json", "x-dev-token": DEV_TOKEN})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def main(argv):
    if not argv:
        print(__doc__)
        return
    cmd, rest = argv[0], argv[1:]
    if cmd == "up":
        subprocess.run(["docker", "compose", "up", "--build", "-d"], check=False)
        print("Plant UI:        http://localhost:8080")
        print("Developer Mode:  http://localhost:8080/dev")
    elif cmd == "down":
        subprocess.run(["docker", "compose", "down"], check=False)
    elif cmd == "dev":
        print("Start backend:  cd backend && python run.py")
        print("Start frontend: cd frontend && npm run dev")
    elif cmd == "reset":
        print(_call("/reset"))
    elif cmd == "status":
        print(json.dumps(_call("/status"), indent=2))
    elif cmd == "scenario":
        if not rest:
            print(json.dumps(_call("/scenarios"), indent=2)); return
        print(json.dumps(_call("/scenarios/run", {"key": rest[0], "fast": True}), indent=2))
    elif cmd == "preset":
        print(_call("/preset", {"preset": rest[0]}))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
