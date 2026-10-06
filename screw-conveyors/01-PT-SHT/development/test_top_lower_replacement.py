from pathlib import Path
import json,shutil
import pythoncom
import win32com.client as w
sw=w.GetActiveObject('SldWorks.Application');base=Path('outputs/Шнек 1 — параметрическая модель').resolve()
original=base/'CAD_восстановленный'/"PT.SHT.01.20.00.00 СБ 'Шнек 1' — восстановлено.SLDASM"
replacement=base/'CAD_восстановленный'/'Нижняя обойма — исправлено 20261004'/"PT.SHT.01.23.00.00 СБ 'Обойма нижняя' — исправлено.SLDASM"
source=sw.GetOpenDocumentByName(str(original));e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
trial=Path('work/Шнек — проверка замены нижней обоймы.SLDASM').resolve()
sw.ActivateDoc3(source.GetTitle,False,2,e)
if not source.Extension.SaveAs2(str(trial),0,3,w.VARIANT(pythoncom.VT_DISPATCH,None),'',False,e,q):raise RuntimeError('Top copy failed')
spec=sw.GetOpenDocSpec(str(trial));spec.DocumentType=2;spec.Silent=True
doc=sw.OpenDoc7(spec)
if not doc or spec.Error:raise RuntimeError('Top trial open failed')
def errors(d):
 result=[];f=d.FirstFeature
 while f:
  if f.GetErrorCode and f.GetTypeName2!='MateGroup':result.append((f.Name,f.GetTypeName2,int(f.GetErrorCode)))
  if f.GetTypeName2=='MateGroup':
   m=f.GetFirstSubFeature
   while m:
    if m.GetErrorCode:result.append((m.Name,m.GetTypeName2,int(m.GetErrorCode)))
    m=m.GetNextSubFeature
  f=f.GetNextFeature
 return result
before=errors(doc)
sw.ActivateDoc3(doc.GetTitle,False,2,e)
c=next(c for c in doc.GetComponents(True) if 'Обойма нижняя' in c.GetPathName)
transform=list(c.Transform2.ArrayData)
doc.ClearSelection2(True)
if not c.Select4(False,doc.SelectionManager.CreateSelectData,False):raise RuntimeError('Component select failed')
print('replace',doc.ReplaceComponents2(str(replacement),'',False,0,True),flush=True)
doc.ForceRebuild3(False)
after=errors(doc)
c=next(c for c in doc.GetComponents(True) if c.GetPathName==str(replacement))
shift=max(abs(a-b) for a,b in zip(transform,c.Transform2.ArrayData))
print('before',before,'after',after,'transform_delta',shift,flush=True)
print('components',len(doc.GetComponents(False)),flush=True)
if set(after)-set(before) or shift>1e-7:raise RuntimeError('Top replacement invalid')
print('save',doc.Save3(1,e,q),e.value,q.value,flush=True)
Path('work/top_lower_replacement_test.json').write_text(json.dumps({'before':before,'after':after,'transform_delta':shift,'components':len(doc.GetComponents(False))},ensure_ascii=False,indent=2),encoding='utf-8')
