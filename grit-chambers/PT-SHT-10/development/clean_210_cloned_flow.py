import sys
sys.stdout.reconfigure(encoding='utf-8')
exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
assert p.GetName()=='PT-SHT-10-210L-cloned'
f=typed(p.GetFeatures(),'IProjectFeatures')
app.SetSilent()
try:
    for feature_type in [0,3,4,104,105,116]:
        xs=f.GetFeatures2(True,feature_type) or []
        print('TYPE',feature_type,'COUNT',len(xs),flush=True)
        for feature in xs:
            print('REMOVE',feature_type,feature.GetName(),f.RemoveFeature(feature.GetUUID()),flush=True)
    print('REBUILD',p.Rebuild(False,True,True,False,False,False),repr(p.GetLastRebuildError()),flush=True)
    print('MESH',typed(p.GetSolver(),'IProjectSolver').CreateMesh(True,False),repr(p.GetLastRebuildError()),flush=True)
finally:
    app.ResetSilent()
