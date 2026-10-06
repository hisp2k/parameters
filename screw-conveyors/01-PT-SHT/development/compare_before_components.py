exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
import shutil
original=base/'snapshots'/'20261004-all-interferences-before'/path.relative_to(base);trial=Path('work/Шнек — исходные связи.SLDASM').resolve();shutil.copy2(original,trial)
spec=sw.GetOpenDocSpec(str(trial));spec.DocumentType=2;spec.Silent=True;spec.ReadOnly=True;old=sw.OpenDoc7(spec)
print('count',len(old.GetComponents(False)),len(doc.GetComponents(False)),flush=True)
a={c.Name2 for c in old.GetComponents(True)};b={c.Name2 for c in doc.GetComponents(True)};print('removed',a-b,'added',b-a,flush=True)
tube=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Труба в сборе' in c.Name2)
for m in mates(tube):
 if m.GetTypeName2=='MateDistanceDim':
  print(m.Name,m.GetDefinition.Distance,[m.GetSpecificFeature2.MateEntity(i).ReferenceComponent.Name2 for i in (0,1)],flush=True)
