import pythoncom,win32com.client as w
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\FW03.dll')
tis={l.GetDocumentation(i)[0]:l.GetTypeInfo(i) for i in range(l.GetTypeInfoCount())}
def wrap(o,n):return w.dynamic.Dispatch(o._oleobj_ if hasattr(o,'_oleobj_') else o,typeinfo=tis[n])
sw=w.Dispatch('SldWorks.Application');uip=sw.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
post=wrap(uip.GetPostDocAPI(),'IPostDocApiHandler')
for pt in [(.2515,.7195,.32),(0.,.458,.34),(.25,.6,0.),(.4,.6,.4)]:
 try:
  inter=post.IGetParamInterpolator2(*pt);print('POINT',pt,inter,flush=True)
  if inter:
   q=wrap(inter,'IParamInterpolatorApi')
   for uid in ['BBB6B2F8-15C9-4015-B560-EA33C2C9116B','F29A5B7A-DC60-4d0a-91F3-B3E0A073A6D9']:
    val=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_R8,0.)
    print(uid,q._oleobj_.Invoke(q._oleobj_.GetIDsOfNames('Interpolate2'),0,pythoncom.DISPATCH_METHOD,1,uid,val),val.value,flush=True)
 except Exception as e:print('ERR',repr(e),flush=True)
