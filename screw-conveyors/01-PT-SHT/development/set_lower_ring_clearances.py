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
    data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[a,b])
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

housing=next(c for c in doc.GetComponents(False) if "'Обойма'_NI" in c.Name2)
for oldname,nominal,z,rz,delta in [('Совпадение10',80,-.069,-.002,.000075),('Совпадение12',70,-.014,0.,-.000075)]:
    old=next(f for f in mates() if f.Name==oldname)
    alignment=old.GetDefinition.MateAlignment
    ring=next(c for c in doc.GetComponents(False) if c.Name2.startswith(f'Стопорное кольцо D{nominal} '))
    before=list(ring.Transform2.ArrayData)[10]
    old.SetSuppression2(0,1,None)
    a,b=plane(housing,z),plane(ring,rz)
    doc.ClearSelection2(True);sel=doc.SelectionManager.CreateSelectData;sel.Mark=1
    print('selected',a.Select4(False,sel),b.Select4(True,sel),flush=True)
    data=doc.CreateMateData(5);data.IsAdvancedMate=False;data.Distance=.000075;data.MateAlignment=alignment;data.FlipDimension=False
    print('data',data.Distance,data.IsAdvancedMate,data.MateAlignment,flush=True)
    data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[a,b])
    new=doc.CreateMate(data)
    print('new',new,flush=True)
    if new is None:raise RuntimeError('Distance failed')
    new.Name=f'Кольцо D{nominal} — осевой зазор 0.075'
    actual=list(ring.Transform2.ArrayData)[10]-before
    if abs(actual-delta)>1e-6:
        definition=new.GetDefinition;definition.FlipDimension=True
        print('flip',new.ModifyDefinition(definition,doc,None),flush=True)
        actual=list(ring.Transform2.ArrayData)[10]-before
    print('delta_mm',actual*1000,'error',new.GetErrorCode,flush=True)
    if abs(actual-delta)>1e-6 or new.GetErrorCode:raise RuntimeError('Wrong clearance')
    remove(old)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
print('save',doc.Save3(1,e,q),e.value,q.value,flush=True)
