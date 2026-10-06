exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
d=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Труба в сборе' in c.Name2)
target=Path('work/tube_collision_trial/Труба — контроль.SLDASM').resolve();target.parent.mkdir(exist_ok=True)
assert not target.exists()
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(d.GetTitle,False,2,e)
assert d.Extension.SaveAs2(str(target),0,7,w.VARIANT(pythoncom.VT_DISPATCH,None),'_TCR04',False,e,q)
spec=sw.GetOpenDocSpec(str(target));spec.DocumentType=2;spec.Silent=True;trial=sw.OpenDoc7(spec)
assert trial and all(Path(c.GetPathName).is_relative_to(target.parent) for c in trial.GetComponents(False))
eq=trial.GetEquationMgr
for i in range(eq.GetCount):print(i,eq.Equation(i),flush=True)
for c in trial.GetComponents(True):
 if any(n in c.Name2 for n in ['Сбрасыватель','Патрубок шнека','Труба шнека','Ухо']):print('COMP',c.Name2,c.GetPathName,list(c.Transform2.ArrayData),flush=True)
