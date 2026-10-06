import json
from pathlib import Path
exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
assert p.GetName()=='PT-SHT-10-210L-Q10-closed'
f=typed(p.GetFeatures(),'IProjectFeatures')
rows=[]
app.SetSilent()
try:
    for raw in f.GetFeatures2(True,0) or []:
        b=typed(raw,'IBoundaryCondition')
        row={'name':b.GetName(),'uuid':b.GetUUID(),'type':b.get_FCType(),
             'refs':b.GetTopologicalReferencesUUIDsAndNames(None,None)}
        rows.append(row)
        print('REMOVE',b.GetUUID(),f.RemoveFeature(b.GetUUID()),flush=True)
    print('REBUILD_NO_BC',p.Rebuild(True,True,True,False,False,False),repr(p.GetLastRebuildError()),flush=True)
    print('MESH_NO_BC',typed(p.GetSolver(),'IProjectSolver').CreateMesh(True,False),
          repr(p.GetLastRebuildError()),flush=True)
finally:
    app.ResetSilent()
    Path('work/210_removed_bc.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
