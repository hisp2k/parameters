exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
d=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2)
target=Path('work/support_collision_trial/Опора — контроль.SLDASM').resolve();target.parent.mkdir(exist_ok=True)
assert not target.exists()
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(d.GetTitle,False,2,e)
assert d.Extension.SaveAs2(str(target),0,7,w.VARIANT(pythoncom.VT_DISPATCH,None),'_SPCR04',False,e,q)
spec=sw.GetOpenDocSpec(str(target));spec.DocumentType=2;spec.Silent=True;trial=sw.OpenDoc7(spec);sw.ActivateDoc3(trial.GetTitle,False,2,e)
cs=list(trial.GetComponents(True));tools=[c for c in cs if any(n in c.Name2 for n in ['Балка','Стойка'])];braces=[c for c in cs if 'Подкос' in c.Name2]
print('braces',len(braces),'tools',len(tools),flush=True);assert braces and tools
before={c.Name2:list(c.Transform2.ArrayData) for c in cs}
seen=set()
for brace in braces:
 if brace.GetPathName in seen:continue
 seen.add(brace.GetPathName)
 trial.ClearSelection2(True);assert brace.Select4(False,trial.SelectionManager.CreateSelectData,False)
 info=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);assert trial.EditPart2(True,False,info)==0
 trial.ClearSelection2(True)
 for i,c in enumerate(tools):assert c.Select4(i>0,trial.SelectionManager.CreateSelectData,False)
 trial.InsertCavity4(0.,0.,0.,True,0,-1);trial.EditAssembly();part=brace.GetModelDoc2;f=part.FeatureByName('Полость1');assert f and not f.GetErrorCode;f.Name='Подрезка подкоса по стойкам и балкам'
 trial.ForceRebuild3(False);errors=[(m.Name,m.GetErrorCode) for m in mates(trial) if m.GetErrorCode];print('mate errors',errors,flush=True);assert not errors
 assert part.Save3(1,e,q)
assert max(abs(v-a) for c in trial.GetComponents(True) for v,a in zip(before[c.Name2],c.Transform2.ArrayData))<1e-7
assert trial.Save3(1,e,q);print('saved support trial',flush=True)
