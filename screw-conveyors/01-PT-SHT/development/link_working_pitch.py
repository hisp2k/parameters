exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
a=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Шнековый вал' in c.Name2);c=next(c for c in a.GetComponents(True) if 'Винт шнека' in c.Name2);d=c.GetModelDoc2
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(a.GetTitle,False,2,e)
eq=a.GetEquationMgr;assert eq.GetCount==24
expr=f'"D4@Спираль1@{Path(c.GetPathName).stem}<1>.Part"="Шаг винта шнека"'
assert eq.Add2(-1,expr,True)==24
eq.Equation(18,'"D1@Расстояние2"=85мм + "Шаг винта шнека" * "Число витков" + "Толщина лопасти"')
eq.EvaluateAll;a.ForceRebuild3(False);assert abs(d.FeatureByName('Спираль1').GetDefinition.Pitch-.105)<1e-8
sw.ActivateDoc3(d.GetTitle,False,2,e);assert d.Save3(1,e,q)
sw.ActivateDoc3(a.GetTitle,False,2,e);assert a.Save3(1,e,q)
sw.ActivateDoc3(doc.GetTitle,False,2,e);doc.ForceRebuild3(False);assert not [(m.Name,m.GetErrorCode) for m in mates(doc) if m.GetErrorCode];assert doc.Save3(1,e,q)
print('native helix linked, saved',flush=True)
