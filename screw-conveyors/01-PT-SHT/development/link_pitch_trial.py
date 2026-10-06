exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
trial=sw.GetOpenDocumentByName(str(Path('work/screw_collision_trial/Шнековый вал — контроль.SLDASM').resolve()))
c=next(c for c in trial.GetComponents(True) if 'Винт шнека' in c.Name2);d=c.GetModelDoc2
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(trial.GetTitle,False,2,e)
eq=trial.GetEquationMgr
expr=f'"D4@Спираль1@{Path(c.GetPathName).stem}<1>.Part"="Шаг винта шнека"'
if eq.GetCount==24:print('add',eq.Add2(-1,expr,True),flush=True)
else:eq.Equation(24,expr)
eq.Equation(18,'"D1@Расстояние2"=85мм + "Шаг винта шнека" * "Число витков" + "Толщина лопасти"')
eq.EvaluateAll;trial.ForceRebuild3(False)
helix=d.FeatureByName('Спираль1');print('pitch',helix.GetDefinition.Pitch,'height',helix.GetDefinition.Height,'box',d.GetPartBox(True),flush=True)
assert abs(helix.GetDefinition.Pitch-.105)<1e-8
errors=[];f=d.FirstFeature
while f:
 if f.GetErrorCode:errors.append((f.Name,f.GetErrorCode))
 f=f.GetNextFeature
print('errors',errors,flush=True);assert not errors
sw.ActivateDoc3(d.GetTitle,False,2,e);assert d.Save3(1,e,q)
sw.ActivateDoc3(trial.GetTitle,False,2,e);assert trial.Save3(1,e,q)
