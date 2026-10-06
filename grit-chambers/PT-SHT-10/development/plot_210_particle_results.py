import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('work/plotdeps').resolve()))
sys.path.insert(0,str(Path('work/particledeps').resolve()))
import numpy as np,trimesh,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

case=sys.argv[1] if len(sys.argv)>1 else 'Q10'
root=Path('work/pt-sht-10-210l/particle_results')
suffix='_'+case if case!='Q10' else ''
rows=json.loads((root/f'summary_15mm_256seeds_hoppertrap{suffix}.json').read_text(encoding='utf-8'))
paths=json.loads((root/f'trajectories_15mm_256seeds_hoppertrap{suffix}.json').read_text(encoding='utf-8'))
out=Path('outputs')
q={'Q10':'10,00','Q2p09':'2,09'}[case]
colors={'hopper_wall':'#358667','main_outlet':'#d5813a','unresolved':'#9ba4ad'}
labels={'hopper_wall':'Контакт с нижней стенкой','main_outlet':'Основной выход','unresolved':'Неразрешённые траектории'}
diam=[r['diameter_mm'] for r in rows]
fig,ax=plt.subplots(figsize=(9.5,5.5),layout='constrained')
left=np.zeros(len(rows))
for key in ['hopper_wall','main_outlet','unresolved']:
 vals=np.array([r['fractions'][key]*100 for r in rows])
 ax.barh(range(len(rows)),vals,left=left,color=colors[key],height=.65,label=labels[key])
 left+=vals
for i,r in enumerate(rows):
 v=r['fractions']['hopper_wall']*100
 ax.text(max(1,v-1),i,f'{v:.1f}%',color='white',ha='right',va='center',fontsize=9)
ax.set(yticks=range(len(rows)),yticklabels=[f'{x:.2f}' for x in diam],xlim=(0,100),xlabel='Доля введённой массы данной фракции, %',ylabel='Диаметр частицы, мм')
ax.set_title(f'PT-SHT-10-210L · Q = {q} м³/ч · демонстрационная трассировка\n256 точек; зелёное = первый контакт с нижней стенкой, не удержание осадка')
ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True);ax.legend(loc='lower right',fontsize=8)
fig.savefig(out/f'PT-SHT-10_210л_частицы_{case}.png',dpi=180)
plt.close(fig)

mesh=trimesh.load('work/pt-sht-10-210l/CADparts/CAD210_fluid_cavity.STL')
mesh.apply_scale(.001);mesh.apply_translation([-.297,0,-.297])
section=mesh.section(plane_origin=[0,0,0],plane_normal=[1,0,0])
sel=[.10,.20,.25]
fig,axs=plt.subplots(1,3,figsize=(12,5),sharex=True,sharey=True,layout='constrained')
for ax,d in zip(axs,sel):
 for loop in section.discrete:ax.plot(loop[:,2],loop[:,1],color='#3e4b55',lw=.7,alpha=.8)
 for item in [p for p in paths if p['diameter_mm']==d]:
  v=np.array(item['points'])
  if len(v)<2:continue
  ax.plot(v[:,2],v[:,1],color=colors.get(item['status'],'gray'),lw=.75,alpha=.65)
  ax.scatter(v[-1,2],v[-1,1],s=10,color=colors.get(item['status'],'gray'))
 ax.axhline(.229,color='#358667',lw=.7,ls='--')
 ax.set(xlim=(-.32,.38),ylim=(0,1.02),aspect='equal',xlabel='z, м',title=f'{d:.2f} мм')
 ax.grid(alpha=.15)
axs[0].set_ylabel('y, м')
fig.suptitle(f'Примеры траекторий · Q = {q} м³/ч · цвет конечного исхода\nЗелёный — контакт с нижней стенкой; оранжевый — основной выход; серый — неопределённо',fontsize=10)
fig.savefig(out/f'PT-SHT-10_210л_траектории_{case}.png',dpi=180)
plt.close(fig)
print('PLOTS',case,flush=True)
