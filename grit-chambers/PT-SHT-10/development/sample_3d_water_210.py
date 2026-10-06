import sys,time
from pathlib import Path
sys.path.insert(0,str(Path('work/particledeps').resolve()))
import numpy as np,trimesh
import pythoncom,win32com.client as win32

pythoncom.CoInitialize()
dx=float(sys.argv[1]) if len(sys.argv)>1 else .015
mm=round(dx*1000)
flow_case=sys.argv[2] if len(sys.argv)>2 else 'Q10'
assert flow_case in ('Q10','Q2p09')
project_name={'Q10':'PT-SHT-10-210L-cloned','Q2p09':'PT-SHT-10-210L-Q2p09'}[flow_case]
project_index={'Q10':4,'Q2p09':5}[flow_case]
mesh=trimesh.load('work/pt-sht-10-210l/CADparts/CAD210_fluid_cavity.STL')
mesh.apply_scale(.001)
mesh.apply_translation([-.297,0,-.297])
assert mesh.is_watertight and abs(mesh.volume-.21023062)/.21023062<.003
xs=np.arange(-.3,.3001,dx)
ys=np.arange(0.,1.0151,dx)
zs=np.arange(-.3,.3601,dx)
grid=np.stack(np.meshgrid(xs,ys,zs,indexing='ij'),-1)
flat=grid.reshape(-1,3)
maskfile=Path(f'work/pt-sht-10-210l/CADparts/cavity_mask_{mm}mm.npz')
if maskfile.exists():
    inside=np.load(maskfile)['inside']
else:
    inside=np.empty(len(flat),dtype=bool)
    for k in range(0,len(flat),1000):
        inside[k:k+1000]=mesh.contains(flat[k:k+1000])
        if k%10000==0:print('CLASSIFY',k,len(flat),flush=True)
    np.savez_compressed(maskfile,inside=inside)
print('GRID',grid.shape,'inside',inside.sum(),flush=True)
sw=win32.Dispatch('SldWorks.Application')
assert 'PT-SHT-10-210L.SLDASM' in sw.ActiveDoc.GetPathName
rot=pythoncom.GetRunningObjectTable();ctx=pythoncom.CreateBindCtx(0);en=rot.EnumRunning()
mon=None;expected=str(sw.GetProcessID)+'EFDApiLibROT'
while True:
    item=en.Next(1)
    if not item:break
    if item[0].GetDisplayName(ctx,None)==expected:mon=item[0];break
assert mon
lib=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
def typed(obj,name):
    ti=next(lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount()) if lib.GetDocumentation(i)[0]==name)
    return win32.dynamic.Dispatch(obj,typeinfo=ti)
app=typed(rot.GetObject(mon).QueryInterface(pythoncom.IID_IDispatch),'IApplication')
project=typed(typed(app.GetActiveDoc(),'IDocument').GetActiveProject(),'IProject')
assert project.GetName()==project_name
fld=(Path.cwd()/'work'/'pt-sht-10-210l'/'Модель'/str(project_index)/(str(project_index)+'.fld')).resolve()
assert fld.exists()
results=typed(project.GetResults(),'IResults')
results.LoadResults(str(fld))
assert results.GetResultsFileType()==3
fwlib=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\FW03.dll')
fwtypes={fwlib.GetDocumentation(i)[0]:fwlib.GetTypeInfo(i) for i in range(fwlib.GetTypeInfoCount())}
def wrap(obj,name):return win32.dynamic.Dispatch(obj._oleobj_ if hasattr(obj,'_oleobj_') else obj,typeinfo=fwtypes[name])
uip=sw.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
post=wrap(uip.GetPostDocAPI(),'IPostDocApiHandler')
uids=['12E844D2-B70E-441c-AB35-32B7B56810BD',
      '65CC5BC2-D735-4a6e-928A-EEB9EF5DD43C',
      '3D2F7944-2365-4527-A334-4341721AD3AA']
field=np.full((len(flat),3),np.nan,dtype=np.float32)
loc=np.flatnonzero(inside)
start=time.monotonic();fail=0
for k,ix in enumerate(loc):
    try:
        inter=post.IGetParamInterpolator2(*map(float,flat[ix]))
        obj=wrap(inter,'IParamInterpolatorApi')
        for j,uid in enumerate(uids):
            val=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_R8,0.)
            ok=obj._oleobj_.Invoke(obj._oleobj_.GetIDsOfNames('Interpolate2'),0,pythoncom.DISPATCH_METHOD,1,uid,val)
            if ok:field[ix,j]=val.value
            else:fail+=1
    except Exception:
        fail+=1
    if k%5000==0:print('SAMPLE',k,len(loc),'seconds',round(time.monotonic()-start,1),flush=True)
field=field.reshape(grid.shape)
out=Path(f'work/pt-sht-10-210l/CADparts/water_field_210_{mm}mm_{flow_case}.npz') if flow_case!='Q10' else Path(f'work/pt-sht-10-210l/CADparts/water_field_210_{mm}mm.npz')
np.savez_compressed(out,x=xs,y=ys,z=zs,velocity=field,inside=inside.reshape(grid.shape[:-1]),
                    flow_source=str(fld),mesh_volume=mesh.volume)
print('SAVED',out,'valid',np.isfinite(field[:,:,:,0]).sum(),'fail',fail,
      'seconds',round(time.monotonic()-start,1),flush=True)
