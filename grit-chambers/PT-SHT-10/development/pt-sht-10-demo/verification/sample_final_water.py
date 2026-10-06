exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
from pathlib import Path
import csv,json
r=typed(p.GetResults(),'IResults')
fld=(Path('work/pt-sht-10-demo/Модель/2/2.fld')).resolve()
r.LoadResults(str(fld))
assert r.GetResultsFileType()==3
fl=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\FW03.dll')
tis={fl.GetDocumentation(i)[0]:fl.GetTypeInfo(i) for i in range(fl.GetTypeInfoCount())}
def wrap(o,n):return w.dynamic.Dispatch(o._oleobj_ if hasattr(o,'_oleobj_') else o,typeinfo=tis[n])
uip=sw.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
post=wrap(uip.GetPostDocAPI(),'IPostDocApiHandler')
params={'speed_m_s':'BBB6B2F8-15C9-4015-B560-EA33C2C9116B','vx_m_s':'12E844D2-B70E-441c-AB35-32B7B56810BD','vy_m_s':'65CC5BC2-D735-4a6e-928A-EEB9EF5DD43C','vz_m_s':'3D2F7944-2365-4527-A334-4341721AD3AA','pressure_Pa':'88A4B00C-3C32-4822-94C2-4682145D4F95'}
rows=[]
for plane in ['x=0','y=0.7195']:
 for j in range(91 if plane=='x=0' else 77):
  for i in range(77):
   a=-.38+i*.01;b=j*.01 if plane=='x=0' else -.38+j*.01
   xyz=(0.,b,a) if plane=='x=0' else (a,.7195,b)
   row=dict(plane=plane,x_m=xyz[0],y_m=xyz[1],z_m=xyz[2],valid=0)
   try:
    inter=post.IGetParamInterpolator2(*xyz)
    if inter:
     q=wrap(inter,'IParamInterpolatorApi')
     for name,uid in params.items():
      val=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_R8,0.)
      ok=q._oleobj_.Invoke(q._oleobj_.GetIDsOfNames('Interpolate2'),0,pythoncom.DISPATCH_METHOD,1,uid,val)
      if not ok:raise RuntimeError('interpolation failed')
      row[name]=val.value
     row['valid']=1
   except Exception:pass
   rows.append(row)
  if j%20==0:print(plane,'row',j,flush=True)
out=Path('outputs/PT-SHT-10_поля_воды.csv')
with out.open('w',encoding='utf-8-sig',newline='') as f:
 wr=csv.DictWriter(f,fieldnames=['plane','x_m','y_m','z_m','valid']+list(params));wr.writeheader();wr.writerows(rows)
print('samples',len(rows),'valid',sum(v['valid'] for v in rows),'source',fld,flush=True)
