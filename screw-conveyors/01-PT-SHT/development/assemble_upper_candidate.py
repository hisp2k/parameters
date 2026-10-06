from pathlib import Path
import pythoncom
import win32com.client as w

ROOT=Path('work/upper_interference_trial').resolve()
sw=w.GetActiveObject('SldWorks.Application')
doc=sw.GetOpenDocumentByName(str(ROOT/'Обойма верхняя — контроль.SLDASM'))
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
    data=doc.CreateMateData(kind);data.MateAlignment=alignment;data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[a,b])
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

import shutil
housing=next(c for c in doc.GetComponents(False) if "'Обойма'_UI_R04" in c.Name2)
oldseal=next(c for c in doc.GetComponents(False) if c.Name2.startswith('Манжета 2 -50'))
for f in list(mates()):
 if any(f.GetSpecificFeature2.MateEntity(i).ReferenceComponent.Name2==oldseal.Name2 for i in (0,1)):remove(f)
sealpath=ROOT/'Манжета 50x70x10 — контроль верхней обоймы.SLDPRT'
source=next(Path('outputs/Шнек 1 — параметрическая модель/CAD_восстановленный/Нижняя обойма — исправлено 20261004').glob('Манжета 50x70x10*SLDPRT')).resolve();shutil.copy2(source,sealpath)
doc.ClearSelection2(True);assert oldseal.Select4(False,doc.SelectionManager.CreateSelectData,False);assert doc.ReplaceComponents2(str(sealpath),'',False,0,False)
seal=next(c for c in doc.GetComponents(False) if Path(c.GetPathName)==sealpath)
add(cylinder(housing,.035),cylinder(seal,.035),1,1,'Манжета — соосность')
add(plane(housing,-.024),plane(seal,0.),0,1,'Манжета — посадка 10 мм')
for nominal,z,rz,target in [(70,-.014,0.,-.013925),(80,-.069,-.002,-.069075)]:
 ring=next(c for c in doc.GetComponents(False) if c.Name2.startswith(f'Стопорное кольцо D{nominal} '))
 involved=[f for f in mates() if any(f.GetSpecificFeature2.MateEntity(i).ReferenceComponent.Name2==ring.Name2 for i in (0,1))]
 if nominal==70:
  old=next(f for f in involved if f.GetTypeName2=='MateConcentric');alignment=old.GetDefinition.MateAlignment;old.SetSuppression2(0,1,None)
  add(cylinder(housing,.035),cylinder(ring,.0365),1,alignment,'Кольцо D70 — соосность наружной окружности');remove(old)
 old=next(f for f in involved if f.GetTypeName2=='MateCoincident');alignment=old.GetDefinition.MateAlignment;old.SetSuppression2(0,1,None)
 a,b=plane(housing,z),plane(ring,rz)
 new=add(a,b,5,alignment,f'Кольцо D{nominal} — осевой зазор 0.075',.000075)
 def position():
  t=list(ring.Transform2.ArrayData);h=list(housing.Transform2.ArrayData)
  p=[rz*t[6+i]+t[9+i]-h[9+i] for i in range(3)]
  return sum(p[i]*h[6+i] for i in range(3))
 if abs(position()-target)>1e-6:
  definition=new.GetDefinition;definition.FlipDimension=True;assert new.ModifyDefinition(definition,doc,None)
 print('ring',nominal,position(),target,flush=True)
 assert abs(position()-target)<1e-6
 remove(old)
doc.ForceRebuild3(False);errors=[(f.Name,f.GetErrorCode) for f in mates() if f.GetErrorCode];print('errors',errors,flush=True);assert not errors
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);print('saved',doc.Save3(1,e,q),e.value,q.value,flush=True)
