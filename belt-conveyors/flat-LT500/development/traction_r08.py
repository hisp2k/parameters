from pathlib import Path
import json,math,itertools
import numpy as np
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер';g=9.80665
inputs=dict(L_calc_m=10.,belt_width_mm=500.,q_material_kg_m=30.,peak_kg=15.,q_belt_kg_m_assumed=5.,moving_mass_equivalent_other_kg_assumed=60.,carry_pitch_m_assumed=.75,return_pitch_m_assumed=2.,carry_relative_sag_proposed=.01,return_relative_sag_proposed=.02,D_example_m=.2,wrap_deg_example=180.,eta_example=.85,angle_active_deg=1.5,v_active_m_s=.2,c_active=.03,R_misc_active_N=100.,mu_active=.2,start_time_active_s=3.,stop_time_active_s=3.,breakaway_factor_example=1.5,jam_output_torque_limit_Nm=None)
def calc(q,peak,angle,v,c,extra,mu,mode,tstart=1.,tstop=1.,pc=.75,pr=2.,sc=.01,sr=.02,qb=5.,L=10.):
 a=0 if mode=='RUN' else v/tstart if mode=='START' else -v/tstop;k=1.5 if mode=='START' else 1.;rad=math.radians(angle);cs=math.cos(rad);sn=math.sin(rad);mC=30.;mR=30.
 rc=k*c*g*(q+qb)*cs-g*(q+qb)*sn+(q+qb+mC/L)*a
 rr=k*c*g*qb*cs+g*qb*sn+(qb+mR/L)*a
 point=peak*(k*c*g*cs-g*sn+a);clean=k*extra;tailoff=clean+rr*L;Fu=tailoff+rc*L+point
 carrymin=tailoff+min(0,rc*L)+min(0,point);carrymax=tailoff+max(0,rc*L)+max(0,point);retmin=min(clean,tailoff)
 sagC=g*cs*((q+qb)*pc/(8*sc)+peak/(4*sc));sagR=g*cs*qb*pr/(8*sr)
 grip=0 if abs(Fu)<1e-12 else abs(Fu)/math.expm1(mu*math.pi)
 out=max(sagC-carrymin,sagR-retmin,grip-min(0,Fu),-min(0,carrymin,retmin,Fu));tin=out+Fu;tail=out+tailoff;tmax=out+max(0,clean,tailoff,carrymax,Fu)
 # Independent tension-ratio, segment minima and both global/branch balances.
 assert min(tin,out)>0 and max(tin,out)/min(tin,out)<=math.exp(mu*math.pi)+1e-9
 assert out+carrymin>=sagC-1e-8 and out+retmin>=sagR-1e-8
 totalmass=q*L+peak+2*qb*L+mC+mR
 net=k*(c*g*cs*(q*L+peak+2*qb*L)+extra)-g*sn*(q*L+peak)+totalmass*a
 assert abs(Fu-net)<1e-8
 # Explicit positions of the single peak verify the offset bound (not independent feed peaks).
 for f in [0,.25,.5,.75,1]:
  nodes=[tailoff,tailoff+rc*L*f,tailoff+rc*L*f+point,Fu]
  assert min(nodes)>=carrymin-1e-8 and max(nodes)<=carrymax+1e-8
 return dict(mode=mode,q_material_kg_m=q,peak_kg=peak,angle_deg=angle,v_m_s=v,c_equivalent=c,R_misc_N=extra,mu_example=mu,acceleration_m_s2=a,k_breakaway=k,rc_N_m=rc,rr_N_m=rr,peak_step_N=point,cleaner_step_N=clean,tail_offset_N=tailoff,carry_min_offset_N=carrymin,return_min_offset_N=retmin,Fu_N=Fu,T_sag_carry_N=sagC,T_sag_return_N=sagR,T_grip_low_N=grip,T_out_N=out,T_in_N=tin,T_tail_N=tail,T_max_loop_N=tmax,drive_resultant_N=tin+out,tail_resultant_N=2*tail,drive_X_N=-(tin+out)*cs,drive_Y_N=(tin+out)*sn,tail_X_N=2*tail*cs,tail_Y_N=-2*tail*sn,belt_torque_example_Nm=Fu*.1,belt_power_signed_kW=Fu*v/1000,belt_tmax_N_mm=tmax/500,Meq_kg=totalmass)
active=[calc(30,15,1.5,.2,.03,100,.2,mode,3,3) for mode in ['RUN','START','STOP']]
grid=[]
for (q,peak),angle,v,(label,c,extra),mu,mode in itertools.product([(0,0),(15,0),(30,15)],[1,2],[.1,.2,.3],[('LOW',.01,0),('MID',.03,100),('HIGH',.06,200)],[.1,.2,.3],['RUN','START','STOP']):
 r=calc(q,peak,angle,v,c,extra,mu,mode);r['resistance_case']=label;r['id']=len(grid)+1;grid.append(r)
assert len(grid)==486
selected=[x for x in grid if x['q_material_kg_m']==30 and x['peak_kg']==15 and x['angle_deg']==2 and x['v_m_s']==.3]
extrema={k:{'min':min(x[k] for x in grid),'min_id':min(grid,key=lambda x:x[k])['id'],'max':max(x[k] for x in grid),'max_id':max(grid,key=lambda x:x[k])['id']} for k in ['Fu_N','drive_resultant_N','tail_resultant_N','T_max_loop_N','belt_torque_example_Nm','belt_power_signed_kW']}
def meanoff(r,xi):return r['cleaner_step_N']+(.75*r['rr_N_m']+.25*r['rc_N_m'])*10+.5*r['peak_step_N']*(1-xi)
mean_target=max(r['T_out_N']+max(meanoff(r,0),meanoff(r,1)) for r in grid)
installed=[]
for r in grid:
 for xi in [0,.5,1]:
  out=mean_target-meanoff(r,xi);assert out>=r['T_out_N']-1e-8;tin=out+r['Fu_N'];tail=out+r['tail_offset_N'];installed.append(dict(source_id=r['id'],peak_position_fraction=xi,T_out_N=out,T_in_N=tin,T_tail_N=tail,drive_resultant_N=out+tin,tail_resultant_N=2*tail))
