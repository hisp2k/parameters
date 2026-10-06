exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
upper=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Обойма верхняя' in c.Name2)
target=Path('work/upper_interference_trial/Обойма верхняя — контроль.SLDASM').resolve();target.parent.mkdir(exist_ok=True)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(upper.GetTitle,False,2,e)
assert upper.Extension.SaveAs2(str(target),0,7,w.VARIANT(pythoncom.VT_DISPATCH,None),'_UI_R04',False,e,q)
spec=sw.GetOpenDocSpec(str(target));spec.DocumentType=2;spec.Silent=True;trial=sw.OpenDoc7(spec)
print('upper candidate',len(trial.GetComponents(False)),flush=True)
for c in trial.GetComponents(True):
 if any(x in c.Name2 for x in ["'Обойма'",'Стопорное кольцо D','Манжета']):print(c.Name2,c.GetPathName,flush=True)
