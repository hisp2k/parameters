from pathlib import Path
from datetime import datetime
import sys,json,math
import pythoncom,win32com.client as w
from support_pipe_joint_helpers import design,verify,plane_face,point,direction
from brace_bypass_20261005 import rectangle_feature
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base))
import bridge,pin_joints
sw=w.GetActiveObject('SldWorks.Application');previous=sw.CommandInProgress;sw.CommandInProgress=True
errors=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);warnings=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)

def activate(document):
    sw.ActivateDoc3(document.GetPathName,False,2,errors);assert not errors.value

def expressions(support):
    brace,post,expected=design(support)
    stem=Path(brace.GetPathName).stem
    projection='Проекция длины прямого подкоса';join='Координата стыка прямого подкоса'
    axis='("Наклон корпуса от горизонтали" - "Наклон рамы от горизонтали")'
    return brace,post,expected,[
        f'"{projection}" = (600мм * cos({axis}) - 20мм) / cos(23градусов)',
        f'"{join}" = -600мм * sin({axis}) - "{projection}" * sin(23градусов)',
        f'"D1@Плоскость2@{stem}<1>.Part" = "{projection}"',
        f'"D1@Плоскость1@{stem}<1>.Part" = atn(-"{join}" * sin(15градусов) / cos(15градусов) / "{projection}")',
    ]

def install(root):
    support=next(c.GetModelDoc2 for c in root.GetComponents(True) if 'Опора шнековая' in c.Name2)
    brace,post,expected,equations=expressions(support)
    activate(support);mgr=support.GetEquationMgr
    mgr.AngularEquationUnits=1
    cavity=brace.GetModelDoc2.FeatureByName('Подрезка подкоса по стойкам и балкам')
    assert cavity
    activate(brace.GetModelDoc2);assert cavity.SetSuppression2(0,1,None)
    activate(support)
    assert not any('Проекция длины прямого подкоса' in mgr.Equation(i) for i in range(mgr.GetCount))
    added=[]
    for expression in equations:
        index=mgr.Add2(-1,expression,True);assert index>=0,expression;added.append(index)
    mgr.EvaluateAll
    initial_rebuild=support.ForceRebuild3(False)
    part=brace.GetModelDoc2
    dims={'length':float(part.Parameter('D1@Плоскость2').SystemValue),'angle':float(part.Parameter('D1@Плоскость1').SystemValue)}
    print('Derived dimensions',dims,'expected',expected,flush=True)
    if not initial_rebuild:
        print('Initial rebuild issues',bridge.model_issues(sw,support),flush=True)
        activate(root);root.ForceRebuild3(False);activate(support);print('Retry support rebuild',support.ForceRebuild3(False),flush=True)
    assert abs(dims['length']-expected['length_plane_m'])<1e-8
    assert abs(dims['angle']-expected['flare_angle_rad'])<1e-8
    old=support.FeatureByName('Параллельность2');assert old;assert old.SetSuppression2(0,1,None)
    endface,_=plane_face(brace,-.020);postface,_=plane_face(post,-.020)
    # A point on the real end face gives one independent joint constraint;
    # the pin axis and front-plane offset retain the other degrees of freedom.
    vertices=[]
    for edge in endface.GetEdges:
        for vertex in (edge.GetStartVertex,edge.GetEndVertex):
            if vertex:vertices.append(vertex)
    assert vertices
    vertex=vertices[0]
    data=support.CreateMateData(0);data.MateAlignment=0
    data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,
        [brace.GetCorrespondingEntity(vertex),post.GetCorrespondingEntity(postface)])
    mate=support.CreateMate(data);assert mate
    mate.Name='Подкос 1 — стойка 1 — стык труб';print('New mate',mate.GetErrorCode,flush=True)
    activate(part)
    relief_name='Зазор у уха — местная выборка'
    rectangle_feature(part,relief_name,-.0165,.002,.0145,.035,True,.020)
    part_mgr=part.GetEquationMgr;part_mgr.AngularEquationUnits=1
    relief_equation=f'"{relief_name}" = iif("D1@Плоскость1" > 15градусов, "unsuppressed", "suppressed")'
    assert part_mgr.Add2(-1,relief_equation,True)>=0
    part_mgr.EvaluateAll
    assert part.ForceRebuild3(False)
    activate(support)
    assert support.ForceRebuild3(False)
    bridge.refresh_cavities(sw,support);assert support.ForceRebuild3(False)
    activate(root);assert root.ForceRebuild3(False)
    issues=bridge.model_issues(sw,root);print('Issues',issues,flush=True)
    joints=pin_joints.verify(root);connections=verify(support);print('Pipe connections',connections,flush=True)
    intersections=bridge.interference_issues(root);print('Intersections',intersections,flush=True)
    assert issues==(0,0,[]) and connections['ok'] and not intersections
    endface,_=plane_face(brace,-.020)
    old.Name='Архив — Параллельность2'
    return {'equations':equations,'expected_dimensions':expected,'actual_dimensions':dims,
            'issues':issues,'pin_joints':joints,'pipe_joints':connections,'interferences':intersections,
            'mate':mate.Name,'relief_equation':relief_equation,'root':root.GetPathName}

if __name__=='__main__':
    try:
        path=json.loads((base/'straight_brace_restore_20261005.json').read_text(encoding='utf-8'))['trial_root']
        folder=Path(path).parent
        old_paths=[d.GetPathName for d in sw.GetDocuments if d.GetPathName and Path(d.GetPathName).is_relative_to(folder)]
        for old_path in sorted(old_paths,key=lambda p:Path(p).suffix.upper()!='.SLDASM'):
            if sw.GetOpenDocumentByName(old_path):sw.CloseDoc(old_path)
        root=sw.GetOpenDocumentByName(path)
        if root is None:
            spec=sw.GetOpenDocSpec(path);spec.DocumentType=2;spec.Silent=True;root=sw.OpenDoc7(spec)
        assert root
        folder=Path(path).parent
        assert all(Path(c.GetPathName).is_relative_to(folder) for c in root.GetComponents(False) if c.GetPathName)
        print('Independent copy opened',path,flush=True)
        proof=install(root)
        assert root.Save3(13,errors,warnings) and not errors.value
        (base/'support_pipe_joint_trial_20261005.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Pipe joint trial saved',flush=True)
    finally:
        sw.ActivateDoc3(str(bridge.TOP_ASSEMBLY),False,2,errors);sw.CommandInProgress=previous
