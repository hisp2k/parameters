from pathlib import Path
from datetime import datetime
import json, sys, math, shutil
import pythoncom, win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve()
sys.path.insert(0,str(base))
import bridge, pin_joints
sw=w.GetActiveObject('SldWorks.Application')
previous=sw.CommandInProgress;sw.CommandInProgress=True
errors=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
warnings=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
created=[];suppressed=[];equations_added=[];original_plane=None

def activate(document):
    sw.ActivateDoc3(document.GetPathName,False,2,errors)
    assert not errors.value

def concentric(document, first, second, d1, d2, name):
    activate(document)
    faces=[];axes=[]
    for component, diameter in [(first,d1),(second,d2)]:
        faces.append(component.GetCorrespondingEntity(pin_joints.cylindrical_face(component,diameter)))
        axes.append(pin_joints.cylindrical_axis(component,diameter)[1])
    data=document.CreateMateData(1)
    data.MateAlignment=0 if sum(axes[0][i]*axes[1][i] for i in range(3))>0 else 1
    data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,faces)
    feature=document.CreateMate(data);assert feature,name
    feature.Name=name;created.append((document,feature));return feature

try:
    trial_path=json.loads((base/'pin_joint_trial_20261005.json').read_text(encoding='utf-8'))['root']
    trial=sw.GetOpenDocumentByName(trial_path);assert trial
    trial_proof=pin_joints.verify(trial)
    print('Independent trial joint proof:',trial_proof,flush=True)
    top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));assert top
    docs=bridge.open_models(sw);support=docs['support']
    paths={Path(c.GetPathName).resolve() for c in top.GetComponents(False) if c.GetPathName}|{bridge.TOP_ASSEMBLY}
    assert all(p.is_relative_to(base) for p in paths),'Foreign CAD reference'
    loaded={Path(d.GetPathName).resolve():d for d in sw.GetDocuments if d.GetPathName}
    assert not [p for p in paths if p in loaded and loaded[p].GetSaveFlag], 'Unsaved working CAD'
    snapshot=base/'snapshots'/datetime.now().strftime('%Y%m%d-%H%M%S-before-pin-joints')
    for path in paths:
        if path.is_file():
            target=snapshot/path.relative_to(base);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    values=json.loads(bridge.STATE.read_text(encoding='utf-8'))['values']
    frame=next(c for c in top.GetComponents(True) if 'Опора шнековая' in c.Name2)
    pose_before=list(frame.Transform2.ArrayData)
    original_plane=float(support.Parameter('D1@ПЛОСКОСТЬ3').SystemValue)
    manager=support.GetEquationMgr
    activate(support)
    expressions=[f'"Наклон корпуса от горизонтали" = {values["incline"]:g}градусов',
                 '"Наклон рамы от горизонтали" = 15градусов',
                 '"D1@ПЛОСКОСТЬ3" = "Наклон корпуса от горизонтали" - "Наклон рамы от горизонтали"']
    assert not any('Наклон корпуса от горизонтали' in manager.Equation(i) for i in range(manager.GetCount))
    for expression in expressions:
        index=manager.Add2(-1,expression,True);assert index>=0,expression;equations_added.append(index)
    manager.EvaluateAll
    assert support.ForceRebuild3(False)
    activate(top)
    for name in ('Угол1','Совпадение111'):
        feature=top.FeatureByName(name);assert feature
        assert feature.SetSuppression2(0,1,None);suppressed.append((top,feature,name))
    components=list(top.GetComponents(False))
    bush=next(c for c in components if ".25.00.05 'Втулка'" in c.Name2 and c.Name2.endswith('-2'))
    ear3=next(c for c in components if ".21.00.11 'Ухо'" in c.Name2 and c.Name2.endswith('-3'))
    ear4=next(c for c in components if ".21.00.11 'Ухо'" in c.Name2 and c.Name2.endswith('-4'))
    concentric(top,bush,ear3,18,10.8,'Втулка 2 — ухо 3 — соосность')
    face1,_,normal1=pin_joints.seating_face(bush,.03)
    face2,_,normal2=pin_joints.seating_face(ear4,.03)
    data=top.CreateMateData(0)
    data.MateAlignment=0 if sum(normal1[i]*normal2[i] for i in range(3))>0 else 1
    data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,
        [bush.GetCorrespondingEntity(face1),ear4.GetCorrespondingEntity(face2)])
    seat=top.CreateMate(data);assert seat
    seat.Name='Втулка 2 — ухо 4 — торцевая посадка';created.append((top,seat))
    activate(support)
    old=support.FeatureByName('Совпадение17');assert old
    assert old.SetSuppression2(0,1,None);suppressed.append((support,old,'Совпадение17'))
    components=list(support.GetComponents(True))
    bush=next(c for c in components if ".25.00.05 'Втулка'" in c.Name2 and c.Name2.endswith('-2'))
    brace=next(c for c in components if ".25.00.09 'Подкос 1'" in c.Name2)
    concentric(support,brace,bush,18,18,'Подкос 1 — втулка 2 — соосность')
    assert support.ForceRebuild3(False)
    activate(top);assert top.ForceRebuild3(False)
    issues=bridge.model_issues(sw,top);print('Working model issues:',issues,flush=True)
    assert issues==(0,0,[]),issues
    proof=pin_joints.verify(top)
    print('Working axes and seats:',proof,flush=True)
    intersections=bridge.interference_issues(top)
    print('Intersections:',intersections,flush=True);assert not intersections
    pose_after=list(frame.Transform2.ArrayData)
    assert max(abs(a-b) for a,b in zip(pose_before,pose_after))<1e-7,(pose_before,pose_after)
    for document,feature,name in suppressed:
        feature.Name='Архив — '+name
    activate(top);assert top.Save3(13,errors,warnings) and not errors.value
    output={'timestamp':datetime.now().astimezone().isoformat(timespec='seconds'),
            'snapshot':str(snapshot),'issues':issues,'interferences':intersections,
            'joints':proof,'equations':expressions,'frame_pose_before':pose_before,
            'frame_pose_after':pose_after,'archived_mates':[name for _,_,name in suppressed],
            'trial':trial_path,'working_root':str(bridge.TOP_ASSEMBLY)}
    (base/'pin_joint_repair_20261005.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Working joint repair saved',flush=True)
except Exception:
    if created or equations_added:
        for document,feature in reversed(created):
            activate(document);document.ClearSelection2(True)
            assert feature.Select2(False,0);assert document.Extension.DeleteSelection2(0)
        for document,feature,name in suppressed:
            activate(document);feature.Name=name;assert feature.SetSuppression2(1,1,None)
        activate(support)
        for index in reversed(equations_added):manager.Delete(index)
        support.Parameter('D1@ПЛОСКОСТЬ3').SystemValue=original_plane
        manager.EvaluateAll;assert support.ForceRebuild3(False)
        activate(top);assert top.ForceRebuild3(False)
        assert bridge.model_issues(sw,top)==(0,0,[]) and not bridge.interference_issues(top)
        assert top.Save3(13,errors,warnings) and not errors.value
        print('Original working model restored',flush=True)
    raise
finally:
    sw.ActivateDoc3(str(bridge.TOP_ASSEMBLY),False,2,errors);sw.CommandInProgress=previous
