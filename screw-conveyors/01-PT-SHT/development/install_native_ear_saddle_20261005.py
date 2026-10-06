"""Install only after the standalone saddle trial has passed."""
from pathlib import Path
import sys, json, shutil
import pythoncom, win32com.client as w
from native_ear_saddle import create_saddle, saddle_surfaces

base=Path('outputs/Шнек 1 — параметрическая модель').resolve()
sys.path.insert(0,str(base))
import bridge

trial=json.loads((base/'ear_saddle_trial_20261005.json').read_text(encoding='utf-8'))
assert [r['diameter_mm'] for r in trial]==[141,145,141]
sw=w.GetActiveObject('SldWorks.Application')
previous=sw.CommandInProgress
sw.CommandInProgress=True
errors=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
warnings=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
try:
    top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY))
    tube=sw.GetOpenDocumentByName(str(bridge.FILES['tube']))
    assert top and tube
    ears=[c for c in tube.GetComponents(True) if 'Ухо' in c.Name2]
    assert len(ears)==4 and len({c.GetPathName for c in ears})==1
    ear=next(c for c in ears if c.Name2.endswith('-1'))
    part=ear.GetModelDoc2
    paths={Path(c.GetPathName) for c in top.GetComponents(False) if c.GetPathName}|{bridge.TOP_ASSEMBLY}
    opened={Path(d.GetPathName):d for d in sw.GetDocuments if d.GetPathName}
    assert not [p for p in paths if p in opened and opened[p].GetSaveFlag], 'Unsaved CAD must be reviewed first'
    backup=base/'snapshots/20261005-before-native-ear-saddle'
    assert not backup.exists()
    for path in paths:
        if path.is_file() and path.is_relative_to(base):
            target=backup/path.relative_to(base);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,target)
    old_volume=sum(b.GetMassProperties(1)[3] for b in part.GetBodies2(0,True))
    sw.ActivateDoc3(part.GetPathName,False,2,errors)
    assert not errors.value and sw.ActiveDoc.GetPathName==part.GetPathName
    dimension,_=create_saddle(sw,part)
    new_volume=sum(b.GetMassProperties(1)[3] for b in part.GetBodies2(0,True))
    assert abs(old_volume-new_volume)*1e9<.001,(old_volume,new_volume)
    sw.ActivateDoc3(tube.GetPathName,False,2,errors)
    assert not errors.value
    expression=f'"D1@Седло корпуса — профиль@{Path(part.GetPathName).stem}<1>.Part" = "Диаметр трубы"'
    manager=tube.GetEquationMgr
    index=manager.Add2(-1,expression,True)
    assert index>=0 and manager.Equation(index)==expression
    manager.EvaluateAll
    assert tube.ForceRebuild3(False)
    sw.ActivateDoc3(top.GetPathName,False,2,errors)
    assert not errors.value and top.ForceRebuild3(False)
    assert bridge.model_issues(sw,top)==(0,0,[])
    assert not bridge.interference_issues(top)
    assert all(abs(s[6]*2000-141)<1e-6 for s in saddle_surfaces(part))
    assert top.Save3(13,errors,warnings) and not errors.value
    result={'equation':expression,'backup':str(backup),'volume_difference_mm3':(new_volume-old_volume)*1e9,
            'component_instances':4,'model_issues':[0,0,[]],'positive_interferences':0,
            'saddle_surfaces':saddle_surfaces(part)}
    (base/'native_ear_saddle_install_20261005.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Native saddle installed: baseline geometry unchanged, errors and interferences 0',flush=True)
finally:
    sw.CommandInProgress=previous