installed_extrema={k:dict(min=min(x[k] for x in installed),max=max(x[k] for x in installed),max_case=max(installed,key=lambda x:x[k])) for k in ['drive_resultant_N','tail_resultant_N']}
sag_cases=[]
for p,s,peak in itertools.product([.5,.75,1.],[.01,.02],[0,15]):sag_cases.append(dict(pitch_m=p,relative_sag=s,peak_kg=peak,T_required_N=g*math.cos(math.radians(1.5))*(35*p/(8*s)+peak/(4*s))))
# Independent finite-difference string equilibrium, prescribed uniform + central point normal load.
n=1000;p=.75;dx=p/n;F=g*math.cos(math.radians(1.5))*15;w=g*math.cos(math.radians(1.5))*35;H=active[0]['T_sag_carry_N'];x=np.linspace(0,p,n+1);y=w*x*(p-x)/(2*H)+F*np.minimum(x,p-x)/(2*H)
res=H*(2*y[1:-1]-y[:-2]-y[2:])/dx**2-w;res[n//2-1]-=F/dx;assert np.max(np.abs(res))<1e-4;assert abs(max(y)-.01*p)<1e-12
d=dict(revision='R08',scope='Условная тяга, пуск/торможение, натяжение и силы на концевые барабаны; фрикционная лента на роликах',inputs=inputs,active_cases=active,selected27=selected,all486=grid,extrema=extrema,sag_cases=sag_cases,speed_examples=[dict(v_m_s=v,flow_at_30kg_m_t_h=3.6*30*v,drum_rpm_at_D200=60*v/(math.pi*.2)) for v in [.1,.2,.3]],checks=dict(force_balance_all486=True,capstan_and_sag_constraints_all486=True,single_peak_position_bounds=True,finite_difference_string_nodes=n+1,sag_difference_equation_max_residual_N_m=float(max(abs(res))),deflection_target_m=float(max(y)),component_selected=False,simulation_performed=False),sources=[dict(title='Rulmeca: Calculating Conveyor Power for Bulk Handling',url='https://rulmecacorp.com/bulk-handling-power-calculation-program/',use='Различие эффективной тяги, натяжения для сцепления/провисания и сил на барабан; численные коэффициенты R08 не взяты из этой страницы.'),dict(title='Rulmeca: Technical Precautions, TC101 02/24, p82',url='https://rulmecacorp.com/wp-content/uploads/2024/07/TC101_catalog_2024_pg80-90a.pdf',use='Результирующую на барабане определяют векторно; лента/минимальный диаметр по требованиям поставщика. Не выбор модели мотор-барабана.')],limitations=['Длина 10 м — расчётный сценарий прямой ветви; это не определённое межосевое расстояние. Опорные оси R04 не используются как оси барабанов.','q=30 кг/м плюс единственные15 кг — условное сочетание. 15 кг учитываются один раз в общей массе и как отдельная точечная нагрузка для провисания, не три одновременно падающие порции.','qB=5 кг/м, эквивалентная дополнительная масса60 кг, коэффициенты c/μ, сопротивление очистителя и времена разгона/торможения — допущения, не измеренные свойства и не нормативные значения.','60 кг разделены поровну между ветвями как инерционный эквивалент роликов/хвостового барабана/ленты на дугах. Инерция двигателя, редуктора и приводного барабана не включена.','Барабаны D200 и скорость0,1–0,3 м/с — примеры, не подбор по ленте/потоку. Профиль использует параллельные ветви и обхват180°.','Коэффициент сопротивления — эквивалентный параметр упрощенной модели, не коэффициент ISO/DIN и не заявленный расчёт по ним.','Минимальное натяжение вычислено заново для каждого режима: реальные винтовые натяжители не меняют натяжение автоматически. Результаты отдельных режимов нельзя считать совместимым назначением преднатяга.','Ориентиры провисания1%/2% не утверждены. Точечная15 кг размещена в центре одного пролёта; её реальное распределение по роликам неизвестно.','Отрицательная тяга означает необходимость удерживать/тормозить движение вниз в этой модели. Выбор тормоза/редуктора, время остановки и поведение при потере питания не подтверждены.','Момент заклинивания и ограничение момента неизвестны: расчёт заклинивания недоступен, термореле не трактуется как заданный механический ограничитель.','Результирующие у барабанов не являются силами на одной связи M10 среднего узла R07. Не задан путь усилий от подшипников через концевые рамы к опорам и анкерам.','Скорость выбирается по производительности и удержанию мокрых отбросов; номинальную мощность двигателя нельзя назначить по одной величине Fu*v.'])
d['fixed_mean_comparison']=dict(T_mean_target_N=mean_target,states=installed,extrema=installed_extrema,assumption='Одинаковый упругий EA и неизменная длина пути ленты: постоянное среднее натяжение, без изменения длины от провисания/температуры/релаксации. Это отдельное сравнение, не назначение винтового натяжителя.')
(B/'work/traction_r08.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8');(O/'02_Расчеты/ЛТ500_Тяга_и_натяжение_R08.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({'active':[{k:r[k] for k in ['mode','Fu_N','T_sag_carry_N','drive_resultant_N','tail_resultant_N']} for r in active],'fixed_mean':mean_target,'installed_extrema':installed_extrema},ensure_ascii=False))
