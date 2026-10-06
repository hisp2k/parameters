exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
trial=sw.GetOpenDocumentByName(str(Path('work/screw_collision_trial/Шнековый вал — контроль.SLDASM').resolve()))
d=next(c.GetModelDoc2 for c in trial.GetComponents(True) if 'Винт шнека' in c.Name2)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(d.GetTitle,False,2,e)
bs=[b for b in d.GetBodies2(0,False) if b.Name=='По траектории1' and not b.Visible];assert len(bs)==1
d.ClearSelection2(True);assert bs[0].Select2(False,None)
f=d.FeatureManager.InsertDeleteBody2(False);assert f and not f.GetErrorCode
f.Name='Удаление вспомогательного тела прототипа'
d.ForceRebuild3(False);assert len(d.GetBodies2(0,False))==24
print('saved',d.Save3(1,e,q),e.value,q.value,flush=True)
sw.ActivateDoc3(trial.GetTitle,False,2,e);trial.ForceRebuild3(False);print('saved assembly',trial.Save3(1,e,q),flush=True)
