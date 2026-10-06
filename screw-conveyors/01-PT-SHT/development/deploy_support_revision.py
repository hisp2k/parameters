exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
trial=sw.GetOpenDocumentByName(str(Path('work/support_collision_trial/Опора — контроль.SLDASM').resolve()))
dest=base/'CAD_восстановленный'/'Опора — исправлено 20261004';dest.mkdir(exist_ok=True)
target=dest/"PT.SHT.01.25.00.00 СБ 'Опора шнековая' — исправлено.SLDASM";assert not target.exists()
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(trial.GetTitle,False,2,e)
assert trial.Extension.SaveAs2(str(target),0,7,w.VARIANT(pythoncom.VT_DISPATCH,None),'_SPR04',False,e,q)
spec=sw.GetOpenDocSpec(str(target));spec.DocumentType=2;spec.Silent=True;new=sw.OpenDoc7(spec);assert new
assert all(Path(c.GetPathName).is_relative_to(dest) for c in new.GetComponents(False))
assert 'support_collision_trial' not in str(new.GetDependencies2(True,True,False))
sw.ActivateDoc3(doc.GetTitle,False,2,e);old=next(c for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2);before=list(old.Transform2.ArrayData)
doc.ClearSelection2(True);assert old.Select4(False,doc.SelectionManager.CreateSelectData,False);assert doc.ReplaceComponents2(str(target),'',False,0,True)
doc.ForceRebuild3(False);c=next(c for c in doc.GetComponents(True) if Path(c.GetPathName)==target)
errors=[(m.Name,m.GetErrorCode) for m in mates(doc) if m.GetErrorCode];print('errors',errors,flush=True);assert not errors
assert max(abs(a-b) for a,b in zip(before,c.Transform2.ArrayData))<1e-7;assert doc.Save3(1,e,q);print('saved support and top',flush=True)
