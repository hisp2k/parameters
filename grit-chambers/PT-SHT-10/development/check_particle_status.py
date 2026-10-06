import sys
sys.path.insert(0,'work/particledeps')
import numpy as np
p='work/pt-sht-10-210l/particle_results/particle_0p2_15mm_256seeds_hoppertrap.npz'
a=np.load(p)
for s in ['hopper_wall','main_outlet','unresolved']:
 m=a['status']==s
 print(s,m.sum(),'y range',np.percentile(a['end'][m,1],[0,25,50,75,100]) if m.any() else None,'collision',np.percentile(a['collisions'][m],[0,25,50,75,100]) if m.any() else None)
