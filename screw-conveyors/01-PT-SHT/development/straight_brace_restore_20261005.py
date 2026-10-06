"""Restore original straight braces, first in an isolated full assembly."""
from pathlib import Path
from datetime import datetime
import sys,json,shutil
import pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base))
import bridge,pin_joints
sw=w.GetActiveObject('SldWorks.Application');previous=sw.CommandInProgress;sw.CommandInProgress=True
errors=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);warnings=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
names=['Проход корпуса — выборка для 55 градусов',
       'Полость обхода — нижний переход','Полость обхода — наружная ветвь','Полость обхода — верхний переход',
       'Обход корпуса — нижний переход','Обход корпуса — наружная ветвь','Обход корпуса — верхний переход']
changed=[]

def activate(document):
    sw.ActivateDoc3(document.GetPathName,False,2,errors);assert not errors.value

def braces(root):
    return [c for c in root.GetComponents(False) if "'Подкос 1'" in c.Name2]

def restore(root,live=False):
    result=[]
    for component in braces(root):
        part=component.GetModelDoc2;activate(part)
        features=[]
        for name in names:
            feature=part.FeatureByName(name)
            if feature and not feature.IsSuppressed:
                assert feature.SetSuppression2(0,1,None),name
                if live:changed.append((part,feature))
                features.append(name)
        assert part.ForceRebuild3(False),component.Name2
        bodies=list(part.GetBodies2(0,True));assert len(bodies)==1,component.Name2
        result.append({'component':component.Name2,'file':part.GetPathName,'suppressed_bypass_features':features,
                       'solid_bodies':len(bodies),'volume_mm3':sum(b.GetMassProperties(1)[3] for b in bodies)*1e9})
    support=next(c.GetModelDoc2 for c in root.GetComponents(True) if 'Опора шнековая' in c.Name2)
    activate(support);assert support.ForceRebuild3(False)
    activate(root);assert root.ForceRebuild3(False)
    issues=bridge.model_issues(sw,root);print('Issues:',issues,flush=True)
    joints=pin_joints.verify(root)
    intersections=bridge.interference_issues(root);print('Intersections:',intersections,flush=True)
    for component in braces(root):
        assert len(component.GetModelDoc2.GetBodies2(0,True))==1,component.Name2
    return {'braces':result,'issues':issues,'joints':joints,'interferences':intersections,
            'geometry':bridge.measured_geometry(root)}

try:
    root=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));assert root
    state=json.loads(bridge.STATE.read_text(encoding='utf-8'))
    paths={Path(c.GetPathName).resolve() for c in root.GetComponents(False) if c.GetPathName}|{bridge.TOP_ASSEMBLY}
    assert all(p.is_relative_to(base) for p in paths)
    loaded={Path(d.GetPathName).resolve():d for d in sw.GetDocuments if d.GetPathName}
    assert not [str(p) for p in paths if p in loaded and loaded[p].GetSaveFlag],'Unsaved working CAD'
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S');folder=(Path('work')/('straight-brace-trial-'+stamp)).resolve();folder.mkdir()
    target=folder/'Сборка — прямые подкосы.SLDASM'
    activate(root)
    assert root.Extension.SaveAs2(str(target),0,7,w.VARIANT(pythoncom.VT_DISPATCH,None),'_STRAIGHT_'+stamp,False,errors,warnings) and not errors.value
    spec=sw.GetOpenDocSpec(str(target));spec.DocumentType=2;spec.Silent=True;trial=sw.OpenDoc7(spec);assert trial
    assert all(Path(c.GetPathName).resolve().is_relative_to(folder) for c in trial.GetComponents(False) if c.GetPathName)
    print('Independent assembly copy:',target,flush=True)
    trial_proof=restore(trial)
    output={'timestamp':datetime.now().astimezone().isoformat(timespec='seconds'),'trial_root':str(target),'trial':trial_proof}
    (base/'straight_brace_restore_20261005.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    assert trial_proof['issues']==(0,0,[]) and not trial_proof['interferences'],'Straight brace trial has errors/intersections'
    assert trial.Save3(13,errors,warnings) and not errors.value
    snapshot=base/'snapshots'/datetime.now().strftime('%Y%m%d-%H%M%S-before-straight-braces')
    for path in paths:
        if path.is_file():
            dest=snapshot/path.relative_to(base);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    output['snapshot']=str(snapshot)
    print('Restore straight braces in working assembly',flush=True)
    live_proof=restore(root,True)
    assert live_proof['issues']==(0,0,[]) and not live_proof['interferences'],live_proof
    for key in ('working_length','tube_diameter','incline'):
        assert abs(live_proof['geometry'][key]-state['values'][key])<1e-4,key
    activate(root);assert root.Save3(13,errors,warnings) and not errors.value
    output['working']=live_proof;output['saved']=True
    (base/'straight_brace_restore_20261005.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Straight braces saved; joints preserved',flush=True)
except Exception:
    if changed:
        for part,feature in reversed(changed):
            activate(part);assert feature.SetSuppression2(1,1,None)
        for part,_ in changed:assert part.ForceRebuild3(False)
        activate(root);assert root.ForceRebuild3(False)
        assert bridge.model_issues(sw,root)==(0,0,[]) and not bridge.interference_issues(root)
        assert root.Save3(13,errors,warnings) and not errors.value
        print('Previous working braces restored',flush=True)
    raise
finally:
    sw.ActivateDoc3(str(bridge.TOP_ASSEMBLY),False,2,errors);sw.CommandInProgress=previous
