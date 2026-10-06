"""Independent spherical-particle settling check and velocity risk maps."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path('work/particledeps').resolve()))
sys.path.insert(1, str(Path('work/plotdeps').resolve()))
import numpy as np
from scipy.optimize import brentq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path('outputs')
rho_p, rho_w, mu, g = 2650.0, 997.574425, .0010016718, 9.81
diameters_mm = [.05, .075, .1, .15, .2, .25, .3, .5, .6, .75, 1, 1.5, 2]

def drag(re):
    return 24/re * (1 + .15 * re**.687) if re <= 1000 else .44

def equilibrium(d, v):
    re = rho_w * d * v / mu
    return .5 * drag(re) * rho_w * np.pi * d*d/4 * v*v - (rho_p-rho_w)*np.pi*d**3/6*g

rows=[]
for dm in diameters_mm:
    d=dm/1000
    ws=brentq(lambda v: equilibrium(d,v), 1e-8, 3, xtol=1e-13)
    re=rho_w*d*ws/mu
    st=(rho_p-rho_w)*g*d*d/(18*mu)
    residual=abs(equilibrium(d,ws))/((rho_p-rho_w)*np.pi*d**3/6*g)
    assert residual < 1e-7
    rows.append(dict(diameter_mm=dm,particle_density_kg_m3=rho_p,sphericity_assumed=1.0,
                     Re_p=re,C_D=drag(re),terminal_speed_m_s=ws,
                     stokes_speed_m_s=st,stokes_overestimate_percent=100*(st/ws-1),
                     force_residual_relative=residual))
with (OUT/'PT-SHT-10_аналитика_осаждения.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)

data=np.load('work/water_field_3d_12mm.npz')
x,y,z=data['x'],data['y'],data['z']
ix=int(np.argmin(abs(x)))
v=np.array(data['velocity'][ix],dtype=float)
up=np.maximum(v[:,:,1],0)
speed=np.linalg.norm(v,axis=2)
Z,Y=np.meshgrid(z,y)
valid=np.isfinite(up)

fig,axs=plt.subplots(1,2,figsize=(12,6),sharex=True,sharey=True,layout='constrained')
im=axs[0].pcolormesh(Z,Y,np.ma.masked_invalid(speed),shading='nearest',cmap='turbo',vmin=0,vmax=np.nanpercentile(speed,99))
fig.colorbar(im,ax=axs[0],label='|V|, м/с')
iv=axs[1].pcolormesh(Z,Y,np.ma.masked_invalid(v[:,:,1]),shading='nearest',cmap='RdBu_r',vmin=-.16,vmax=.16)
fig.colorbar(iv,ax=axs[1],label='V_y, м/с (+ вверх)')
dy=3;dz=3
axs[1].quiver(Z[::dy,::dz],Y[::dy,::dz],v[::dy,::dz,2],v[::dy,::dz,1],scale=5,color='k',width=.002,alpha=.45)
for ax,title in zip(axs,['FLOW-01/02 — скорость и векторы','FLOW-03 — вертикальная скорость']):
    ax.set(title=title,xlabel='z, м',ylabel='y, м',xlim=(-.32,.38),ylim=(0,.85),aspect='equal')
fig.suptitle('Плоскость x≈0; штатное поле воды Flow, выборка 12 мм; g направлена по −y')
fig.savefig(OUT/'PT-SHT-10_FLOW-01-03_скорости.png',dpi=180)
plt.close(fig)

fig,axs=plt.subplots(1,3,figsize=(14,5.7),sharex=True,sharey=True,layout='constrained')
stats=[]
for ax,dm in zip(axs,[.1,.25,.6]):
    ws=next(r['terminal_speed_m_s'] for r in rows if r['diameter_mm']==dm)
    R=up/ws
    im=ax.pcolormesh(Z,Y,np.ma.masked_invalid(np.minimum(R,3)),shading='nearest',cmap='YlOrRd',vmin=0,vmax=3)
    ax.contour(Z,Y,np.where(valid,R,np.nan),levels=[.5,1],colors=['#3e75a5','#222222'],linewidths=[1,1.3])
    ax.set(title=f'd={dm:g} мм; wₛ={ws*1000:.1f} мм/с',xlabel='z, м',xlim=(-.32,.38),ylim=(0,.85),aspect='equal')
    stats.append((dm,100*np.count_nonzero(valid & (R>1))/np.count_nonzero(valid)))
axs[0].set_ylabel('y, м')
fig.colorbar(im,ax=axs,label='R=max(V_y,0)/wₛ (цвет ограничен 3)')
fig.suptitle('FLOW-03 / индекс возможного восходящего удержания; R>1 не является вероятностью уноса')
fig.savefig(OUT/'PT-SHT-10_карты_R.png',dpi=180)
plt.close(fig)
print('rows',len(rows),'slice valid',np.count_nonzero(valid),'R>1 grid fractions',stats)
