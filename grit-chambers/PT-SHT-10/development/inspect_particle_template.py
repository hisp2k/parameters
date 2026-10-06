exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
def qi(o,n):
 ti=next(lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount()) if lib.GetDocumentation(i)[0]==n)
 ptr=o._oleobj_.QueryInterface(ti.GetTypeAttr().iid,pythoncom.IID_IDispatch)
 return w.dynamic.Dispatch(ptr,typeinfo=ti)
f=typed(p.GetFeatures(),'IProjectFeatures')
raw=f.CreateFeature(104);print('study',raw,raw._oleobj_.GetTypeInfo().GetDocumentation(-1),flush=True)
st=qi(raw,'IParticleStudy');inj=st.CreateInjection();print('injection',inj,inj._oleobj_.GetTypeInfo().GetDocumentation(-1),flush=True)
for n in ['IParticleInjection','IPointPlot','IPlot','IParticleInjectionExporter']:
 try:
  ob=qi(inj,n);print('SUPPORTS',n,flush=True)
  if n=='IPointPlot':
   pts=qi(ob.GetPointsPlotProps(),'IPointsPlotProps');print('points',pts.GetPointsDefMode(),pts.GetRequiredPointsCount(),pts.GetPoints(),flush=True)
  if n=='IParticleInjection':
   pr=qi(ob.GetParticleInjectionProps(),'IParticleInjectionProps');print('velocitytype',pr.GetVelocityType(),'material',pr.GetMaterialInfo(None,None),flush=True)
   par=qi(pr.Get_IExcelParamsCollectionProps(),'IExcelParamsCollectionProps')
   for k in [103,104,105,106,107,108,109,110,111,144]:
    pa=par.GetParameter(k)
    print('PARAM',k,pa,flush=True)
    if pa:print('  interface',pa._oleobj_.GetTypeInfo().GetDocumentation(-1),flush=True)
 except Exception as e:print('ERROR',n,repr(e),flush=True)
