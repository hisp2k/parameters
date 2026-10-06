exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
assert p.GetName()=='PT-SHT-10-210L-Q10-closed'
g=typed(p.GetGeneralSettings(),'IGeneralSettings')
sub=typed(p.GetProjectSubstances(),'IProjectSubstances')
water='6D4EB34F944911D4B47100A024552746'
app.SetSilent()
try:
    print('INTERNAL',g.SetProblemType(True,True,1),g.GetProblemType(),flush=True)
    g.SetFluidType(2)
    print('FLUIDTYPE',g.GetFluidType(),flush=True)
    print('GRAVITY',g.SetGravitation(True),g.GetGravitation(),flush=True)
    print('ADD WATER',sub.AddSubstance(2,water),flush=True)
    print('DEFAULT WATER',sub.SetDefaultFluid(water,True),flush=True)
    g.put_ResultResulution(3)
    print('RESOLUTION',g.get_ResultResulution(),flush=True)
    print('REBUILD',p.Rebuild(False,False,True,False,False,False),p.GetLastRebuildError(),flush=True)
    cad=typed(app.GetCAD(),'ICADApplication')
    print('SAVE',typed(cad.GetActiveDoc(),'ICADDocument').Save(),flush=True)
finally:
    app.ResetSilent()
