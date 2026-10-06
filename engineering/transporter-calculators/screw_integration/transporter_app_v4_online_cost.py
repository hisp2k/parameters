"""Backward-compatible entrypoint for the local web calculator."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().with_name("transporter_app_local.py")), run_name="__main__")
