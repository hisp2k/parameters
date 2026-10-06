"""Engineering corrections confined to the copied lower-bearing assembly."""
from pathlib import Path
import sys
import pythoncom
import win32com.client as w

ROOT=Path('work/upper_interference_trial').resolve()
print('connecting',flush=True)
sw=w.GetActiveObject('SldWorks.Application')
empty=w.VARIANT(pythoncom.VT_DISPATCH,None)

def active(path):
    d=sw.GetOpenDocumentByName(str(path))
    if d is None:
        spec=sw.GetOpenDocSpec(str(path));spec.DocumentType=1;spec.Silent=True
        d=sw.OpenDoc7(spec)
    err=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    sw.ActivateDoc3(d.GetTitle,False,2,err)
    if err.value or sw.ActiveDoc.GetPathName != d.GetPathName:
        raise RuntimeError('Could not activate exact candidate document')
    return d

def save(d):
    e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    ok=d.Save3(1,e,q)
    print('saved',d.GetTitle,ok,e.value,q.value,flush=True)
    if not ok or e.value:raise RuntimeError('Save failed')

def move_plane(d,z,delta,name,radius=None):
    found=[]
    for b in d.GetBodies2(0,True):
        for face in b.GetFaces():
            box=face.GetBox
            if face.GetSurface.IsPlane and abs(box[2]-z)<1e-7 and abs(box[5]-z)<1e-7:
                if radius is None or abs(max(abs(box[i]) for i in (0,1,3,4))-radius)<1e-5:
                    found.append(face)
    print(name,'faces',len(found),flush=True)
    if len(found)!=1:raise RuntimeError('Ambiguous planar face')
    d.ClearSelection2(True);sel=d.SelectionManager.CreateSelectData;sel.Mark=1
    if not found[0].Select4(False,sel):raise RuntimeError('Face selection failed')
    vector=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,(0.,0.,delta))
    feature=d.FeatureManager.InsertMoveFace3(1,False,0.,0.,vector,None,0,0.)
    if feature is None or feature.GetErrorCode:raise RuntimeError('Move-face operation failed')
    feature.Name=name
    d.ClearSelection2(True)
    print('created',name,flush=True)

stage=sys.argv[1]
if stage=='rings':
    for nominal,z,delta in [(70,-.0017,-.0008),(80,0.,.0005)]:
        d=active(next(ROOT.glob(f'Стопорное кольцо D{nominal} *_UI_R04.SLDPRT')))
        move_plane(d,z,delta,'Толщина 2.5 мм DIN 472')
        save(d)
elif stage=='housing':
    d=active(next(ROOT.glob("*'Обойма'_UI_R04.SLDPRT")))
    dim=d.Parameter('D1@Скругление1')
    if dim is None:raise RuntimeError('Groove fillet dimension missing')
    dim.SystemValue=.00005
    rebuild=d.EditRebuild3
    if callable(rebuild):rebuild()
    for name in ['Вырез-Вытянуть1','Вырез-Вытянуть2']:
        depth=d.Parameter('D1@'+name)
        if depth is None:raise RuntimeError('Groove depth unavailable')
        depth.SystemValue=.00265
    d.Parameter('D5@Эскиз1').SystemValue=.024
    d.Parameter('D6@Эскиз1').SystemValue=.006
    if d.GetActiveSketch2 is not None:d.SketchManager.InsertSketch(True)
    d.Parameter('D1@Плоскость1').SystemValue=.010
    rebuild=d.EditRebuild3
    if callable(rebuild):rebuild()
    save(d)
elif stage=='sleeve':
    d=active(next(ROOT.glob("*'Гильза'_UI_R04.SLDPRT")))
    dim=d.Parameter('D1@Бобышка-Вытянуть1')
    if dim is None or abs(dim.SystemValue-.021)>1e-6:raise RuntimeError('Unexpected sleeve length')
    dim.SystemValue=.0183
    rebuild=d.EditRebuild3
    if callable(rebuild):rebuild()
    save(d)
elif stage=='seal':
    target=ROOT/'Манжета 50x70x10 ГОСТ 8752-79 — габаритная модель.SLDPRT'
    if target.exists():raise RuntimeError('Seal model already exists')
    d=sw.NewDocument(r'C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\gost-part.prtdot',0,0.,0.)
    if d is None:raise RuntimeError('Could not create seal envelope')
    if not d.Extension.SelectByID2('Спереди','PLANE',0.,0.,0.,False,0,empty,0):
        raise RuntimeError('Front plane unavailable')
    sk=d.SketchManager;sk.InsertSketch(True)
    sk.CreateCircleByRadius(0.,0.,0.,.035)
    sk.CreateCircleByRadius(0.,0.,0.,.025)
    sk.InsertSketch(True)
    feature=d.FeatureManager.FeatureExtrusion2(True,False,False,0,0,.010,0.,False,False,False,False,0.,0.,False,False,False,False,True,False,True,0,0.,False)
    if feature is None or feature.GetErrorCode:raise RuntimeError('Seal envelope failed')
    feature.Name='Габарит 50x70x10 — контроль посадки'
    props=d.Extension.CustomPropertyManager('')
    props.Add3('Обозначение',30,'Манжета 2.2-50x70-5 ГОСТ 8752-79',1)
    props.Add3('Представление CAD',30,'Консервативный габарит 50x70x10; профиль кромок не моделируется',1)
    e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    ok=d.Extension.SaveAs2(str(target),0,1,empty,'',False,e,q)
    print('seal_saved',ok,e.value,q.value,flush=True)
    if not ok or e.value:raise RuntimeError('Seal save failed')
else:
    raise ValueError(stage)

