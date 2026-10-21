"""Run the dependency-free probe from the same source shipped in the backend."""
from pathlib import Path
import runpy
_runtime = runpy.run_path(str(Path(__file__).resolve().parents[2]/"backend/app/core/public_health.py"))
Probe = _runtime["Probe"]
if __name__ == "__main__":
    _runtime["main"]()
