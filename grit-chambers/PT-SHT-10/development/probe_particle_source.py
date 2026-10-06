exec(open('work/inspect_particle_template.py',encoding='utf-8').read().split("f=typed(p.GetFeatures()")[0])
f=typed(p.GetFeatures(),'IProjectFeatures')
st=qi(f.GetFeatures2(True,104)[0],'IParticleStudy')
inj=st.CreateInjection()
for label,obj in [('inj',inj),('props',inj.GetParticleInjectionProps())]:
 for n in ['IFeature','IPreParticlesInjection','IPointsPlotProps','IPointPlot','IPlot','IGeomReferenceProps']:
  try:
   v=qi(obj,n);print(label,n,'SUPPORTED',flush=True)
  except Exception:print(label,n,'unsupported',flush=True)
print('add',st.AddInjection(inj),flush=True)
print('commit',f.AddUpdateFeature(p,st),flush=True)
st=qi(f.GetFeatures2(True,104)[0],'IParticleStudy')
print('saved injections',st.GetInjections(True),flush=True)
