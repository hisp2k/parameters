from pathlib import Path
import json
exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
f=typed(p.GetFeatures(),'IProjectFeatures');g=typed(p.GetGeneralSettings(),'IGeneralSettings')
assert not (f.GetFeatures2(True,4) or [])
app.SetSilent();out=[]
try:
 for raw in f.GetFeatures2(True,0):
  bc=typed(raw,'IBoundaryCondition');fc=bc.get_FCType();label={1:'Inlet',10:'MainOutlet',6:'BottomOutlet'}[fc]
  bc.DisableAutomaticNameChange();bc.SetName(label)
  uuids,names=bc.GetTopologicalReferencesUUIDsAndNames(None,None)
  for tag,typ,calc in [('Q',17,0),('MassFlow',4,0),('StaticP',1,2),('TotalP',18,4)]:
   goal=typed(f.CreateFeature(4),'ISurfaceGoal');goal.put_GoalType(typ);goal.put_CalculateValue(calc)
   goal.put_UseInConvergence(tag=='TotalP' and label=='Inlet')
   for uid,name in zip(uuids,names):goal.AddTopologicalReferenceUUIDAndName(uid,name)
   goal.DisableAutomaticNameChange();goal.SetName(label+'_'+tag)
   assert f.AddUpdateFeature(p,goal)
   out.append({'name':goal.GetName(),'uuid':goal.GetUUID(),'type':typ,'calc':calc})
 goal=typed(f.CreateFeature(3),'IGlobalGoal');goal.put_GoalType(21);goal.put_CalculateValue(3);goal.put_UseInConvergence(True);goal.DisableAutomaticNameChange();goal.SetName('Global_Velocity_Max');assert f.AddUpdateFeature(p,goal)
 out.append({'name':goal.GetName(),'uuid':goal.GetUUID(),'type':21,'calc':3})
 opts=typed(p.GetCalculationControlOptions(),'ICalculationControlOptions');fin=typed(opts.GetFinishConditions(),'IFinishingConditions')
 fin.SetUseMaxIter(True);fin.SetMaxIter(800);fin.SetUseGoalsConv(True);fin.SetUseMaxTravels(False);fin.SetFinishCondition(0)
 p.ApplyCalculationControlOptions(opts,True)
 print('REBUILD',p.Rebuild(False,False,True,False,False,False),p.GetLastRebuildError(),flush=True)
 print('GOALS',json.dumps(out,ensure_ascii=False),flush=True)
 Path('work/flow_goals.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
finally:app.ResetSilent()
