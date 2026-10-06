from pathlib import Path
import json,math
import numpy as np
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер'
def rounded(b,h,r):
 a=b*h-(4-math.pi)*r*r;c=h/2-r
 i=b*h**3/12-4*(c*c*(1-math.pi/4)*r*r+c*r**3/3+r**4*(1/3-math.pi/16))
 return a,i
def section(h,b,t):
 r=2*t;a,i=rounded(b,h,r);ai,ii=rounded(b-2*t,h-2*t,r-t)
 _,j=rounded(h,b,r);_,ji=rounded(h-2*t,b-2*t,r-t)
 return dict(h_mm=h,b_mm=b,t_mm=t,ro_mm=r,ri_mm=r-t,A_mm2=a-ai,I_mm4=i-ii,I_weak_mm4=min(i-ii,j-ji),W_mm3=(i-ii)/(h/2),kg_m=(a-ai)*7850e-6)
g=9.80665;E=200000.;L=2.4;rail=section(100,50,3);leg=section(50,50,3)
# Independent two-element Euler-Bernoulli stiffness solution, all vertical supports fixed, rotations free.
k=np.array([[12,6*L,-12,6*L],[6*L,4*L*L,-6*L,2*L*L],[-12,-6*L,12,-6*L],[6*L,2*L*L,-6*L,4*L*L]])/L**3
K=np.zeros((6,6));free=[1,3,5]
for el in range(2):
 idx=np.array([2*el,2*el+1,2*el+2,2*el+3]);K[np.ix_(idx,idx)]+=k
def solve(w=0.,point=None):
 f=np.zeros(6)
 for el in range(2):
  idx=np.array([2*el,2*el+1,2*el+2,2*el+3]);f[idx]+=w*np.array([L/2,L**2/12,L/2,-L**2/12])
 if point:
  x,p=point;el=min(1,int(x/L));a=(x-el*L)/L
  n=np.array([1-3*a*a+2*a**3,L*(a-2*a*a+a**3),3*a*a-2*a**3,L*(-a*a+a**3)])
  f[np.array([2*el,2*el+1,2*el+2,2*el+3])]+=p*n
 u=np.zeros(6);u[free]=np.linalg.solve(K[np.ix_(free,free)],f[free]);r=(K@u-f)[[0,2,4]]
 return -r # both distributed and point loads positive downward; returned reactions upward
# positive equivalent nodal uniform gives negative support forces, minus sign restores upward reactions
uniform=solve(1.);assert np.allclose(uniform,L*np.array([.375,1.25,.375]))
point_records=[]
for x in np.linspace(0,2*L,1001):
 r=solve(point=(float(x),15*g));assert abs(sum(r)-15*g)<1e-8;assert abs(r@[0,L,2*L]-15*g*x)<1e-7
 assert np.max(np.abs(solve(1.,(float(x),15*g))-uniform-r))<1e-8
 point_records.append({'x_m':float(x),'R_N':r.tolist()})
local_bounds=[{'support':i,'max_N':max(x['R_N'][i] for x in point_records),'min_N':min(x['R_N'][i] for x in point_records)} for i in range(3)]
assert abs(sum(uniform)-2*L)<1e-9
assert abs(uniform@[0,L,2*L]-2*L*L)<1e-9
coords=[200,2600,5000,7400,9800];trib=[.9,3.,1.8,3.,.9];terminal=[.2,0,0,0,.2]
stations=[]
for i,x in enumerate(coords):
 r_rail=2*rail['kg_m']*g*trib[i];r_q=30*g*(trib[i]+terminal[i]);r_p=15*g
 stations.append(dict(x_mm=x,rail_tributary_m=trib[i],material_tributary_m=trib[i]+terminal[i],R_rails_N=r_rail,R_material_N=r_q,R_local_envelope_N=r_p,R_uniform_plus_rails_N=r_rail+r_q,R_local_plus_rails_N=r_rail+r_p,R_conditional_N=r_rail+r_q+r_p))
assert abs(sum(x['R_material_N'] for x in stations)-300*g)<1e-7
assert abs(sum(x['R_rails_N'] for x in stations)-9.6*2*rail['kg_m']*g)<1e-7
P=max(x['R_conditional_N'] for x in stations);cross=[]
for h,b,t in [(60,40,3),(80,40,3),(80,100,4)]:
 s=section(h,b,t);w=s['kg_m']*g;l=.6
 # upper magnitude: place 50 mm end overhang weights as loads at midspan (conservative positive bending/deflection)
 pend=w*.1;M=(P+pend)*l/4+w*l*l/8;delta=((P+pend)*l**3/48+5*w*l**4/384)*1e9/(E*s['I_mm4'])
 cross.append({'name':f'{h}x{b}x{t}','section':s,'load_mid_N':P,'M_upper_Nm':M,'sigma_MPa':M*1000/s['W_mm3'],'delta_mm':delta,'land_each_module_mm':b/2,'half_rail_contact_area_mm2':50*b/2})
