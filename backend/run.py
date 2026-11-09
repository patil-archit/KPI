"""Run both apps (plant on 8000, developer mode on 8100) in one process."""
import threading

import uvicorn

from app import settings
from app.main import dev_app, plant_app


def _serve(app, port):
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    t = threading.Thread(target=_serve, args=(dev_app, settings.DEV_PORT), daemon=True)
    t.start()
    _serve(plant_app, settings.API_PORT)
