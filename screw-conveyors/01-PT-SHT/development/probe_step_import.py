from pathlib import Path
import shutil
import sys

import win32com.client as win32
import pythoncom

project = Path(sys.argv[1]).resolve()
source = next((project / 'CAD').glob('*КТ*.STEP'))
probe = project / 'snapshots' / 'step-import-probe'
probe.mkdir(parents=True, exist_ok=True)
copy = probe / (source.stem + '-assembly.STEP')
if not copy.exists():
    shutil.copy2(source, copy)

sw = win32.GetActiveObject('SldWorks.Application')
pref = 579  # swImportNeutralAssemblyStructureMapping
original = sw.GetUserPreferenceIntegerValue(pref)
print('MAPPING_BEFORE', original, flush=True)
sw.SetUserPreferenceIntegerValue(pref, 0)  # Default, preserve STEP structure
err = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
data = sw.GetImportFileData(str(copy))
print('IMPORT_DATA', bool(data), flush=True)
try:
    doc = sw.LoadFile4(str(copy), '', data, err)
finally:
    sw.SetUserPreferenceIntegerValue(pref, original)
print('OPEN', bool(doc), 'ERROR', err.value, flush=True)
if doc is None:
    sys.exit(1)
print('DOC', doc.GetPathName, doc.GetTitle, doc.GetType, flush=True)
if doc.GetType == 2:
    components = doc.GetComponents(False) or []
    print('COMPONENTS', len(components), flush=True)
    for component in components[:12]:
        print('COMP', component.Name2, component.GetPathName, flush=True)
