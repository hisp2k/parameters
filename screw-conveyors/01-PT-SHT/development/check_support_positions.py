exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
import shutil
support=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2)
original=base/'snapshots'/'20261004-all-interferences-before'/Path(support.GetPathName).relative_to(base);trial=Path('work/Опора — сравнение положения.SLDASM').resolve();shutil.copy2(original,trial)
spec=sw.GetOpenDocSpec(str(trial));spec.DocumentType=2;spec.Silent=True;spec.ReadOnly=True;old=sw.OpenDoc7(spec)
for c in support.GetComponents(True):
 if c.Name2.startswith('PT.SHT.01.01.02.03'):
  oc=next(o for o in old.GetComponents(True) if o.Name2==c.Name2)
  print(c.Name2,'before',list(oc.Transform2.ArrayData),'after',list(c.Transform2.ArrayData),flush=True)
