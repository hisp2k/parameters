"""Read-only SOLIDWORKS/Flow Simulation status for the clean CFD test copy."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pythoncom
import win32com.client as win32


rot = pythoncom.GetRunningObjectTable()
bind = pythoncom.CreateBindCtx(0)
matches = [
    item
    for item in rot.EnumRunning()
    if item.GetDisplayName(bind, None) == "SolidWorks_PID_10044"
]
if len(matches) != 1:
    raise RuntimeError("Expected one observed SOLIDWORKS ROT instance")

sw = win32.Dispatch(rot.GetObject(matches[0]).QueryInterface(pythoncom.IID_IDispatch))
target = Path(
    r"C:\Users\adm\Documents\Codex\2026-10-03\new-chat\work"
    r"\GRIT_CFD_BASE_CLEAN_TEST_20261004.SLDPRT"
)
documents = [
    item for item in (sw.GetDocuments or ()) if Path(item.GetPathName) == target
]
if len(documents) != 1:
    raise RuntimeError("Clean test document not open exactly once")
doc = documents[0]
addon = sw.GetAddInObject("FloWorks.App")
api = addon.GetAPI() if addon else None
flow_doc = api.GetDocument(doc) if api else None
bodies = doc.GetBodies2(0, False) or ()
result = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "status": "NO_FLOW_SOLUTION",
    "solidworks_revision": sw.RevisionNumber,
    "solidworks_pid": 10044,
    "cad_file": str(target),
    "cad_configuration": doc.ConfigurationManager.ActiveConfiguration.Name,
    "solid_body_count": len(bodies),
    "flow_addin_available": bool(addon),
    "flow_api_available": bool(api),
    "flow_demo_version": api.IsDemoVersion() if api else None,
    "flow_project_count": len(flow_doc.Projects or ()) if flow_doc else None,
    "solver_run": False,
    "particle_study_run": False,
    "capture_efficiency_0_20_percent": None,
}
out = Path(
    r"C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs"
    r"\grit_chamber\03_Результаты\GRIT_SOLIDWORKS_EFFICIENCY_STATUS_20261004.json"
)
out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(result, indent=2, ensure_ascii=True))
