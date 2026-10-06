exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
trial=sw.GetOpenDocumentByName(str(Path('work/screw_collision_trial/Шнековый вал — контроль.SLDASM').resolve()))
d=next(c.GetModelDoc2 for c in trial.GetComponents(True) if 'Винт шнека' in c.Name2)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(d.GetTitle,False,2,e)
bs=list(d.GetBodies2(0,True));print('bodies',len(bs),flush=True)
f=d.FirstFeature
while f:
 print(f.Name,f.GetTypeName2,f.GetErrorCode,flush=True);f=f.GetNextFeature
new=d.FeatureManager.InsertCombineFeature(15903,w.VARIANT(pythoncom.VT_DISPATCH,None),w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,bs))
print('combine',new.Name if new else None,'bodies',len(d.GetBodies2(0,True)),flush=True)
assert new and not new.GetErrorCode
new.Name='Объединение винтовой лопасти'
print('save',d.Save3(1,e,q),e.value,q.value,flush=True)
