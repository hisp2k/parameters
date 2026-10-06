from pathlib import Path
import sys
import pythoncom
import win32com.client as w
sw=w.GetActiveObject('SldWorks.Application')
title=sys.argv[1] if len(sys.argv)>1 else 'Обойма нижняя — испытание сопряжений.SLDASM'
doc=next(d for d in sw.GetDocuments if d.GetTitle==title)
err=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
sw.ActivateDoc2(doc.GetTitle,False,err)
f=doc.FirstFeature
old=None
while f:
    if f.GetTypeName2=='MateGroup':
        m=f.GetFirstSubFeature
        while m:
            if m.Name=='Концентричный38':
                doc.ClearSelection2(True);m.Select2(False,0);doc.Extension.DeleteSelection2(0)
                break
            if m.Name=='Концентричный19':old=m
            m=m.GetNextSubFeature
    f=f.GetNextFeature
if old is None:raise RuntimeError('Mate missing')
ring=old.GetSpecificFeature2.MateEntity(1).ReferenceComponent
faces=[face for body in ring.GetModelDoc2.GetBodies2(0,True) for face in body.GetFaces()
       if face.GetSurface.IsCylinder and abs(face.GetSurface.CylinderParams[6]-.0365)<1e-7]
print('faces',len(faces),'before',ring.Transform2.ArrayData[9:12],flush=True)
if not faces:raise RuntimeError('Outer ring surface missing')
doc.ClearSelection2(True)
sel=doc.SelectionManager.CreateSelectData;sel.Mark=1
a=old.GetDefinition.EntitiesToMate[0];b=ring.GetCorrespondingEntity(faces[0])
alignment=old.GetDefinition.MateAlignment
if not old.SetSuppression2(0,1,None):raise RuntimeError('Suppress failed')
sa=a.Select4(False,sel);sb=b.Select4(True,sel)
print('selected',sa,sb,'active',sw.ActiveDoc.GetTitle,flush=True)
if not sa or not sb:raise RuntimeError('Select failed')
data=doc.CreateMateData(1);data.MateAlignment=alignment
new=doc.CreateMate(data)
if new is None or new.GetErrorCode:raise RuntimeError('New mate invalid')
doc.ClearSelection2(True)
if not old.Select2(False,0) or not doc.Extension.DeleteSelection2(0):raise RuntimeError('Delete failed')
if callable(doc.EditRebuild3):doc.EditRebuild3()
print('after',ring.Transform2.ArrayData[9:12],flush=True)
