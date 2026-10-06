exec(open('work/inspect_particle_template.py',encoding='utf-8').read().split("f=typed(p.GetFeatures()")[0])
from pathlib import Path
f=typed(p.GetFeatures(),'IProjectFeatures');app.SetSilent()
try:
 existing=f.GetFeatures2(True,104) or []
 st=qi(existing[0] if existing else f.CreateFeature(104),'IParticleStudy')
 st.DisableAutomaticNameChange();st.SetName('Sand_demo_0p25mm_SETUP')
 print('ADD STUDY',f.AddUpdateFeature(p,st),st.GetUUID(),flush=True)
 inj=st.CreateInjection();print('INJECTION',inj,flush=True)
 ip=qi(inj.GetParticleInjectionProps(),'IParticleInjectionProps')
 ep=qi(ip.Get_IExcelParamsCollectionProps(),'IExcelParamsCollectionProps')
 for k,val in [(107,.00025),(110,2650.),(106,293.15)]:
  prop=qi(ep.GetParameter(k),'IExcelParameterProps');param=qi(prop.Get_IExcelParam(),'IExcelParam');print('SET',k,param.SetValue(val),param.GetValue(0.),flush=True)
 print('ADD INJECTION',st.AddInjection(inj),flush=True)
 print('STUDY INJECTIONS',st.GetInjections(True),flush=True)
 for typ in [104,105,116]:
  xs=f.GetFeatures2(True,typ) or []
  print('FEATURE TYPE',typ,'COUNT',len(xs),flush=True)
  for ob in xs:
   print(' WRAPPER',ob._oleobj_.GetTypeInfo().GetDocumentation(-1),flush=True)
   try:print(' NAME',ob.GetName(),'UUID',ob.GetUUID(),flush=True)
   except Exception as e:print(type(e).__name__,flush=True)
finally:app.ResetSilent()
