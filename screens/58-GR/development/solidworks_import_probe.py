"""Open STEP in a separate SOLIDWORKS instance for read-only inspection."""

import json
from pathlib import Path
import sys
import time
import win32com.client


STEP = Path(r"C:\Users\adm\Downloads\Новая папка\58.GR.00.00.00.00 СБ  Решетка грабельная (STEP 214 ТТ)(2).STEP")

def log(*parts):
    print(*parts, flush=True)

sw = win32com.client.DispatchEx("SldWorks.Application")
log("revision", sw.RevisionNumber)
docs = sw.GetDocuments
log("initial_docs", len(docs) if docs else 0)
if docs:
    log("ABORT: DispatchEx attached to an instance with existing documents")
    sys.exit(2)
sw.Visible = False
sw.UserControl = False
try:
    import_data = sw.GetImportFileData(str(STEP))
    log("import_data", bool(import_data))
    if import_data:
        import_data.MapConfigurationData = True
    start = time.time()
    result = sw.LoadFile4(str(STEP), "r", import_data, 0)
    log("load_seconds", round(time.time() - start, 1))
    log("load_result_type", type(result).__name__)
    log("load_result", str(result)[:500])
    model = result[0] if isinstance(result, tuple) else result
    if model:
        log("title", model.GetTitle)
        log("path", model.GetPathName)
        log("type", model.GetType)
        config = model.ConfigurationManager.ActiveConfiguration
        log("configuration", config.Name if config else "")
        comps = model.GetComponents(False) if model.GetType == 2 else None
        log("components", len(comps) if comps else 0)
        if comps:
            names = [c.Name2 for c in comps]
            log("first_components", names[:8])
        Path(__file__).with_name("solidworks_import_probe.json").write_text(json.dumps({
            "title": model.GetTitle, "path": model.GetPathName, "type": model.GetType,
            "configuration": config.Name if config else "", "components": len(comps) if comps else 0,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
finally:
    log("exiting_probe_instance")
    sw.ExitApp()
