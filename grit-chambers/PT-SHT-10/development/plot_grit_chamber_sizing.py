from pathlib import Path
import sys,csv
sys.path.insert(0,str(Path('work/particledeps').resolve()))
sys.path.insert(1,str(Path('work/plotdeps').resolve()))
import numpy as np,trimesh,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out=Path('outputs')
mesh=trimesh.load('work/cavity_for_particle_model.stl')
mesh.apply_scale(.001)
mesh.apply_translation([-.297,0,-.297])
assert mesh.is_watertight
ys=np.linspace(.0045,.38,301)
areas=[]
for y in ys:
    section=mesh.section(plane_origin=[0,float(y),0],plane_normal=[0,1,0])
    if section is None:
        areas.append(0.);continue
    rings=sorted([abs(.5*np.sum(c[:-1,0]*c[1:,1]-c[1:,0]*c[:-1,1]))
                  for c in section.to_2D()[0].discrete],reverse=True)
    areas.append(sum(a if i%2==0 else -a for i,a in enumerate(rings)))
vols=np.r_[0,np.cumsum((np.array(areas[:-1])+np.array(areas[1:]))/2*np.diff(ys))]
y5=float(np.interp(.005,vols,ys))
y10=float(np.interp(.010,vols,ys))
with (out/'PT-SHT-10_объём_нижнего_конуса_по_высоте.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['height_from_CAD_origin_m','cumulative_cavity_volume_below_L'])
    for y,v in zip(ys,vols):w.writerow([round(float(y),6),round(float(v*1000),4)])

side=mesh.section(plane_origin=[0,0,0],plane_normal=[1,0,0])
fig,axs=plt.subplots(1,2,figsize=(11,6),layout='constrained')
for loop in side.discrete:axs[0].plot(loop[:,2],loop[:,1],color='#38464c',lw=1.4)
for y,c,label in [(y5,'#278761','5 л: рабочая отметка'),(y10,'#c88424','10 л: предельная отметка')]:
    axs[0].axhline(y,ls='--',color=c,lw=1.6)
    axs[0].text(-.31,y+.012,label,color=c,fontsize=9)
axs[0].scatter([.329,.353,0],[.7195,.458,.004],color=['#249e5d','#db772d','#1c7caa'],s=38,zorder=5)
axs[0].set(xlabel='z, м',ylabel='Высота y, м',title='Сечение полости CAD-копии\nс отметками заполнения нижнего конуса',xlim=(-.35,.4),ylim=(-.02,.86),aspect='equal')
axs[0].grid(alpha=.2)

axs[1].plot(vols*1000,ys,color='#3b718a',lw=2.2)
axs[1].scatter([5,10],[y5,y10],c=['#278761','#c88424'],s=65,zorder=5)
axs[1].annotate(f'5 л, y={y5:.3f} м',xy=(5,y5),xytext=(11,.15),arrowprops={'arrowstyle':'->'},fontsize=10)
axs[1].annotate(f'10 л, y={y10:.3f} м',xy=(10,y10),xytext=(19,.22),arrowprops={'arrowstyle':'->'},fontsize=10)
axs[1].axhline(.24,ls=':',color='#c25959',label='Нижний край обратного конуса ≈0,24 м')
axs[1].set(xlabel='Геометрический объём полости ниже отметки, л',ylabel='Высота y, м',title='Заполнение нижнего конуса\nпо сечениям 3D полости',xlim=(0,42),ylim=(0,.39))
axs[1].legend(fontsize=8,loc='upper left');axs[1].grid(alpha=.2)
fig.suptitle('PT-SHT-10 — ёмкость для накопления песка в существующей CAD-копии\nГеометрическая оценка; не расчёт эффективности улавливания')
fig.savefig(out/'PT-SHT-10_зона_накопления_песка.png',dpi=180)
print('mesh_volume_L',mesh.volume*1000,'y5_m',y5,'y10_m',y10,'below_0p24_L',np.interp(.24,ys,vols)*1000)
