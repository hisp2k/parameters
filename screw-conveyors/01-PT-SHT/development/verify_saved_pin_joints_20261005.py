from pathlib import Path
from datetime import datetime
import json,sys
import pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base))
import bridge,pin_joints,support_pipe_joints
sw=w.GetActiveObject('SldWorks.Application');previous=sw.CommandInProgress;sw.CommandInProgress=True
try:
    paths=[Path(d.GetPathName) for d in sw.GetDocuments if d.GetPathName]
    relevant=[p for p in paths if p.is_relative_to(bridge.CAD) or p.is_relative_to(bridge.RECOVERED_CAD)
              or 'pin-joint-trial-20261005_141313' in str(p)]
    assert not [str(p) for p in relevant if sw.GetOpenDocumentByName(str(p)).GetSaveFlag], 'Unsaved CAD'
    # Only close the two verified assemblies and their dedicated references.
    for path in sorted(relevant,key=lambda p:p.suffix.upper()!='.SLDASM'):
        if sw.GetOpenDocumentByName(str(path)):sw.CloseDoc(str(path))
    assert sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY)) is None
    spec=sw.GetOpenDocSpec(str(bridge.TOP_ASSEMBLY));spec.DocumentType=2;spec.Silent=True
    top=sw.OpenDoc7(spec);assert top and not top.IsOpenedReadOnly
    assert spec.Error==0,spec.Error
    joints=pin_joints.verify(top)
    geometry=bridge.measured_geometry(top)
    state=json.loads(bridge.STATE.read_text(encoding='utf-8'))
    for key in ('working_length','tube_diameter','incline'):
        assert abs(geometry[key]-state['values'][key])<1e-4,(key,geometry)
    support=sw.GetOpenDocumentByName(str(bridge.FILES['support']))
    assert abs(float(support.Parameter('D1@ПЛОСКОСТЬ3').SystemValue)*180/3.141592653589793-40)<1e-6
    state['cad_verification']['pin_joints']=joints
    pipe_joints=support_pipe_joints.verify(support)
    state['cad_verification']['support_pipe_joints']=pipe_joints
    proof={'timestamp':datetime.now().astimezone().isoformat(timespec='seconds'),
        'reopened_from_disk':True,'load_errors':spec.Error,'geometry':geometry,'joints':joints}
    proof['support_pipe_joints']=pipe_joints
    if '--straight-braces' in sys.argv:
        braces=[]
        for component in top.GetComponents(False):
            if "'Подкос 1'" not in component.Name2:continue
            part=component.GetModelDoc2
            for name in ['Проход корпуса — выборка для 55 градусов',
                         'Полость обхода — нижний переход','Полость обхода — наружная ветвь','Полость обхода — верхний переход',
                         'Обход корпуса — нижний переход','Обход корпуса — наружная ветвь','Обход корпуса — верхний переход']:
                feature=part.FeatureByName(name)
                assert feature is None or feature.IsSuppressed,name
            bodies=list(part.GetBodies2(0,True));assert len(bodies)==1
            braces.append({'component':component.Name2,'solid_bodies':len(bodies),'bypass_inactive':True,
                           'volume_mm3':sum(body.GetMassProperties(1)[3] for body in bodies)*1e9})
        assert len(braces)==2
        proof['straight_braces']=braces
        (base/'straight_brace_saved_verification_20261005.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    (base/'pin_joint_saved_verification_20261005.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    (base/'support_pipe_joint_saved_verification_20261005.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    bridge.STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    errors=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    sw.ActivateDoc3(top.GetPathName,False,2,errors);assert not errors.value
    print(json.dumps(proof,ensure_ascii=False),flush=True)
finally:sw.CommandInProgress=previous
