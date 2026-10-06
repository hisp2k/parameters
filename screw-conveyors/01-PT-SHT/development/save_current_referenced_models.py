exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
models={doc.GetPathName:doc}
for c in doc.GetComponents(False):
 d=c.GetModelDoc2
 if d:models[d.GetPathName]=d
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
for path,d in sorted(models.items(),key=lambda x:(x[1].GetType!=1,x[0]==doc.GetPathName,x[0])):
 if d.GetSaveFlag:
  assert d.Save3(1,e,q),(path,e.value,q.value);print('saved',Path(path).name,flush=True)
print('saved all current referenced docs',flush=True)
