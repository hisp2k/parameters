from pathlib import Path
from datetime import datetime
import sys,json,shutil
import pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');previous=sw.CommandInProgress;sw.CommandInProgress=True
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
try:
    top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));tube=sw.GetOpenDocumentByName(str(bridge.FILES['tube']))
    pipe=next(c.GetModelDoc2 for c in tube.GetComponents(True) if 'Труба шнека' in c.Name2)
    cut=pipe.FeatureByName('Вырез-Вытянуть5');assert cut and cut.IsSuppressed
    paths={Path(c.GetPathName) for c in top.GetComponents(False) if c.GetPathName}|{bridge.TOP_ASSEMBLY}
    opened={Path(d.GetPathName):d for d in sw.GetDocuments if d.GetPathName}
    assert not [p for p in paths if p in opened and opened[p].GetSaveFlag]
    snapshot=base/'snapshots'/datetime.now().strftime('%Y%m%d-%H%M%S-before-opening110')
    for path in paths:
        if path.is_file() and path.is_relative_to(base):
            target=snapshot/path.relative_to(base);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    shutil.copy2(base/'parameter_correspondence_20261005.json',base/'parameter_correspondence_20261005_before_opening.json')
    before=sum(b.GetMassProperties(1)[3] for b in pipe.GetBodies2(0,True))
    result={'snapshot':str(snapshot),'before_suppressed':True}
    try:
        sw.ActivateDoc3(pipe.GetPathName,False,2,e);assert not e.value
        assert cut.SetSuppression2(1,1,None)
        assert pipe.ForceRebuild3(False)
        sw.ActivateDoc3(tube.GetPathName,False,2,e);assert not e.value and tube.ForceRebuild3(False)
        sw.ActivateDoc3(top.GetPathName,False,2,e);assert not e.value and top.ForceRebuild3(False)
        assert bridge.model_issues(sw,top)==(0,0,[])
        assert not bridge.interference_issues(top)
        cylinders=[list(f.GetSurface.CylinderParams) for b in pipe.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsCylinder]
        opening=[s for s in cylinders if abs(s[6]*2000-110)<1e-5]
        assert opening,'No physical cylindrical opening 110 mm'
        after=sum(b.GetMassProperties(1)[3] for b in pipe.GetBodies2(0,True))
        assert after<before
        assert top.Save3(13,e,q) and not e.value
        result.update(restored=True,opening_cylinders=opening,removed_volume_mm3=(before-after)*1e9,
                      model_errors=0,positive_interferences=0)
        print('Opening 110 restored and measured; native checks 0',flush=True)
    except Exception as error:
        result.update(restored=False,error=str(error))
        sw.ActivateDoc3(pipe.GetPathName,False,2,e);assert cut.SetSuppression2(0,1,None)
        assert pipe.ForceRebuild3(False)
        sw.ActivateDoc3(tube.GetPathName,False,2,e);assert tube.ForceRebuild3(False)
        sw.ActivateDoc3(top.GetPathName,False,2,e);assert top.ForceRebuild3(False)
        assert bridge.model_issues(sw,top)==(0,0,[]) and not bridge.interference_issues(top)
        assert top.Save3(13,e,q) and not e.value
        print('Opening restoration rejected and rolled back:',error,flush=True)
    (base/'opening110_restore_20261005.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
finally:sw.CommandInProgress=previous
