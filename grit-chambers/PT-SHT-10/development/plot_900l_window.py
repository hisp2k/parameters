from pathlib import Path
import sys
sys.path.insert(0, str(Path('work/particledeps').resolve()))
sys.path.insert(1, str(Path('work/plotdeps').resolve()))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

dt=.1
t=np.arange(0,2400+dt,dt)
qin_rate=.006
qfeed=10/3600
volumes=[.2,.2,.2,.2,.1]

def scenario(starts):
    qin=np.zeros_like(t)
    for start,vol in zip(starts,volumes):
        end=start+vol/qin_rate
        qin+=qin_rate*np.clip(np.minimum(t+dt,end)-np.maximum(t,start),0,dt)/dt
    stock=np.zeros_like(t)
    prev=0.
    for i,rate in enumerate(qin):
        available=prev+rate*dt
        processed=min(qfeed*dt,available) if available>0 else 0.
        prev=available-processed
        stock[i]=prev
    return qin,stock

qin_close,stock_close=scenario([0,200/6,400/6,600/6,800/6])
qin_space,stock_space=scenario([0,600,1200,1800,2340])

fig,ax=plt.subplots(figsize=(10,5.5),layout='constrained')
ax.plot(t/60,stock_close*1000,lw=2.5,label='5 залпов подряд, 4 × 200 л + 100 л',color='#bb593b')
ax.plot(t/60,stock_space*1000,lw=2,label='Те же залпы с паузами (пример)',color='#287f9d')
ax.set(xlim=(0,40),ylim=(0,530),xlabel='Время от начала 40-минутного интервала, мин',ylabel='Дополнительный объём в буфере, л',title='900 л за 40 мин: зависимость буфера от расположения залпов')
ax.axhline(483.3333,ls=':',color='#bb593b',lw=1)
ax.annotate('483,3 л',xy=(2.5,483.3),xytext=(7,450),arrowprops={'arrowstyle':'->'},fontsize=11)
ax.annotate('107,4 л',xy=(0.55,107.4),xytext=(6,180),arrowprops={'arrowstyle':'->'},fontsize=11)
ax.grid(alpha=.25)
ax.legend(loc='upper right')
fig.text(.5,.01,'Идеальная подача 10 м³/ч запускается сразу; объём без осадка, свободного борта и резервов.',ha='center',fontsize=9)
fig.savefig('outputs/PT-SHT-10_900л_за_40мин_буфер.png',dpi=180,bbox_inches='tight')
print('max close',stock_close.max()*1000,'max spaced',stock_space.max()*1000)