chosen=cross[-1];hleg=542.;maxleg=hleg+4800*math.tan(math.radians(2));legload=P+chosen['section']['kg_m']*.7*g+leg['kg_m']*maxleg/1000*g
euler=math.pi**2*E*leg['I_weak_mm4']/(2*maxleg)**2
plateA=150*120;plateV=150*120*8*1e-9;volume=(chosen['section']['A_mm2']*.7+leg['A_mm2']*.542*2)*1e-6+plateV*2
heights=[]
for angle in [1,1.5,2]:
 heights.append({'angle_deg':angle,'stations':[{'x_mm':x,'belt_mm':800+(5000-x)*math.tan(math.radians(angle)),'stand_top_mm':630+(5000-x)*math.tan(math.radians(angle)),'leg_mm':542+(5000-x)*math.tan(math.radians(angle))} for x in coords]})
d={'revision':'R04','scope':'Вертикальные реакции и отдельная поперечная опора; не расчёт полной прочности транспортёра','constants':{'g':g,'E_MPa_assumed':E,'rho_kg_m3':7850,'q_kg_m':30,'local_mass_kg':15},'rail':rail,'continuous_uniform_reaction_coefficients':[.375,1.25,.375],'span_m':L,'moving_local_reaction_bounds':local_bounds,'support_stations':stations,'crossbeam_candidates':cross,'chosen_crossbeam':chosen,'leg':leg,'leg_checks':{'height_mid_mm':hleg,'height_max_2deg_mm':maxleg,'load_entire_frame_on_one_leg_N':legload,'compression_MPa':legload/leg['A_mm2'],'axial_shortening_mm':legload*maxleg/(E*leg['A_mm2']),'Euler_K2_N':euler,'Euler_ratio_Ncr_N':euler/legload,'Euler_scope':'Идеальная прямая отдельная стойка, K=2. Не проверка устойчивости портала, нормы или допускаемая нагрузка.'},'height_scenarios':heights,'prototype':{'bodies':5,'crossbeam_length_mm':700,'leg_length_mm':542,'leg_centres_mm':600,'plate_mm':[120,150,8],'top_above_plate_bottom_mm':630,'volume_m3':volume,'mass_kg':volume*7850,'fixed_geometry':True},'plate_mean_compression_MPa':(legload+plateV*7850*g)/plateA,'assumptions':['Оси крайних опор отнесены на 200 мм внутрь габарита; это вариант компоновки, не утверждённые монтажные координаты.','Две балки каждого модуля непрерывны над промежуточной опорой; стык у x=5000 расчётно шарнирный, передачи момента через стык пока не задано.','Реакции 3/8, 5/4, 3/8 получены для двух равных пролётов и равномерной нагрузки. Для локальных 15 кг рассчитана отдельная огибающая перемещения.','По 0,2 м концевого материала условно переданы на крайнюю опору; геометрия барабанных участков и массы их узлов не определены.','Трубы продольных балок R03 длиной 5000 остаются прототипом. При принятии этих осей геометрическую длину несущего каркаса предстоит уточнить около 9600 мм.','Сумма q и 15 кг условная: совместность и отсутствие двойного учёта неизвестны. 15 кг учтены в огибающей каждой опоры, но не одновременно на пяти опорах.','Вся вертикальная огибающая рамы поставлена в середину верхней балки для сравнения сечений; фактическая загрузка приходит через места опирания продольных балок.','Стойка проверена на осевую упругую деформацию и идеальную нагрузку Эйлера; горизонтальные усилия, несовершенства, связи, сварка и общая устойчивость ещё открыты.','Расстояние 170 мм от рабочей поверхности ленты до верха опоры принято для геометрического прототипа, не подтверждено роликами.','Подкладные плиты без отверстий являются геометрическими заготовками. Контакт с бетоном, изгиб плиты, анкеры и швы не рассчитаны.'],'checks':{'uniform_FE_vs_closed_form':True,'moving_load_samples':1001,'point_vertical_and_moment_equilibrium':True,'total_material_300kg_and_rail_mass_balance':True,'strength_approved':False,'simulation_performed':False}}
d['inclined_interface']={'crossbeam_longitudinal_width_mm':100,'height_difference_1p5deg_mm':100*math.tan(math.radians(1.5)),'height_difference_2deg_mm':100*math.tan(math.radians(2)),'resolved_in_CAD':False,'requirement':'Согласовать наклонную поверхность опирания: наклон верхней балки с соответствующим торцом стоек либо рассчитанная седловая деталь. Номинальные площадки 50 мм не подтверждают полный контакт наклонной балки с горизонтальной опорой.'}
d['checks']['uniform_plus_point_FE_superposition']=True
d['assumptions'].append('CAD верхней балки горизонтальный. Приведённые высоты номинальные по осям; поправки на наклонное опирание не выпущены. При 2° перепад на ширине 100 мм равен 3,49 мм; требуются согласованные опорные поверхности.')
(B/'work/support_r04.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8');(O/'02_Расчеты/ЛТ500_Опоры_вертикальные_нагрузки_R04.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'P':P,'crossbeam':chosen,'leg':d['leg_checks'],'prototype':d['prototype'],'local_bounds':local_bounds},ensure_ascii=False))
