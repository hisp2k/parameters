from pathlib import Path
import json,time
exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
app.SetSilent()
try:
 assert p.Rebuild(False,False,True,False,False,False),p.GetLastRebuildError()
 solver=typed(p.GetSolver(),'IProjectSolver')
 print('SOLVE START',time.strftime('%Y-%m-%d %H:%M:%S'),flush=True)
 ok=solver.Solve(False,True,True,False)
 print('SOLVE RESULT',ok,'error',p.GetLastRebuildError(),flush=True)
 Path('work/water_solve_return.json').write_text(json.dumps({'return':ok,'time':time.strftime('%Y-%m-%d %H:%M:%S'),'error':p.GetLastRebuildError()}),encoding='utf-8')
finally:app.ResetSilent()
