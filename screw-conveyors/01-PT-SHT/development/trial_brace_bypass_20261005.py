from pathlib import Path
from datetime import datetime
import json,sys,shutil,pythoncom,win32com.client as w
from brace_bypass_20261005 import create_bypass
from brace_clearance_20261005 import create_clearance
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');previous=sw.CommandInProgress;sw.CommandInProgress=True
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
try:
 geometry=json.loads(Path('work/brace_clearance_geometry_20261005.json').read_text(encoding='utf-8'))
 support=sw.GetOpenDocumentByName(str(bridge.FILES['support']));source=next(c.GetPathName for c in support.GetComponents(True) if "'Подкос 1'" in c.Name2)
 target=(Path('work')/datetime.now().strftime('Подкос — обход корпуса — %Y%m%d-%H%M%S.SLDPRT')).resolve();shutil.copy2(source,target)
 spec=sw.GetOpenDocSpec(str(target));spec.DocumentType=1;spec.Silent=True;part=sw.OpenDoc7(spec);assert part
 sw.ActivateDoc3(str(target),False,2,e);assert not e.value
 bypass=create_bypass(sw,part,geometry['center'],geometry['axis'])
 print('Bypass created',bypass,flush=True)
 cut=create_clearance(sw,part,geometry['center'],geometry['axis'])
 assert len(part.GetBodies2(0,True))==1
 assert part.ForceRebuild3(False)
 assert part.Save3(9,e,q) and not e.value
 proof={'part':str(target),'bypass':bypass,'clearance':cut,'bodies':len(part.GetBodies2(0,True)),'volume_mm3':sum(b.GetMassProperties(1)[3] for b in part.GetBodies2(0,True))*1e9}
 (base/'brace_bypass_trial_20261005.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Single continuous brace verified',proof,flush=True)
finally:
 sw.ActivateDoc3(str(bridge.TOP_ASSEMBLY),False,2,e);sw.CommandInProgress=previous
