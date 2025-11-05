# start.py — robust runtime launcher: reads PORT env and starts uvicorn
import os
from pathlib import Path

# Ensure current directory is app root
os.chdir(Path(__file__).parent)

port_env = os.environ.get("PORT")
try:
    PORT = int(port_env) if port_env and port_env.strip() != "" else 8000
except Exception:
    PORT = 8000

# Use uvicorn programmatically (will use installed uvicorn)
import uvicorn
print(f"Starting Uvicorn on 0.0.0.0:{PORT}")
uvicorn.run("app:app", host="0.0.0.0", port=PORT, log_level="info")
