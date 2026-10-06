"""Demonstration: one-way particle tracking over native Flow Simulation water field.

This is an independent model, not a SOLIDWORKS Particle Study. Particles are
quartz spheres; walls absorb. No turbulent random walk, erosion, or screw model.
"""
import sys,json,time,csv
from pathlib import Path
sys.path.insert(0,str(Path('work/particledeps').resolve()))
import numpy as np,trimesh
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import distance_transform_edt
from scipy.stats import qmc

GRID_MM=int(sys.argv[1]) if len(sys.argv)>1 else 15
N=int(sys.argv[2]) if len(sys.argv)>2 else 256
WALL_MODE=sys.argv[3] if len(sys.argv)>3 else 'trap'
assert WALL_MODE in ('trap','reflect','hoppertrap')
MAX_COLLISIONS=int(sys.argv[5]) if len(sys.argv)>5 else 200
MAX_STEP_M=float(sys.argv[6]) if len(sys.argv)>6 else .005
source=Path(f'work/water_field_3d_{GRID_MM}mm.npz')
data=np.load(source)
x,y,z=[data[k] for k in ['x','y','z']]
f=data['velocity'].astype(float);inside=data['inside']
good=np.isfinite(f[:,:,:,0]) & inside
assert good.sum()>10000
_,indexes=distance_transform_edt(~good,return_indices=True)
for j in range(3):f[:,:,:,j][~good]=f[:,:,:,j][tuple(indexes[:,~good])]
field=RegularGridInterpolator((x,y,z),f,method='linear',bounds_error=False,fill_value=np.nan)
dist=distance_transform_edt(inside)
mesh=trimesh.load('work/cavity_for_particle_model.stl');mesh.apply_scale(.001);mesh.apply_translation([-.297,0,-.297])
rho_f=997.5744250027426;mu=.0010016718;rho_p=2650.;grav=np.array([0.,-9.81,0.]);diameters=[float(v) for v in sys.argv[4].split(',')] if len(sys.argv)>4 else [.10,.15,.20,.25,.30,.60]
sob=qmc.Sobol(d=2,scramble=False).random_base2(int(np.log2(N)))
assert len(sob)==N
radius=.0253*np.sqrt(sob[:,0]);theta=2*np.pi*sob[:,1]
initial=np.stack([.2515+radius*np.cos(theta),.7195+radius*np.sin(theta),np.full(N,.323)],axis=-1)
assert mesh.contains(initial).all(), 'Start positions must lie inside CAD fluid cavity'
uvw=field(initial)
weights=np.maximum(-uvw[:,2],0)
assert weights.min()>0 and np.isfinite(weights).all()
weights=weights/weights.sum()
print('initial flux range',weights.min(),weights.max(),'water vz',uvw[:,2].min(),uvw[:,2].max(),flush=True)

def exact_inside(points):
 out=np.empty(len(points),dtype=bool)
 for k in range(0,len(points),500):out[k:k+500]=mesh.contains(points[k:k+500])
 return out

def terminal_speed(d):
 v=(rho_p-rho_f)*9.81*d*d/(18*mu)
 for _ in range(20):
  re=rho_f*d*v/mu;factor=1+.15*re**.687 if re<1000 else .0183*re
  v=(rho_p-rho_f)*9.81*d*d/(18*mu*factor)
 return v

