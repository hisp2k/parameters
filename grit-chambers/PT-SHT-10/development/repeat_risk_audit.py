"""Repeat independently computable hydrodynamic risk audit on saved Flow field."""
import csv,sys,json
from pathlib import Path
sys.path.insert(0,str(Path('work/particledeps').resolve()))
sys.path.insert(1,str(Path('work/plotdeps').resolve()))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out=Path('outputs')
analytic=list(csv.DictReader((out/'PT-SHT-10_аналитика_осаждения.csv').open(encoding='utf-8-sig')))
records=[]
for mm in [12,15]:
    d=np.load(f'work/water_field_3d_{mm}mm.npz')
    y=d['y'];v=d['velocity'].astype(float)
    good=np.isfinite(v[:,:,:,0]) & d['inside']
    speed=np.linalg.norm(v,axis=3)
    vy=v[:,:,:,1]
    Y=y[None,:,None]
    for r in analytic:
        dm=float(r['diameter_mm']);ws=float(r['terminal_speed_m_s'])
        for region,mask in [('full',good),('lower_y_lt_0p35',good & (Y<.35))]:
            n=int(mask.sum());risk=int((mask & (vy>ws)).sum())
            row={'field_sample_mm':mm,'region':region,'diameter_mm':dm,'terminal_speed_mm_s':1000*ws,
                 'valid_nodes':n,'upward_faster_than_settling_nodes':risk,
                 'R_gt_1_percent_of_sampled_nodes':100*risk/n,
                 'median_speed_m_s':float(np.nanmedian(speed[mask])),
                 'p95_speed_m_s':float(np.nanpercentile(speed[mask],95)),
                 'upward_flow_nodes_percent':float(100*np.count_nonzero(mask & (vy>0))/n)}
            records.append(row)

with (out/'PT-SHT-10_повторная_проверка_R_3D.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=records[0].keys());w.writeheader();w.writerows(records)

dat=np.load('work/water_field_3d_12mm.npz')
x,y,z=dat['x'],dat['y'],dat['z'];vy=dat['velocity'][:,:,:,1]
ws=next(float(r['terminal_speed_m_s']) for r in analytic if float(r['diameter_mm'])==.25)
fig,axs=plt.subplots(1,3,figsize=(14,5),sharex=True,sharey=True,layout='constrained')
for ax,ym in zip(axs,[.18,.36,.60]):
    iy=int(np.argmin(abs(y-ym))); R=np.maximum(vy[:,iy,:],0)/ws
    X,Z=np.meshgrid(x,z,indexing='ij')
    im=ax.pcolormesh(X,Z,np.ma.masked_invalid(np.minimum(R,3)),shading='nearest',vmin=0,vmax=3,cmap='YlOrRd')
    ax.contour(X,Z,np.where(np.isfinite(R),R,np.nan),levels=[.5,1],colors=['#387cb1','#222222'],linewidths=[1,1.3])
    ax.set(title=f'y≈{y[iy]:.3f} м',xlabel='x, м',xlim=(-.32,.32),ylim=(-.32,.36),aspect='equal')
axs[0].set_ylabel('z, м')
fig.colorbar(im,ax=axs,label='R=max(Vy,0)/ws (цвет ограничен 3)')
fig.suptitle('d=0,25 мм; горизонтальные срезы поля Flow mesh-3; шаг выборки 12 мм\nR>1 — локальный индикатор, а не эффективность захвата')
fig.savefig(out/'PT-SHT-10_R_025_горизонтальные_срезы.png',dpi=180)
plt.close(fig)

for region in ['full','lower_y_lt_0p35']:
    print(region)
    for dm in [.1,.25,.6]:
        for mm in [12,15]:
            r=next(z for z in records if z['region']==region and z['diameter_mm']==dm and z['field_sample_mm']==mm)
            print(dm,mm,'nodes',r['valid_nodes'],'R>1%',round(r['R_gt_1_percent_of_sampled_nodes'],2),'speed median',round(r['median_speed_m_s'],4))
