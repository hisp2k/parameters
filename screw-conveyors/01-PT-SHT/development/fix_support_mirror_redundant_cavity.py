exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
import sys,shutil;sys.path.insert(0,str(base));import bridge
s=sw.GetOpenDocumentByName(str(bridge.FILES['support']));c=next(c for c in s.GetComponents(True) if "09-01 'Подкос" in c.Name2);part=c.GetModelDoc2
backup=base/'snapshots/20261004-before-support-mirror-fix';backup.mkdir(parents=True,exist_ok=True)
for p in [Path(part.GetPathName),bridge.FILES['support']]:shutil.copy2(p,backup/p.name)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
before=sum(b.GetMassProperties(1)[3] for b in part.GetBodies2(0,True));transform=list(c.Transform2.ArrayData)
sw.ActivateDoc3(part.GetTitle,False,2,e);f=part.FeatureByName('Подрезка подкоса по стойкам и балкам');assert f.GetErrorCode==71
part.ClearSelection2(True);assert f.Select2(False,0);assert part.Extension.DeleteSelection2(0);part.ForceRebuild3(False)
after=sum(b.GetMassProperties(1)[3] for b in part.GetBodies2(0,True));assert abs(before-after)<1e-12,(before,after);assert part.Save3(1,e,q)
sw.ActivateDoc3(s.GetTitle,False,2,e);s.ForceRebuild3(False);assert max(abs(a-b) for a,b in zip(transform,c.Transform2.ArrayData))<1e-10;assert s.Save3(1,e,q)
f=s.FirstFeature;errors=[]
while f:
 if f.GetErrorCode:errors.append((f.Name,f.GetErrorCode))
 f=f.GetNextFeature
print('support errors',errors,'volume difference mm3',(after-before)*1e9,flush=True);assert not errors
sw.ActivateDoc3(doc.GetTitle,False,2,e);doc.ForceRebuild3(False);assert doc.Save3(1,e,q);print('saved root',flush=True)
