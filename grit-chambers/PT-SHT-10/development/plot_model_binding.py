"""CAD cavity and port coordinate diagram for PT-SHT-10 traceability."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('work/particledeps').resolve()))
sys.path.insert(1,str(Path('work/plotdeps').resolve()))
import numpy as np,trimesh,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out=Path('outputs')
data=json.loads((out/'PT-SHT-10_привязка_расчёта_к_CAD.json').read_text(encoding='utf-8'))
mesh=trimesh.load('work/cavity_for_particle_model.stl');mesh.apply_scale(.001);mesh.apply_translation([-.297,0,-.297])
assert mesh.is_watertight
side=mesh.section(plane_origin=[0,0,0],plane_normal=[1,0,0])
top=mesh.section(plane_origin=[0,.7195,0],plane_normal=[0,1,0])
ports={p['port']:p['center_m'] for p in data['boundaries']}

fig,axs=plt.subplots(1,2,figsize=(12,6),layout='constrained')
for loop in side.discrete:axs[0].plot(loop[:,2],loop[:,1],color='#323e43',lw=1.2)
axs[0].scatter([ports['main_outlet'][2],ports['bottom_outlet'][2]],[ports['main_outlet'][1],ports['bottom_outlet'][1]],s=60,c=['#db732a','#2679a7'],zorder=5)
axs[0].scatter(ports['inlet'][2],ports['inlet'][1],s=65,c='#2e9147',marker='D',zorder=5)
axs[0].annotate('Вход Ø51 мм\nпроекция; x=0,2515 м',xy=(.329,.7195),xytext=(-.12,.77),arrowprops={'arrowstyle':'->'},fontsize=9)
axs[0].annotate('Основной выход Ø78 мм',xy=(.353,.458),xytext=(.04,.36),arrowprops={'arrowstyle':'->'},fontsize=9)
axs[0].annotate('Нижний выпуск Ø102 мм',xy=(0,.004),xytext=(-.29,.1),arrowprops={'arrowstyle':'->'},fontsize=9)
axs[0].set(xlabel='z, м',ylabel='y, м',title='Вертикальное сечение полости x=0\nзелёная точка — проекция входа',xlim=(-.36,.4),ylim=(-.02,.87),aspect='equal')

for loop in top.discrete:axs[1].plot(loop[:,0],loop[:,2],color='#323e43',lw=1.2)
axs[1].scatter([ports['inlet'][0],0,0],[ports['inlet'][2],ports['main_outlet'][2],0],s=55,c=['#2e9147','#db732a','#2679a7'],zorder=5)
axs[1].annotate('Вход Q=10 м³/ч',xy=(.2515,.329),xytext=(-.23,.31),arrowprops={'arrowstyle':'->'},fontsize=9)
axs[1].arrow(.2515,.32,0,-.13,width=.0025,head_width=.018,head_length=.018,length_includes_head=True,color='#2e9147')
axs[1].plot([0,.2515],[0,0],ls=':',color='#666')
axs[1].annotate('Смещение оси входа\n0,2515 м',xy=(.12,0),xytext=(-.27,-.34),arrowprops={'arrowstyle':'->'},fontsize=9)
axs[1].set(xlabel='x, м',ylabel='z, м',title='Горизонтальное сечение y=0,7195 м\nметки остальных портов — проекции; вход: −z',xlim=(-.36,.38),ylim=(-.38,.39),aspect='equal')
for ax in axs:ax.grid(alpha=.18)
fig.suptitle('PT-SHT-10 / узел бункера 01.PT.SHT.01.00.00.00\nКонтур — полость демонстрационной CAD-копии; метки — грани граничных условий Flow')
fig.savefig(out/'PT-SHT-10_привязка_портов_к_модели.png',dpi=180)
print('figure saved')
