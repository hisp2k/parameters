import sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path('work/particledeps').resolve()))
import numpy as np,trimesh
import pythoncom,win32com.client as w
pythoncom.CoInitialize()
mesh=trimesh.load('work/cavity_for_particle_model.stl');mesh.apply_scale(.001);mesh.apply_translation([-.297,0,-.297])
assert mesh.is_watertight and abs(mesh.volume-.1625431054)/.1625431054<.002
dx=float(sys.argv[1]) if len(sys.argv)>1 else .015
xs=np.arange(-.3,.30001,dx);ys=np.arange(0.,.84001,dx);zs=np.arange(-.3,.36001,dx)
grid=np.stack(np.meshgrid(xs,ys,zs,indexing='ij'),-1)
flat=grid.reshape(-1,3);inside=np.empty(len(flat),dtype=bool)
maskfile=Path(f'work/cavity_grid_mask_{int(dx*1000)}mm.npz')
if maskfile.exists():inside=np.load(maskfile)['inside']
else:
 for k in range(0,len(flat),1000):
  inside[k:k+1000]=mesh.contains(flat[k:k+1000])
  if k%10000==0:print('geometry classify',k,'of',len(flat),flush=True)
 np.savez_compressed(maskfile,inside=inside)
print('grid',grid.shape,'inside',sum(inside),'of',len(flat),flush=True)
sw=w.Dispatch('SldWorks.Application')
model=next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Бункер в сборе.SLDASM'))
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);wr=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
d=sw.OpenDoc6(str(model.resolve()),2,0,'',e,wr)
assert d
if Path(sw.ActiveDoc.GetPathName).resolve()!=model.resolve():
 d=sw.ActivateDoc3(model.name,False,0,e)
assert d and Path(sw.ActiveDoc.GetPathName).resolve()==model.resolve()
rot=pythoncom.GetRunningObjectTable();ctx=pythoncom.CreateBindCtx(0);enum=rot.EnumRunning();mon=None
expected=str(sw.GetProcessID)+'EFDApiLibROT'
while True:
 x=enum.Next(1)
 if not x:break
 if x[0].GetDisplayName(ctx,None)==expected:mon=x[0];break
assert mon
lib=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
def typed(obj,name):
 ti=next(lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount()) if lib.GetDocumentation(i)[0]==name)
 return w.dynamic.Dispatch(obj,typeinfo=ti)
app=typed(rot.GetObject(mon).QueryInterface(pythoncom.IID_IDispatch),'IApplication')
project=typed(typed(app.GetActiveDoc(),'IDocument').GetActiveProject(),'IProject')
assert project.GetName()=='PT-SHT-10-demo-Q10-sealed'
mesh_name=sys.argv[2] if len(sys.argv)>2 else None
assert mesh_name in (None,'mesh1','mesh2','mesh3')
r=typed(project.GetResults(),'IResults')
fld=((Path.cwd()/'work'/'water_runs'/mesh_name/'2.fld') if mesh_name else (Path.cwd()/'work'/'pt-sht-10-demo'/'Модель'/'2'/'2.fld')).resolve()
r.LoadResults(str(fld));assert r.GetResultsFileType()==3
fl=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\FW03.dll')
tis={fl.GetDocumentation(i)[0]:fl.GetTypeInfo(i) for i in range(fl.GetTypeInfoCount())}
def wrap(obj,name):return w.dynamic.Dispatch(obj._oleobj_ if hasattr(obj,'_oleobj_') else obj,typeinfo=tis[name])
uip=sw.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
post=wrap(uip.GetPostDocAPI(),'IPostDocApiHandler')
uids=['12E844D2-B70E-441c-AB35-32B7B56810BD','65CC5BC2-D735-4a6e-928A-EEB9EF5DD43C','3D2F7944-2365-4527-A334-4341721AD3AA']
field=np.full((len(flat),3),np.nan,dtype=np.float32)
loc=np.flatnonzero(inside);start=time.monotonic();fail=0
for k,ix in enumerate(loc):
 try:
  obj=post.IGetParamInterpolator2(*map(float,flat[ix]))
  q=wrap(obj,'IParamInterpolatorApi')
  for j,uid in enumerate(uids):
   val=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_R8,0.)
   ok=q._oleobj_.Invoke(q._oleobj_.GetIDsOfNames('Interpolate2'),0,pythoncom.DISPATCH_METHOD,1,uid,val)
   if ok:field[ix,j]=val.value
   else:fail+=1
 except Exception:fail+=1
 if k%5000==0:print('sample',k,'of',len(loc),'seconds',round(time.monotonic()-start,1),flush=True)
field=field.reshape(grid.shape)
fn=Path(f'work/water_field_{mesh_name}_3d_{int(dx*1000)}mm.npz') if mesh_name else Path(f'work/water_field_3d_{int(dx*1000)}mm.npz')
np.savez_compressed(fn,x=xs,y=ys,z=zs,velocity=field,inside=inside.reshape(grid.shape[:-1]),mesh_volume=mesh.volume,flow_source=str(fld))
print('saved',fn,'valid',np.isfinite(field[:,:,:,0]).sum(),'fail',fail,'elapsed',time.monotonic()-start,flush=True)
