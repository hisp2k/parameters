import win32com.client as win32
from pathlib import Path
sw=win32.Dispatch('SldWorks.Application'); sw.Visible=True
tpl=r'C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\gost-part.prtdot'
doc=sw.NewDocument(tpl,0,0,0)
def features():
    a=[]; f=doc.FirstFeature
    while f:
        a.append(f); f=f.GetNextFeature
    return a
top=next(f for f in features() if f.Name=='Сверху')
doc.ClearSelection2(True); print('select top',top.Select2(False,0))
doc.SketchManager.InsertSketch(True)
doc.SketchManager.CreateCornerRectangle(-.425,-.425,0,.425,.425,0)
doc.SketchManager.InsertSketch(True)
sk1=[f for f in features() if f.GetTypeName2=='ProfileFeature'][-1]
print('sk1',sk1.Name)
doc.ClearSelection2(True); top.Select2(False,0)
plane=doc.FeatureManager.InsertRefPlane(8,1.0,0,0,0,0)
print('plane',plane.Name if plane else None)
doc.ClearSelection2(True); plane.Select2(False,0)
doc.SketchManager.InsertSketch(True)
doc.SketchManager.CreateCornerRectangle(-.45,-.45,0,.45,.45,0)
doc.SketchManager.InsertSketch(True)
sk2=[f for f in features() if f.GetTypeName2=='ProfileFeature'][-1]
print('sk2',sk2.Name)
doc.ClearSelection2(True)
print('sel1',sk1.Select2(False,1),'sel2',sk2.Select2(True,1))
loft=doc.FeatureManager.InsertProtrusionBlend2(False,False,False,1,0,0,1,1,True,True,False,0,0,0,True,True,True,0)
print('loft',loft.Name if loft else None)
print('bodies',len(doc.GetBodies2(0,False) or []))
for face in doc.GetBodies2(0,False)[0].GetFaces():
    print('face',face.GetArea,face.Normal)
doc.ClearSelection2(True)
topface=next(f for f in doc.GetBodies2(0,False)[0].GetFaces() if f.Normal[1]>.9)
seldata=doc.SelectionManager.CreateSelectData; seldata.Mark=1
print('select top face',topface.Select4(False,seldata))
doc.InsertFeatureShell(.002,False)
print('after shell',[(f.GetTypeName2,f.Name.encode('unicode_escape').decode()) for f in features()[-5:]])
print('faces',len(doc.GetBodies2(0,False)[0].GetFaces()))
out=Path('outputs/test_loft.SLDPRT').resolve(); out.parent.mkdir(exist_ok=True)
print('save',doc.SaveAs3(str(out),0,1))
