"""兼容入口：请改用 scripts/probe_mcp.py sogou"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(ROOT / "scripts" / "probe_mcp.py"), "sogou"], check=False)
