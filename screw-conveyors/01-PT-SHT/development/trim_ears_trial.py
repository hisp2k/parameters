exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
trial=sw.GetOpenDocumentByName(str(Path('work/tube_collision_trial/Труба — контроль.SLDASM').resolve()))
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(trial.GetTitle,False,2,e)
target=next(c for c in trial.GetComponents(True) if 'Ухо' in c.Name2 and c.Name2.endswith('-1'))
tool=next(c for c in trial.GetComponents(True) if 'Труба шнека' in c.Name2)
trial.ClearSelection2(True);assert target.Select4(False,trial.SelectionManager.CreateSelectData,False)
info=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);assert trial.EditPart2(True,False,info)==0
trial.ClearSelection2(True);assert tool.Select4(False,trial.SelectionManager.CreateSelectData,False)
trial.InsertCavity4(0.,0.,0.,True,0,-1);trial.EditAssembly()
part=target.GetModelDoc2;f=part.FeatureByName('Полость1');assert f and not f.GetErrorCode;f.Name='Подрезка уха по корпусу'
trial.ForceRebuild3(False);errors=[(m.Name,m.GetErrorCode) for m in mates(trial) if m.GetErrorCode];print('mate errors',errors,flush=True);assert not errors
assert part.Save3(1,e,q);assert trial.Save3(1,e,q);print('saved',flush=True)
