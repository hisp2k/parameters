exec(open('work/assemble_lower_candidate.py',encoding='utf-8').read().split('oldseal=next')[0])
import json,shutil
base=Path('outputs/Шнек 1 — параметрическая модель').resolve()
destination=base/'CAD_восстановленный'/'Нижняя обойма — исправлено 20261004'
destination.mkdir(exist_ok=True)
target=destination/"PT.SHT.01.23.00.00 СБ 'Обойма нижняя' — исправлено.SLDASM"
errors=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);warnings=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
empty=w.VARIANT(pythoncom.VT_DISPATCH,None)
print('copy',doc.Extension.SaveAs2(str(target),0,7,empty,'_R04',False,errors,warnings),errors.value,warnings.value,flush=True)
spec=sw.GetOpenDocSpec(str(target));spec.DocumentType=2;spec.Silent=True
newdoc=sw.OpenDoc7(spec)
if newdoc is None or spec.Error:raise RuntimeError('Copy open failed')
references=[{'component':c.Name2,'path':c.GetPathName} for c in newdoc.GetComponents(False)]
external=[r for r in references if not Path(r['path']).is_relative_to(destination)]
print('components',len(references),'external',external,flush=True)
(destination/'references.json').write_text(json.dumps(references,ensure_ascii=False,indent=2),encoding='utf-8')
if external:raise RuntimeError('External references')
