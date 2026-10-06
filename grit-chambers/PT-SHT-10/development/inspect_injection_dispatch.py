exec(open('work/inspect_particle_template.py',encoding='utf-8').read().split("for n in ['IParticleInjection'")[0])
for name in ['GetName','GetUUID','GetPointsPlotProps','GetFeatProperties','GetParticleInjectionProps']:
 try:print('DISPID',name,inj._oleobj_.GetIDsOfNames(name),flush=True)
 except Exception as e:print(name,'NOT EXPOSED',flush=True)
print('new generic injection',flush=True)
obj=f.CreateFeature(105);print(obj,obj._oleobj_.GetTypeInfo().GetDocumentation(-1) if obj else None,flush=True)
if obj:
 for name in ['GetName','GetPointsPlotProps','GetParticleInjectionProps']:
  try:print('GENERIC',name,obj._oleobj_.GetIDsOfNames(name),flush=True)
  except Exception as e:print(name,'NOT EXPOSED',flush=True)
