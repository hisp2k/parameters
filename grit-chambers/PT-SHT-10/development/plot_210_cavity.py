import sys
from pathlib import Path
sys.path.insert(0,'work/particledeps')
sys.path.insert(0,'work/plotdeps')
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.family']='DejaVu Sans'
mesh=trimesh.load('work/pt-sht-10-210l/CADparts/CAD210_fluid_cavity.STL')
mesh.apply_scale(.001)
mesh.apply_translation([-.297,0,-.297])
fig,(a,b)=plt.subplots(1,2,figsize=(13,6),gridspec_kw={'width_ratios':[.85,1]})
for ax,origin,normal,horizontal,vertical in [
    (a,[0,0,0],[1,0,0],2,1),
    (b,[0,.8945,0],[0,1,0],0,2)]:
    sec=mesh.section(plane_origin=origin,plane_normal=normal)
    assert sec is not None
    for line in sec.discrete:
        ax.plot(line[:,horizontal],line[:,vertical],color='#163d56',lw=1.4)
    ax.set_aspect('equal')
    ax.grid(alpha=.2)
a.scatter([.329,.353,0],[.8945,.458,.004],c=['#009979','#e58a32','#567eaa'],s=42,zorder=4)
a.annotate('Вход Ø51',(.329,.8945),xytext=(.40,.89),arrowprops={'arrowstyle':'-', 'color':'#009979'})
a.annotate('Выход Ø78',(.353,.458),xytext=(.40,.52),arrowprops={'arrowstyle':'-', 'color':'#e58a32'})
a.text(0,.12,'Нижний накопитель ≈10 л',ha='center',fontsize=9)
a.set_xlim(-.38,.55);a.set_ylim(-.03,1.08)
a.set_xlabel('z, м');a.set_ylabel('y, м');a.set_title('Сечение x=0')
b.scatter([.2515],[.329],c='#009979',s=42,zorder=4)
b.annotate('Тангенциальный вход',(.2515,.329),xytext=(-.1,.38),arrowprops={'arrowstyle':'-', 'color':'#009979'})
b.set_xlim(-.39,.42);b.set_ylim(-.38,.43)
b.set_xlabel('x, м');b.set_ylabel('z, м');b.set_title('Сечение на оси входа, y=0,8945 м')
fig.suptitle(f'Реальная CAD-полость перестроенной копии: 210,231 л',fontsize=15)
fig.tight_layout()
out=Path('outputs/PT-SHT-10_полость_210л.png')
fig.savefig(out,dpi=180)
print(out,mesh.volume*1000,flush=True)
