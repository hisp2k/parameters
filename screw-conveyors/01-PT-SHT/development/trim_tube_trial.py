exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
trial=sw.GetOpenDocumentByName(str(Path('work/tube_collision_trial/Труба — контроль.SLDASM').resolve()))
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(trial.GetTitle,False,2,e)
eq=trial.GetEquationMgr;eq.Equation(14,eq.Equation(14).replace('30мм','29мм'))
sbro=next(c for c in trial.GetComponents(True) if 'Сбрасыватель' in c.Name2)
stem=Path(sbro.GetPathName).stem
for dimension,value in [('D1@Эскиз2','Диаметр трубы'),('D1@Эскиз1','Диаметр сбрасывателя'),('D1@Бобышка-Вытянуть1','Длина сбрасывателя')]:
 part=sbro.GetModelDoc2;sw.ActivateDoc3(part.GetTitle,False,2,e)
 dim=part.Parameter(dimension);dim.ReadOnly=False
 if dim.DrivenState==1:dim.DrivenState=2
 sw.ActivateDoc3(trial.GetTitle,False,2,e)
 expr=f'"{dimension}@{stem}<1>.Part"="{value}"';print('added',eq.Add2(-1,expr,True),expr,flush=True)
eq.EvaluateAll;trial.ForceRebuild3(False)
print('sbro saddle',sbro.GetModelDoc2.Parameter('D1@Эскиз2').SystemValue,flush=True)
assert abs(sbro.GetModelDoc2.Parameter('D1@Эскиз2').SystemValue-.141)<1e-8
tools=[next(c for c in trial.GetComponents(True) if 'Патрубок шнека' in c.Name2 and c.Name2.endswith('-2'))]
trial.ClearSelection2(True);assert sbro.Select4(False,trial.SelectionManager.CreateSelectData,False)
info=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);print('edit',trial.EditPart2(True,False,info),info.value,flush=True)
trial.ClearSelection2(True)
for i,c in enumerate(tools):assert c.Select4(i>0,trial.SelectionManager.CreateSelectData,False)
trial.InsertCavity4(0.,0.,0.,True,0,-1)
part=sbro.GetModelDoc2;f=part.FirstFeature;features=[]
while f:
 features.append((f.Name,f.GetTypeName2,f.GetErrorCode));f=f.GetNextFeature
print('features',features[-5:],flush=True)
trial.EditAssembly();assert any(t=='Cavity' for n,t,code in features)
assert not [(n,code) for n,t,code in features if code]
trial.ForceRebuild3(False);print('mate errors',[(m.Name,m.GetErrorCode) for m in mates(trial) if m.GetErrorCode],flush=True)
assert not [(m.Name,m.GetErrorCode) for m in mates(trial) if m.GetErrorCode]
for c in trial.GetComponents(True):
 d=c.GetModelDoc2
 if d and d.GetSaveFlag:assert d.Save3(1,e,q)
assert trial.Save3(1,e,q);print('saved',flush=True)
