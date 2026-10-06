from pathlib import Path
from datetime import datetime
import json,sys,shutil
import pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');previous=sw.CommandInProgress;sw.CommandInProgress=True
from trial_support_pipe_mates_20261005 import install,activate,errors,warnings
root=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));assert root
support=sw.GetOpenDocumentByName(str(bridge.FILES['support']));assert support
brace=next(c.GetModelDoc2 for c in support.GetComponents(True) if ".25.00.09 '" in c.Name2)
manager=support.GetEquationMgr;part_manager=brace.GetEquationMgr
count=manager.GetCount;part_count=part_manager.GetCount
old_units=manager.AngularEquationUnits;old_part_units=part_manager.AngularEquationUnits
old_dims={name:float(brace.Parameter(name).SystemValue) for name in ('D1@Плоскость1','D1@Плоскость2')}
changed=False
try:
    trial=json.loads((base/'support_pipe_joint_trial_20261005.json').read_text(encoding='utf-8'))
    assert trial['pipe_joints']['ok'] and not trial['interferences'] and trial['issues']==[0,0,[]]
    paths={Path(c.GetPathName).resolve() for c in root.GetComponents(False) if c.GetPathName}|{bridge.TOP_ASSEMBLY}
    loaded={Path(d.GetPathName).resolve():d for d in sw.GetDocuments if d.GetPathName}
    assert all(p.is_relative_to(base) for p in paths)
    assert not [str(p) for p in paths if p in loaded and loaded[p].GetSaveFlag],'Unsaved working CAD'
    snapshot=base/'snapshots'/datetime.now().strftime('%Y%m%d-%H%M%S-before-pipe-joints')
    for path in paths:
        if path.is_file():
            dest=snapshot/path.relative_to(base);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    changed=True;proof=install(root)
    assert root.Save3(13,errors,warnings) and not errors.value
    proof.update(snapshot=str(snapshot),timestamp=datetime.now().astimezone().isoformat(timespec='seconds'),saved=True)
    (base/'support_pipe_joint_repair_20261005.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Working pipe joints repaired and saved',flush=True)
except Exception:
    if changed:
        activate(support)
        mate=support.FeatureByName('Подкос 1 — стойка 1 — стык труб')
        if mate:
            support.ClearSelection2(True);assert mate.Select2(False,0);assert support.Extension.DeleteSelection2(0)
        for name in ('Архив — Параллельность2','Параллельность2'):
            feature=support.FeatureByName(name)
            if feature:feature.Name='Параллельность2';assert feature.SetSuppression2(1,1,None);break
        for index in reversed(range(count,manager.GetCount)):manager.Delete(index)
        manager.AngularEquationUnits=old_units
        activate(brace)
        for index in reversed(range(part_count,part_manager.GetCount)):part_manager.Delete(index)
        part_manager.AngularEquationUnits=old_part_units
        for name in ('Зазор у уха — местная выборка','Зазор у уха — местная выборка — профиль'):
            feature=brace.FeatureByName(name)
            if feature:
                brace.ClearSelection2(True);assert feature.Select2(False,0);assert brace.Extension.DeleteSelection2(0)
        for name,value in old_dims.items():brace.Parameter(name).SystemValue=value
        assert brace.FeatureByName('Подрезка подкоса по стойкам и балкам').SetSuppression2(1,1,None)
        manager.EvaluateAll;part_manager.EvaluateAll;brace.ForceRebuild3(False)
        activate(support);support.ForceRebuild3(False);activate(root);assert root.ForceRebuild3(False)
        assert bridge.model_issues(sw,root)==(0,0,[]) and not bridge.interference_issues(root)
        assert root.Save3(13,errors,warnings) and not errors.value
        print('Original working geometry restored',flush=True)
    raise
finally:
    sw.ActivateDoc3(str(bridge.TOP_ASSEMBLY),False,2,errors);sw.CommandInProgress=previous
