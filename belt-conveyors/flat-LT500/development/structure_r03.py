from pathlib import Path
import json,math
b=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');o=b/'outputs/Ленточный_транспортер'
def rounded(b,h,r):
 area=b*h-(4-math.pi)*r*r;yc=h/2-r
 inertia=b*h**3/12-4*(yc*yc*(1-math.pi/4)*r*r+yc*r**3/3+r**4*(1/3-math.pi/16))
 return area,inertia
def section(h,b,t,r):
 ao,io=rounded(b,h,r);ai,ii=rounded(b-2*t,h-2*t,r-t)
 a=ao-ai;i=io-ii;_,jo=rounded(h,b,r);_,ji=rounded(h-2*t,b-2*t,r-t)
 return {'h_mm':h,'b_mm':b,'t_mm':t,'r_out_mm':r,'r_in_mm':r-t,'area_mm2':a,'I_vertical_mm4':i,'I_horizontal_mm4':jo-ji,'W_vertical_mm3':i/(h/2),'mass_kg_m':a*7850e-6}
def response(p,L,beta,P=15*9.80665):
 w=(30*beta+p['mass_kg_m'])*9.80665;own=p['mass_kg_m']*9.80665
 mU=w*L*L/8;mP=P*L/4;kU=5*w*L**4/384;kP=P*L**3/48
 dU=kU*1e9/(200000*p['I_vertical_mm4']);dP=kP*1e9/(200000*p['I_vertical_mm4'])
 dmown=5*own*L**4/384*1e9/(200000*p['I_vertical_mm4'])
 max_extra=max(0,(2-(dU+dP))*200000*p['I_vertical_mm4']/1e9*384/(5*L**4)/9.80665)
 return {'span_m':L,'beta':beta,'w_N_m':w,'M_uniform_Nm':mU,'M_local_Nm':mP,'M_conditional_sum_Nm':mU+mP,'sigma_uniform_MPa':mU*1000/p['W_vertical_mm3'],'sigma_local_plus_own_MPa':(own*L*L/8+mP)*1000/p['W_vertical_mm3'],'sigma_conditional_sum_MPa':(mU+mP)*1000/p['W_vertical_mm3'],'deflection_uniform_mm':dU,'deflection_local_plus_own_mm':dP+dmown,'deflection_conditional_sum_mm':dU+dP,'stiffness_budget_extra_kg_m':max_extra,'end_reaction_conditional_N':w*L/2+P/2}
profiles=[];rows=[]
for h,bw,t in [(80,40,3),(100,50,3),(120,60,4)]:
 p=section(h,bw,t,2*t);p['name']=f'{h}x{bw}x{t}';profiles.append(p)
 for L in [2,2.5,10/3,5]:
  for beta in [.5,1]:rows.append({'profile':p['name'],**response(p,L,beta)})
selected=profiles[1];sens=[]
for f in [1,.9]:
 for r_factor in [1.6,2,3]:
  t=3*f;p=section(100,50,t,r_factor*t);sens.append({'thickness_factor':f,'radius_factor':r_factor,'section':p,'response':response(p,2.5,1)})
# Independent area/inertia quadrature, not reuse of closed-form expressions.
def width(y,bw,h,r):
 dy=abs(y)-(h/2-r)
 return bw if dy<=0 else bw-2*r+2*math.sqrt(max(0,r*r-dy*dy))
N=100000;dy=100/N;numA=0;numI=0
for n in range(N):
 y=-50+(n+.5)*dy;w=width(y,50,100,6)
 if abs(y)<47:w-=width(y,44,94,3)
 numA+=w*dy;numI+=w*y*y*dy
assert abs(numA-selected['area_mm2'])/selected['area_mm2']<1e-6
assert abs(numI-selected['I_vertical_mm4'])/selected['I_vertical_mm4']<1e-6
assert abs(response(selected,2.5,1)['M_uniform_Nm']-(30+selected['mass_kg_m'])*9.80665*2.5**2/8)<1e-9
data={'revision':'R03','scope':'Эластический вертикальный изгиб отдельных балок; не полный расчёт рамы','constants':{'g':9.80665,'E_MPa_assumed':200000,'rho_steel_kg_m3':7850,'local_peak_mass_kg':15,'material_line_mass_kg_m':30,'deflection_target_mm_proposed':2},'profiles':profiles,'comparisons':rows,'sensitivity':sens,'selected_for_prototype':selected,'selected_span_m':2.5,'support_reference_coordinates_mm':[0,2500,5000,7500,10000],'module_length_mm':5000,'rail_centres_distance_mm_proposed':600,'assumptions':['Сечения вычислены геометрически, не получены из паспорта купленного профиля. Номинальный наружный радиус 2t, внутренний r-t.','E=200000 МПа принят для сравнения; плотность 7850 кг/м³. Свойства конкретного Ст3 не подтверждены сертификатом.','2 мм — предлагаемый критерий вертикального прогиба для концепции, не утверждённый допуск.','Балка шарнирно опёрта. Собственный вес включён во все случаи; локальные 15 кг целиком на одну балку в середине пролёта.','Сумма q+15 кг — условная огибающая для сравнения; не подтверждает совместность и может дважды учитывать материал.','Деформации стыков, роликов, поперечин, стоек, основания и собственные массы остальных узлов не включены.','Остаточная масса для пуска и усилия натяжения не определены; поэтому полная прочность рамы не подтверждена.','Толщина 0,9t и радиусы 1,6t…3t — исследование чувствительности, не заявленные допускаемые отклонения ГОСТ.'],'checks':{'independent_quadrature_area_mm2':numA,'independent_quadrature_I_mm4':numI,'relative_error_max':max(abs(numA-selected['area_mm2'])/selected['area_mm2'],abs(numI-selected['I_vertical_mm4'])/selected['I_vertical_mm4']),'passed':True},'source':'https://tubulareurope.arcelormittal.com/sites/default/files/2023-12/structural_hollow_section_arcelormittal.pdf — табличные физические свойства, стр. 3; не сертификат выбранного Ст3, не действующая экологическая декларация (срок до 2025).'}
(b/'work/structure_r03.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');(o/'02_Расчеты/ЛТ500_Вертикальный_изгиб_рамы_R03.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'candidate':selected,'case':response(selected,2.5,1),'sensitivity_max_deflection':max(x['response']['deflection_conditional_sum_mm'] for x in sens),'quad_passed':True},ensure_ascii=False))
