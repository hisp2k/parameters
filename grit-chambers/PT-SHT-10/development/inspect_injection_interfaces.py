exec(open('work/inspect_particle_template.py',encoding='utf-8').read().split("for n in ['IParticleInjection'")[0])
st.AddInjection(inj)
xs=st.GetInjections(True)
for x in xs or []:
 print('enumerated',x._oleobj_.GetTypeInfo().GetDocumentation(-1),flush=True)
 for name in ['GetName','GetUUID','GetPointsPlotProps','GetParticleInjectionProps']:
  try:print(name,x._oleobj_.GetIDsOfNames(name),flush=True)
  except Exception as e:print(name,'absent',flush=True)
pr=qi(inj.GetParticleInjectionProps(),'IParticleInjectionProps');pa=qi(pr.Get_IExcelParamsCollectionProps(),'IExcelParamsCollectionProps')
for k in [100,101,102]:print('START PARAM',k,pa.GetParameter(k),flush=True)
