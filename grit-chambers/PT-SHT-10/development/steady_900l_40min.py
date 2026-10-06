from pathlib import Path
import sys, math, csv
sys.path.insert(0,str(Path('work/particledeps').resolve()))
sys.path.insert(1,str(Path('work/plotdeps').resolve()))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out=Path('outputs')
qin=.9/2400
qp=10/3600
area=math.pi*.051**2/4
dt=.1
t=np.arange(0,44*60+dt,dt)
buffer=np.zeros_like(t)
pump=np.zeros_like(t)
inflow=np.where(t<2400,qin,0.)
running=False
level=0.
starts=[]
for i,sec in enumerate(t):
    if not running and level >=.2-1e-10:
        running=True
        starts.append(sec)
    available=level+inflow[i]*dt
    pumped=min(qp*dt,available) if running else 0.
    level=available-pumped
    if running and level<1e-12:
        running=False
        level=0.
    buffer[i]=level
    pump[i]=pumped/dt

with (out/'PT-SHT-10_равномерный_900л_40мин_баланс.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['time_s','inflow_L_s','controlled_feed_L_s','buffer_L'])
    for j in range(0,len(t),10):
        w.writerow([round(float(t[j]),2),round(float(inflow[j]*1000),6),round(float(pump[j]*1000),6),round(float(buffer[j]*1000),6)])

fig,axs=plt.subplots(2,1,figsize=(10,7),sharex=True,layout='constrained')
axs[0].plot(t/60,inflow*1000,lw=2.2,label='Равномерный приток: 0,375 л/с',color='#c5733a')
axs[0].plot(t/60,pump*1000,lw=1.7,label='Подача в Ø51: 2,778 л/с во время работы',color='#197894')
axs[0].set(ylabel='Расход, л/с',ylim=(-.1,3.15))
axs[0].legend(loc='upper left');axs[0].grid(alpha=.25)
axs[1].plot(t/60,buffer*1000,color='#427955',lw=2)
axs[1].axhline(200,color='#427955',ls=':',lw=1)
axs[1].set(xlabel='Время, мин',ylabel='Рабочее накопление, л',ylim=(-5,220),xlim=(0,44))
axs[1].grid(alpha=.25)
fig.suptitle('900 л равномерно за 40 мин: пример циклической подачи 10 м³/ч\nУсловное включение при 200 л и выключение после опорожнения буфера')
fig.savefig(out/'PT-SHT-10_равномерный_900л_40мин.png',dpi=180)
print('qin_lps',qin*1000,'qin_m3h',qin*3600,'v_direct',qin/area,'v_pumped',qp/area,'pump_total_s',sum(pump)*dt/qp,'max_buffer_l',max(buffer)*1000,'starts_min',[round(s/60,2) for s in starts],'end_buffer_l',buffer[-1]*1000,'total_pumped_l',sum(pump)*dt*1000)
