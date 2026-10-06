import sys,csv,json
from pathlib import Path
sys.path.insert(0,str(Path('work/plotdeps').resolve()))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
out=Path('outputs');folder=Path('work/pt-sht-10-demo/Модель/2')
rows=list(csv.DictReader((out/'PT-SHT-10_поля_воды.csv').open(encoding='utf-8-sig')))
fig,axs=plt.subplots(1,2,figsize=(12,6),layout='constrained')
for ax,plane in zip(axs,['x=0','y=0.7195']):
 rs=[r for r in rows if r['plane']==plane]
 horizontal='z_m' if plane=='x=0' else 'x_m';vertical='y_m' if plane=='x=0' else 'z_m'
 xx=sorted(set(float(r[horizontal]) for r in rs));yy=sorted(set(float(r[vertical]) for r in rs))
 a=np.full((len(yy),len(xx)),np.nan)
 for r in rs:
  if r['valid']=='1':a[yy.index(float(r[vertical])),xx.index(float(r[horizontal]))]=float(r['speed_m_s'])
 im=ax.pcolormesh(xx,yy,np.ma.masked_invalid(a),cmap='viridis',vmin=0,vmax=1.6,shading='nearest')
 ax.set(title='Сечение '+plane+' м',xlabel=horizontal[0]+' [м]',ylabel=vertical[0]+' [м]',aspect='equal')
 ax.set_facecolor('#eeeeee');ax.grid(alpha=.15)
 fig.colorbar(im,ax=ax,label='Скорость воды, м/с',shrink=.8)
fig.suptitle('PT-SHT-10 · 10 м³/ч · Flow Simulation · сетка 274 398 жидкостных ячеек\nИнтерполяция результата 2.fld; шаг выборки 10 мм, серое — нет данных',fontsize=12)
fig.savefig(out/'PT-SHT-10_скорость_воды.png',dpi=180);plt.close(fig)
def goal(n):return np.genfromtxt(folder/'Goals.DAT'/f'{n}.txt',names=True,delimiter='\t')
ip=goal('Inlet_TotalP');op=goal('MainOutlet_TotalP');q=goal('MainOutlet_Q');v=goal('Global_Velocity_Max')
head=(ip['Value']-op['Value'])/(997.5744250027426*9.81)+.7195-.458
fig,axs=plt.subplots(2,1,figsize=(10,7),layout='constrained')
axs[0].plot(ip['Iteration'],head,color='#16697a');axs[0].set(ylabel='Потери полного напора, м',ylim=(0,.5),title='Сходимость решения воды: подробная сетка')
axs[1].plot(q['Iteration'],-q['Value']*3600,color='#cf5c36');axs[1].axhline(9.9,color='gray',linestyle='--');axs[1].set(xlabel='Итерация',ylabel='Основной отток, м³/ч')
for a in axs:a.grid(alpha=.25)
fig.savefig(out/'PT-SHT-10_сходимость.png',dpi=180);plt.close(fig)
print('plots saved')