outdir=Path('work/particle_results');outdir.mkdir(exist_ok=True)
allresults=[];samplepaths=[]
for dmm in diameters:
 d=dmm/1000;pos=initial.copy();vel=uvw.copy();times=np.zeros(N);status=np.array(['active']*N,dtype='<U20');steps=np.zeros(N,int);collisions=np.zeros(N,int)
 tracks={k:[pos[k].copy()] for k in [0,15,31,63,95,127,159,191,223,255] if k<N}
 tic=time.monotonic();tau0=rho_p*d*d/(18*mu)
 for cycle in range(10000):
  active=np.flatnonzero(status=='active')
  if not len(active):break
  old=pos[active].copy();vold=vel[active].copy();water=field(old)
  missing=~np.isfinite(water).all(axis=1)
  if missing.any():status[active[missing]]='unresolved';active=active[~missing];old=old[~missing];vold=vold[~missing];water=water[~missing]
  if not len(active):break
  dt=np.minimum(.04,MAX_STEP_M/np.maximum(np.linalg.norm(vold,axis=1),.05))
  slip=np.linalg.norm(water-vold,axis=1);re=rho_f*d*slip/mu
  fd=np.where(re<1000,1+.15*re**.687,.0183*re)
  a=np.exp(-fd*dt/tau0)
  veq=water+((tau0/fd)*(1-rho_f/rho_p))[:,None]*grav
  vnew=veq+(vold-veq)*a[:,None]
  new=old+.5*(vold+vnew)*dt[:,None]
  pos[active]=new;vel[active]=vnew;times[active]+=dt;steps[active]+=1
  for k in tracks:
   if status[k]=='active' and (cycle%5==0):tracks[k].append(pos[k].copy())
  # Aperture crossings are resolved before generic wall contact.
  bottom=(new[:,1]<=.0042)&(np.hypot(new[:,0],new[:,2])<=.0505)
  main=(new[:,2]>=.3528)&(np.hypot(new[:,0],new[:,1]-.458)<=.0385)
  inlet=(new[:,2]>=.3292)&(np.hypot(new[:,0]-.2515,new[:,1]-.7195)<=.0255)
  status[active[bottom]]='bottom_outlet';status[active[main&~bottom]]='main_outlet';status[active[inlet&~main&~bottom]]='inlet_backflow'
  check=(status[active]=='active')
  if check.any():
   ids=active[check];p=pos[ids]
   ijk=np.rint((p-np.array([x[0],y[0],z[0]]))/(GRID_MM/1000)).astype(int)
   outside=np.any((ijk<0)|(ijk>=np.array(inside.shape)),axis=1)
   ijk=np.clip(ijk,0,np.array(inside.shape)-1)
   if WALL_MODE=='trap':near=(dist[tuple(ijk.T)]<1.75)|outside
   else:near=(~inside[tuple(ijk.T)])|outside|((cycle%5==0)&(dist[tuple(ijk.T)]<1.75))
   if near.any():
    validity=exact_inside(p[near]);hit=ids[near][~validity]
    if WALL_MODE=='trap':status[hit]=np.where(pos[hit,1]<.35,'hopper_wall','other_wall')
    elif len(hit):
     if WALL_MODE=='hoppertrap':
      lower=hit[pos[hit,1]<.35];status[lower]='hopper_wall';hit=hit[pos[hit,1]>=.35]
    if WALL_MODE!='trap' and len(hit):
     loc,distance,tri=trimesh.proximity.closest_point(mesh,pos[hit]);normal=mesh.face_normals[tri]
     vn=np.einsum('ij,ij->i',vel[hit],normal)
     vel[hit]=.75*(vel[hit]-vn[:,None]*normal)-.2*np.maximum(vn,0)[:,None]*normal
     pos[hit]=loc-normal*.00002
     collisions[hit]+=1
     status[hit[collisions[hit]>MAX_COLLISIONS]]='unresolved'
  expired=active[(status[active]=='active')&(times[active]>=180.)]
  status[expired]='unresolved'
  if cycle%500==0:print('d',dmm,'cycle',cycle,'active',sum(status=='active'),'elapsed',round(time.monotonic()-tic,1),flush=True)
 # Any particles left after the iteration cap remain numerically unresolved.
 status[status=='active']='unresolved'
 fractions={k:float(weights[status==k].sum()) for k in ['bottom_outlet','main_outlet','inlet_backflow','hopper_wall','other_wall','unresolved']}
 assert abs(sum(fractions.values())-1)<1e-10
 counts={k:int(sum(status==k)) for k in fractions}
 row={'diameter_mm':dmm,'grid_mm':GRID_MM,'seed_count':N,'wall_mode':WALL_MODE,'collision_limit':MAX_COLLISIONS,'max_spatial_step_m':MAX_STEP_M,'free_settling_m_s':terminal_speed(d),'tau_stokes_s':tau0,'fractions':fractions,'counts':counts,'mean_residence_s':float(np.sum(weights*times)),'max_steps':int(steps.max()),'max_collisions':int(collisions.max()),'max_particle_time_s':float(times.max())}
 allresults.append(row)
 suffix=f'_{WALL_MODE}'+(f'_c{MAX_COLLISIONS}' if MAX_COLLISIONS!=200 else '')+(f'_h{int(MAX_STEP_M*1000)}' if MAX_STEP_M!=.005 else '')
 np.savez_compressed(outdir/f'particle_{str(dmm).replace(".","p")}_{GRID_MM}mm_{N}seeds{suffix}.npz',start=initial,end=pos,status=status,weight=weights,time=times,collisions=collisions)
 for k,points in tracks.items():samplepaths.append({'diameter_mm':dmm,'seed':k,'status':status[k],'points':np.array(points).tolist()})
 print('RESULT',json.dumps(row,ensure_ascii=False),flush=True)
 (outdir/f'summary_{GRID_MM}mm_{N}seeds{suffix}.json').write_text(json.dumps(allresults,ensure_ascii=False,indent=2),encoding='utf-8')
(outdir/f'trajectories_{GRID_MM}mm_{N}seeds{suffix}.json').write_text(json.dumps(samplepaths,ensure_ascii=False),encoding='utf-8')
