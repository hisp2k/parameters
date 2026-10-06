import sys,json
from pathlib import Path
exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
level=int(sys.argv[1]);g=typed(p.GetGeneralSettings(),'IGeneralSettings');f=typed(p.GetFeatures(),'IProjectFeatures');app.SetSilent()
try:
 old=json.loads(Path('work/water_runs/mesh1/summary.json').read_text(encoding='utf-8'))
 correction=101325-old['goals']['MainOutlet_StaticP']['value']
 for raw in f.GetFeatures2(True,0):
  bc=typed(raw,'IBoundaryCondition')
  if bc.get_FCType()==10:
   bc.GetParameter(3).SetValue(101325+correction)
   print('OUTLET reference pressure',bc.GetParameter(3).GetValue(0.),'hydrostatic correction',correction,flush=True)
  print('BC temperature',bc.GetName(),bc.GetParameter(1).GetValue(0.),flush=True)
 g.put_ResultResulution(level);print('RESOLUTION',g.get_ResultResulution(),flush=True)
 opts=typed(p.GetCalculationControlOptions(),'ICalculationControlOptions');fin=typed(opts.GetFinishConditions(),'IFinishingConditions')
 fin.SetMaxIter(1200);p.ApplyCalculationControlOptions(opts,True)
 assert p.Rebuild(False,True,True,False,False,False),p.GetLastRebuildError()
 print('MESH',typed(p.GetSolver(),'IProjectSolver').CreateMesh(True,False),flush=True)
finally:app.ResetSilent()
