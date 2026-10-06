exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
support=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2)
backup=base/'snapshots'/'20261004-all-interferences-before'/Path(support.GetPathName).relative_to(base)
import shutil
trial=Path('work/Опора — исходные связи.SLDASM').resolve();shutil.copy2(backup,trial)
spec=sw.GetOpenDocSpec(str(trial));spec.DocumentType=2;spec.Silent=True;spec.ReadOnly=True;d=sw.OpenDoc7(spec)
for m in mates(d):
 if m.Name not in ['Расстояние5','Расстояние6']:continue
 print(m.Name)
 for i,ref in enumerate(m.GetDefinition.EntitiesToMate):
  print(i,ref)
  if ref:
   for attr in ['Name','GetTypeName2','GetSpecificFeature2','GetCurve','GetSurface','GetRefAxisParams']:
    try:print(attr,getattr(ref,attr))
    except Exception:pass


