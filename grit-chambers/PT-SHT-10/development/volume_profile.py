import sys
sys.path.insert(0,'work/particledeps')
import numpy as np, trimesh

m=trimesh.load('work/cavity_for_particle_model.stl')
m.apply_scale(.001)
m.apply_translation([-.297,0,-.297])
ys=np.linspace(.0045,.38,301)
areas=[]
for y in ys:
    s=m.section(plane_origin=[0,float(y),0],plane_normal=[0,1,0])
    if s is None:
        areas.append(0.);continue
    p=s.to_2D()[0]
    rings=sorted([abs(.5*np.sum(c[:-1,0]*c[1:,1]-c[1:,0]*c[:-1,1])) for c in p.discrete],reverse=True)
    areas.append(sum(a if i%2==0 else -a for i,a in enumerate(rings)))
vols=np.r_[0,np.cumsum((np.array(areas[:-1])+np.array(areas[1:]))/2*np.diff(ys))]
for target in [.005,.01,.015,.02]:
    print('target_L',target*1000,'height_m',np.interp(target,vols,ys))
for y in [.1,.15,.2,.24,.3,.38]:
    print('height_m',y,'cumulative_L',np.interp(y,ys,vols)*1000)
print('lower_cone_L',vols[-1]*1000,'mesh_total_L',m.volume*1000)
