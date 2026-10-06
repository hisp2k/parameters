exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
import shutil
tube=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Труба в сборе' in c.Name2)
original=base/'snapshots'/'20261004-all-interferences-before'/Path(tube.GetPathName).relative_to(base);trial=Path('work/Труба — исходные связи.SLDASM').resolve();shutil.copy2(original,trial)
spec=sw.GetOpenDocSpec(str(trial));spec.DocumentType=2;spec.Silent=True;spec.ReadOnly=True;old=sw.OpenDoc7(spec)
print('oldtube',len(old.GetComponents(False)),flush=True)
for c in old.GetComponents(True):
 if 'Сбрасыватель' in c.Name2:print(c.Name2,c.GetPathName,list(c.Transform2.ArrayData),flush=True)
for m in mates(old):
 if m.Name in ['Расстояние26','Расстояние27']:print(m.Name,m.GetTypeName2,m.GetDefinition.Distance,[m.GetSpecificFeature2.MateEntity(i).ReferenceComponent.Name2 for i in (0,1)],flush=True)
