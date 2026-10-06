exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
trial=sw.GetOpenDocumentByName(str(Path('work/upper_interference_trial/Обойма верхняя — контроль.SLDASM').resolve()))
dest=base/'CAD_восстановленный'/'Верхняя обойма — исправлено 20261004';dest.mkdir(exist_ok=True);target=dest/"PT.SHT.01.22.00.00 СБ 'Обойма верхняя' — исправлено.SLDASM"
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(trial.GetTitle,False,2,e)
assert trial.Extension.SaveAs2(str(target),0,7,w.VARIANT(pythoncom.VT_DISPATCH,None),'_UR04',False,e,q)
spec=sw.GetOpenDocSpec(str(target));spec.DocumentType=2;spec.Silent=True;new=sw.OpenDoc7(spec)
assert new and all(Path(c.GetPathName).is_relative_to(dest) for c in new.GetComponents(False))
sw.ActivateDoc3(doc.GetTitle,False,2,e);upper=next(c for c in doc.GetComponents(True) if 'Обойма верхняя' in c.Name2);before=list(upper.Transform2.ArrayData)
doc.ClearSelection2(True);assert upper.Select4(False,doc.SelectionManager.CreateSelectData,False);assert doc.ReplaceComponents2(str(target),'',False,0,True)
doc.ForceRebuild3(False);c=next(c for c in doc.GetComponents(True) if c.GetPathName==str(target));shift=max(abs(a-b) for a,b in zip(before,c.Transform2.ArrayData));errors=[(m.Name,m.GetErrorCode) for m in mates(doc) if m.GetErrorCode]
print('position change',shift,'mate errors',errors,'components',len(doc.GetComponents(False)),flush=True);assert shift<1e-7 and not errors and len(doc.GetComponents(False))==205
print('save',doc.Save3(1,e,q),e.value,q.value,flush=True)
