import sys
sys.path.insert(0, 'work/particledeps')
import numpy as np
import trimesh

m = trimesh.load('work/cavity_for_particle_model.stl')
m.apply_scale(.001)
m.apply_translation([-.297, 0, -.297])
print('bounds', m.bounds, 'volume_L', m.volume * 1000)
for y in [.24, .30, .38, .40, .45, .50, .55, .60, .65, .70, .75, .80, .82]:
    s = m.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    if s is None:
        print(y, 'none')
        continue
    paths = s.to_2D()[0].discrete
    rings = sorted((abs(.5 * np.sum(c[:-1, 0] * c[1:, 1] - c[1:, 0] * c[:-1, 1])) for c in paths), reverse=True)
    area = sum((-1)**i * ring for i, ring in enumerate(rings))
    print(y, 'area_m2', round(area, 6), 'rings', [round(x, 6) for x in rings])
