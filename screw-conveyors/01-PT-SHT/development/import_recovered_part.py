"""Probe a recovered single-product STEP and save a native editable copy."""
from pathlib import Path
import sys

import pythoncom
import win32com.client as win32

project = Path(sys.argv[1]).resolve()
sw = win32.GetActiveObject('SldWorks.Application')
names = ([p.stem for p in sorted((project / 'recovered_from_step').glob('*.STEP'))]
         if sys.argv[2] == 'ALL' else [sys.argv[2]])
for name in names:
    source = project / 'recovered_from_step' / (name + '.STEP')
    target = project / 'recovered_from_step' / (name + '.SLDPRT')
    if target.exists():
        print('SKIP', name, flush=True)
        continue
    assert source.is_file()
    data = sw.GetImportFileData(str(source))
    error = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    doc = sw.LoadFile4(str(source), '', data, error)
    print('OPEN', name, bool(doc), error.value, flush=True)
    if not doc or doc.GetType != 1:
        raise RuntimeError('STEP did not import as a part')
    bodies = doc.GetBodies2(0, False) or []
    print('BODIES', len(bodies), flush=True)
    if len(bodies) != 1:
        raise RuntimeError('Expected one solid body')
    box = bodies[0].GetBodyBox()
    print('BOX_M', tuple(round(float(v), 6) for v in box), flush=True)
    save_error = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    save_warning = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    saved = doc.SaveAs4(str(target), 0, 2, save_error, save_warning)
    print('SAVED', saved, save_error.value, save_warning.value, target.stat().st_size if target.exists() else None, flush=True)
    if not saved or save_error.value:
        raise RuntimeError(f'Save failed for {name}')
