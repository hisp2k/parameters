import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('work/particledeps').resolve()))
sys.path.insert(1,str(Path('work/plotdeps').resolve()))
import numpy as np,trimesh,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path('work/particle_results');out=Path('outputs')
trap=json.loads((root/'summary_15mm_128seeds.json').read_text(encoding='utf-8'))
hopper=json.loads((root/'summary_12mm_128seeds_hoppertrap_c5000.json').read_text(encoding='utf-8'))
reflect=json.loads((root/'summary_12mm_128seeds_reflect_c5000.json').read_text(encoding='utf-8'))
coarse=json.loads((root/'summary_15mm_128seeds_reflect_c5000.json').read_text(encoding='utf-8'))
size=[r['diameter_mm'] for r in hopper]
assert size==[r['diameter_mm'] for r in reflect]
fig,axs=plt.subplots(2,1,figsize=(10.5,8))
colors={'hopper_wall':'#418a59','bottom_outlet':'#0077b6','main_outlet':'#e08736','unresolved':'#bcbcbc'}
for ax,rows,title in [(axs[0],hopper,'Остановка при первом контакте со стенкой ниже y=0,35 м'),(axs[1],reflect,'Отражение от стенок; предел — 5000 столкновений')]:
 left=np.zeros(len(size));labels={'hopper_wall':'Первый контакт в нижней области','bottom_outlet':'Пересекло нижнее отверстие','main_outlet':'Ушло через основной выход','unresolved':'Незавершённые траектории'}
 for key in ['hopper_wall','bottom_outlet','main_outlet','unresolved']:
  vals=np.array([r['fractions'][key]*100 for r in rows])
  ax.barh(range(len(size)),vals,left=left,color=colors[key],label=labels[key],height=.65)
  left+=vals
 ax.set(yticks=range(len(size)),yticklabels=[f'{x:.2f}' for x in size],xlim=(0,100),xlabel='Доля введённой массы данной фракции, %',ylabel='Диаметр частицы, мм',title=title)
 ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
for y,rr in enumerate(hopper):
 axs[0].text(rr['fractions']['hopper_wall']*100-1.2,y,f"{rr['fractions']['hopper_wall']*100:.1f}%",va='center',ha='right',color='white',fontsize=8)
for y,rr in enumerate(reflect):
 axs[1].text(max(1,rr['fractions']['bottom_outlet']*100-1),y,f"{rr['fractions']['bottom_outlet']*100:.1f}%",va='center',ha='right',fontsize=8,color='white' if rr['fractions']['bottom_outlet']>.15 else 'black')
fig.suptitle('Предварительная трассировка по полю воды · 10 м³/ч · 128 стартовых точек\nКонтакт со стенкой и выход через отверстие не доказывают устойчивое удержание осадка',fontsize=11)
handles,labels=axs[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.01),ncol=2,fontsize=9)
fig.subplots_adjust(left=.11,right=.98,top=.88,bottom=.16,hspace=.40)
fig.savefig(out/'PT-SHT-10_осаждение_по_фракциям.png',dpi=190);plt.close(fig)

mesh=trimesh.load('work/cavity_for_particle_model.stl');mesh.apply_scale(.001);mesh.apply_translation([-.297,0,-.297])
section=mesh.section(plane_origin=[0,0,0],plane_normal=[1,0,0])
paths=json.loads((root/'trajectories_12mm_128seeds_hoppertrap_c5000.json').read_text(encoding='utf-8'))
fig,axs=plt.subplots(1,3,figsize=(13,5),sharex=True,sharey=True,layout='constrained')
for ax,d,c in zip(axs,[.1,.25,.6],['#3274a1','#ba6b28','#a42636']):
 for loop in section.discrete:
  ax.plot(loop[:,2],loop[:,1],color='#303c43',lw=.8,alpha=.6)
 relevant=[p for p in paths if p['diameter_mm']==d]
 for item in relevant:
  v=np.array(item['points']);ax.plot(v[:,2],v[:,1],color=c,lw=.8,alpha=.75)
  ax.scatter(v[-1,2],v[-1,1],s=12,color=colors.get(item['status'],'gray'),zorder=5)
 ax.scatter([.329,.353,0],[.7195,.458,.004],marker='x',s=40,c=['#3274a1','#e08736','#0077b6'],zorder=6)
 ax.set(title=f'd = {d:.2f} мм',xlabel='z, м',xlim=(-.32,.38),ylim=(0,.86),aspect='equal');ax.grid(alpha=.15)
axs[0].set_ylabel('y, м')
fig.suptitle('Примеры траекторий, проекция на плоскость z–y\nКонтур полости: сечение x=0; зелёные концы — первый контакт со стенкой ниже y=0,35 м',fontsize=11)
fig.savefig(out/'PT-SHT-10_траектории_песка.png',dpi=190);plt.close(fig)

fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
yy=np.arange(len(size));h=.36
v15=[r['fractions']['bottom_outlet']*100 for r in coarse];v12=[r['fractions']['bottom_outlet']*100 for r in reflect]
ax.barh(yy-h/2,v15,height=h,color='#49a3b1',label='Поле 15 мм')
ax.barh(yy+h/2,v12,height=h,color='#116b93',label='Поле 12 мм')
for y0,a,b in zip(yy,v15,v12):
 ax.text(a+1,y0-h/2,f'{a:.1f}%',va='center',fontsize=8)
 ax.text(b+1,y0+h/2,f'{b:.1f}%',va='center',fontsize=8)
ax.set(yticks=yy,yticklabels=[f'{x:.2f}' for x in size],xlim=(0,112),xlabel='Пересекло нижнее отверстие, % введённой массы данной фракции',ylabel='Диаметр, мм',title='Чувствительность к шагу выборки поля воды (все стенки отражают)')
ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True);ax.legend(loc='lower right')
fig.savefig(out/'PT-SHT-10_чувствительность_сетки_частиц.png',dpi=190);plt.close(fig)
print('plots saved')
