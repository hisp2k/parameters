from pathlib import Path
import json,sys,pythoncom,win32com.client as w
from brace_clearance_20261005 import local_point
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');path=json.loads((base/'straight_brace_restore_20261005.json').read_text(encoding='utf-8'))['trial_root'];root=sw.GetOpenDocumentByName(path)
mgr=root.InterferenceDetectionManager;mgr.TreatCoincidenceAsInterference=False;mgr.TreatSubAssembliesAsComponents=False;mgr.IncludeMultibodyPartInterferences=True;mgr.IgnoreHiddenBodies=False
try:
    for item in mgr.GetInterferences or []:
        if item.Volume*1e9<=.001:continue
        brace=next(c for c in item.Components if 'Подкос' in c.Name2)
        dispid=item._oleobj_.GetIDsOfNames('GetInterferenceBody');body=w.Dispatch(item._oleobj_.Invoke(dispid,0,pythoncom.DISPATCH_METHOD,True))
        mass=list(body.GetMassProperties(1))
        box=body.GetBodyBox;box=list(box() if callable(box) else box)
        corners=[local_point([box[3*x],box[1+3*y],box[2+3*z]],list(brace.Transform2.ArrayData)) for x in (0,1) for y in (0,1) for z in (0,1)]
        print(brace.Name2,'volume',mass[3]*1e9,'local centre',local_point(mass[:3],list(brace.Transform2.ArrayData)),'box',[min(p[i] for p in corners) for i in range(3)]+[max(p[i] for p in corners) for i in range(3)],flush=True)
finally:mgr.Done()
