from pathlib import Path
import pythoncom
import win32com.client as w

ROOT=Path('work/lower_interference_trial').resolve()
sw=w.GetActiveObject('SldWorks.Application')
doc=sw.GetOpenDocumentByName(str(ROOT/'Обойма нижняя — контроль интерференций.SLDASM'))
err=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
sw.ActivateDoc3(doc.GetTitle,False,2,err)
if err.value:raise RuntimeError('Activation failed')
rebuild=doc.EditRebuild3
if callable(rebuild):rebuild()

def mates():
    top=doc.FirstFeature
    while top:
        if top.GetTypeName2=='MateGroup':
            f=top.GetFirstSubFeature
            while f:
                yield f
                f=f.GetNextSubFeature
        top=top.GetNextFeature

def remove(f):
    doc.ClearSelection2(True)
    if not f.Select2(False,0) or not doc.Extension.DeleteSelection2(0):raise RuntimeError('Mate delete failed')

def add(a,b,kind,alignment,name,distance=None,flip=False):
    doc.ClearSelection2(True);sel=doc.SelectionManager.CreateSelectData;sel.Mark=1
    if not a.Select4(False,sel) or not b.Select4(True,sel):raise RuntimeError('Mate faces not selected')
    data=doc.CreateMateData(kind);data.MateAlignment=alignment
    if distance is not None:data.Distance=distance;data.FlipDimension=flip
    new=doc.CreateMate(data)
    if new is None or new.GetErrorCode:raise RuntimeError(f'Invalid new mate {name}')
    new.Name=name
    return new

def cylinder(comp,radius):
    faces=[face for body in comp.GetModelDoc2.GetBodies2(0,True) for face in body.GetFaces()
           if face.GetSurface.IsCylinder and abs(face.GetSurface.CylinderParams[6]-radius)<1e-7]
    if not faces:raise RuntimeError('Cylinder missing')
    return comp.GetCorrespondingEntity(faces[0])

def plane(comp,z):
    faces=[face for body in comp.GetModelDoc2.GetBodies2(0,True) for face in body.GetFaces()
           if face.GetSurface.IsPlane and abs(face.GetBox[2]-z)<1e-7 and abs(face.GetBox[5]-z)<1e-7]
    if len(faces)!=1:raise RuntimeError(f'Ambiguous plane {z}: {len(faces)}')
    return comp.GetCorrespondingEntity(faces[0])

oldseal=next(c for c in doc.GetComponents(False) if c.Name2.startswith('Манжета 2 -50'))
oldpos=list(oldseal.Transform2.ArrayData)
for name in ['Совпадение19','Концентричный17']:
    existing=next((f for f in mates() if f.Name==name),None)
    if existing:remove(existing)
doc.ClearSelection2(True)
selection=doc.SelectionManager.CreateSelectData
if not oldseal.Select4(False,selection,False):raise RuntimeError('Seal component selection failed')
sealpath=ROOT/'Манжета 50x70x10 ГОСТ 8752-79 — габаритная модель.SLDPRT'
if not doc.ReplaceComponents2(str(sealpath),'',False,0,False):raise RuntimeError('Seal replacement failed')
seal=next(c for c in doc.GetComponents(False) if Path(c.GetPathName)==sealpath)
housing=next(c for c in doc.GetComponents(False) if "'Обойма'_NI" in c.Name2)
print('housing origin',housing.Transform2.ArrayData[9:12],flush=True)
add(cylinder(housing,.035),cylinder(seal,.035),1,1,'Манжета 50x70 — соосность')
add(plane(housing,-.024),plane(seal,0.),0,1,'Манжета 10 — посадочный торец')
print('seal',seal.GetBox(False,False),flush=True)

for oldname,nominal,expected_delta in [('Совпадение10',80,.000075),('Совпадение12',70,-.000075)]:
    old=next(f for f in mates() if f.Name==oldname)
    faces=old.GetDefinition.EntitiesToMate
    alignment=old.GetDefinition.MateAlignment
    ring=next(c for c in doc.GetComponents(False) if c.Name2.startswith(f'Стопорное кольцо D{nominal} '))
    before=list(ring.Transform2.ArrayData)[10]
    if not old.SetSuppression2(0,1,None):raise RuntimeError('Old ring mate suppression failed')
    name=f'Кольцо D{nominal} — осевой зазор 0.075'
    new=add(faces[0],faces[1],5,alignment,name,.000075)
    delta=list(ring.Transform2.ArrayData)[10]-before
    if abs(delta-expected_delta)>1e-6:
        remove(new)
        new=add(faces[0],faces[1],5,alignment,name,.000075,True)
        delta=list(ring.Transform2.ArrayData)[10]-before
    print(name,'delta_mm',delta*1000,flush=True)
    if abs(delta-expected_delta)>1e-6:raise RuntimeError('Ring clearance direction incorrect')
    remove(old)

rebuild=doc.EditRebuild3
if callable(rebuild):rebuild()
errors=[(f.Name,int(f.GetErrorCode)) for f in mates() if f.GetErrorCode]
print('remaining mate errors',errors,flush=True)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
print('saved',doc.Save3(1,e,q),e.value,q.value,flush=True)
