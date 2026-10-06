from pathlib import Path
import json,math
import numpy as np
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер';old=json.loads((B/'work/seat_r05.json').read_text(encoding='utf8'));r04=json.loads((B/'work/support_r04.json').read_text(encoding='utf8'))
E=200000.;rho=7850.;g=9.80665;Pbase=old['load_from_R04_N'];webV=6*80*80e-9;beamA=r04['chosen_crossbeam']['section']['A_mm2'];legA=r04['leg']['A_mm2'];railA=r04['rail']['A_mm2'];tc=old['variants'][1]['t_centre_mm'];seatV=100*60*tc*1e-9
cases=[]
for t in [6.,8.,10.,12.]:
 capV=120*80*t*1e-9;added_weight=(2*seatV+2*capV+4*webV)*rho*g;P=Pbase+added_weight
 for span in [100.,106.,112.]:
  for width in [38.,60.,80.]:
   I=width*t**3/12;M=P*span/4
   cases.append(dict(t_mm=t,span_mm=span,effective_width_mm=width,P_N=P,M_Nmm=M,sigma_MPa=6*M/(width*t*t),delta_mm=P*span**3/(48*E*I)))
sel=next(x for x in cases if x['t_mm']==12 and x['span_mm']==106 and x['effective_width_mm']==38);bound=next(x for x in cases if x['t_mm']==12 and x['span_mm']==112 and x['effective_width_mm']==38);P=sel['P_N'];capV=120*80*12e-9
assert bound['delta_mm']<=.05 and next(x for x in cases if x['t_mm']==10 and x['span_mm']==112 and x['effective_width_mm']==38)['delta_mm']>.05
# Independent Euler-Bernoulli two-element FE solve in mm, simply supported ends, central load at a node.
def fem(span,t,width,force):
 l=span/2;I=width*t**3/12;k=E*I/l**3*np.array([[12,6*l,-12,6*l],[6*l,4*l*l,-6*l,2*l*l],[-12,-6*l,12,-6*l],[6*l,2*l*l,-6*l,4*l*l]])
 K=np.zeros((6,6));f=np.zeros(6);f[2]=force
 for j in [0,1]:
  idx=[2*j,2*j+1,2*j+2,2*j+3];K[np.ix_(idx,idx)]+=k
 free=[1,2,3,5];u=np.zeros(6);u[free]=np.linalg.solve(K[np.ix_(free,free)],f[free]);R=K@u-f
 return u[2],[-R[0],-R[4]]
fdelta,reactions=fem(sel['span_mm'],12,38,P);assert abs(fdelta-sel['delta_mm'])<1e-12;assert abs(sum(reactions)-P)<1e-7
# Moving point within the 100-mm seat: both reactions nonnegative; individual side web is screened at ALL P, not P/2.
points=[]
for x in np.linspace(-50,50,1001):
 a=x+53;Rl=P*(106-a)/106;Rr=P*a/106;M=P*a*(106-a)/106
 assert Rl>=0 and Rr>=0 and abs(Rl+Rr-P)<1e-8;points.append((Rl,Rr,M))
assert abs(max(x[2] for x in points)-P*106/4)<1e-8
weld=[]
for k in [3.,4.]:
 for net in [44.,54.]:
  throat=k/math.sqrt(2);area=2*throat*net;Igroup=2*throat*net**3/12;moment=P*3
  tau=P/area;sigma=moment*net/2/Igroup
  weld.append(dict(leg_mm=k,throat_mm=throat,net_length_each_mm=net,force_one_web_N=P,eccentricity_mm=3,tau_MPa=tau,sigma_nominal_MPa=sigma,equivalent_nominal_MPa=math.sqrt(sigma*sigma+3*tau*tau)))
selected_weld=next(x for x in weld if x['leg_mm']==3 and x['net_length_each_mm']==54)
variants=[]
for prior in old['variants']:
 a=math.radians(prior['angle_deg']);ct=prior['t_centre_mm'];legs=prior['leg_depth_m']-.012;v=beamA*.7e-6+2*legA*legs*1e-6+2*120*150*8e-9+2*100*60*ct*1e-9+2*capV+4*webV;rows=[]
 for r in prior['stations']:
  rows.append(dict(x_mm=r['x_mm'],belt_mm=r['belt_mm'],rail_seating_plane_y_mm=r['rail_seating_plane_y_mm'],cap_top_mm=r['crossbeam_top_mm'],crossbeam_top_mm=r['crossbeam_top_mm']-12,leg_length_mm=r['leg_length_mm']-12))
 variants.append(dict(angle_deg=prior['angle_deg'],t_centre_seat_mm=ct,leg_depth_m=legs,stand_volume_m3=v,stand_mass_kg=v*rho,with_reference_rails_volume_m3=v+4*railA*.3e-6,with_reference_rails_mass_kg=(v+4*railA*.3e-6)*rho,stations=rows))
seatcheck={'span_mm':100,'effective_width_mm':38,'t_min_mm':10,'sigma_MPa':6*(P*100/4)/(38*10**2),'delta_mm':P*100**3/(48*E*(38*10**3/12))}
# Comparison alternative: replacing the full transverse tube, own mass and changed flat contact kept explicit.
def rounded(b,h,r):
 c=h/2-r;return b*h-(4-math.pi)*r*r,b*h**3/12-4*(c*c*(1-math.pi/4)*r*r+c*r**3/3+r**4*(1/3-math.pi/16))
alternatives=[]
for tw in [4,6,8]:
 area=rounded(100,80,2*tw)[0]-rounded(100-2*tw,80-2*tw,tw)[0];span=100-2*tw;loaded=100-4*tw;force=old['seat']['selected']['load_one_seat_upper_N'];w=force/38
 alternatives.append(dict(option=f'Цельная труба 80x100x{tw}',mass_kg_m=area*rho*1e-6,flat_top_mm=loaded,screen_sigma_MPa=6*w*(2*span-loaded)/8/tw**2,screen_delta_mm=w*(8*span**3-4*span*loaded**2+loaded**3)/(384*E*(tw**3/12))))
d=dict(revision='R06',scope='Наружный колпак усиления опорной зоны: пластина и две вертикальные щеки у каждого седла',constants=dict(E_MPa_assumed=E,rho_kg_m3=rho,g=g),load_from_R04_N=Pbase,load_screen_N=P,geometry=dict(cap_mm=[120,80,12],web_mm=[6,80,80],caps_quantity=2,webs_quantity=4,web_centres_x_mm=[-53,53],web_inner_faces_x_mm=[-50,50],seat_mm=[100,60],seat_t_min_mm=10,seat_angle_deg=1.5,crossbeam_original_mm=[80,100,4],straight_side_height_mm=64,weld_net_length_proposed_mm=54,weld_leg_candidate_mm=3),cap_cases=cases,cap_selected=sel,cap_conservative_geometry=bound,seat_recheck=seatcheck,alternative_full_tubes=alternatives,weld_cases=weld,weld_selected=selected_weld,wall_connection_nominal_shear_MPa=P/(2*54*4),variants=variants,added_mass_main_kg=variants[1]['stand_mass_kg']-old['variants'][1]['stand_mass_kg'],moving_load=dict(samples=1001,max_one_web_reaction_N=max(max(x[:2]) for x in points),max_bending_Nmm=max(x[2] for x in points)),restraint=dict(sliding_component_N_at_2deg=P*math.sin(math.radians(2)),belt_axial_force_N=None,seat_fixation_designed=False),checks=dict(independent_EB_FE_centre_deflection_mm=float(fdelta),FE_end_reactions_N=reactions,FE_vs_formula=True,moving_load_equilibrium=True,manufacturing_approved=False,simulation_performed=False),assumptions=['Нагрузка условная: огибающая R04 плюс вес обоих седел, обоих колпаков и четырёх щёк целиком на одну площадку. Совместность q и 15 кг неизвестна.','Пластина колпака рассчитана как отдельная шарнирно опёртая полоса на наружных щеках. Работа верхней стенки трубы и совместная жёсткость слоёв не включены. Это альтернативный путь вертикальной нагрузки.','Предлагаемый критерий прогиба отдельной пластины 0,05 мм — проектный ориентир, не норматив. Минимальная эффективная ширина 38 мм равна плоской ширине рельса.','Сосредоточенная сила по центру даёт верхнюю оценку изгиба пластины для рассматриваемых положений внутри седла 100 мм. Для одной щеки и её двух швов принята вся P, не P/2.','54 мм — предложенная рабочая длина каждого вертикального шва на прямой боковой поверхности трубы 64 мм, с отступом 5 мм от её концов. Катет 3 мм — расчётный кандидат, WPS и нормативный минимальный размер не утверждены.','Эквивалентные напряжения швов — только номинальная упругая модель группы с a=k/√2, эксцентриситет 3 мм. Нормативная проверка шва, прочность материала/зоны термического влияния и усталость не выполнены.','Номинальный сдвиг боковой стенки у швов не является проверкой местной концентрации напряжений, вмятия и прочности оболочки трубы.','Седло и колпак в CAD ещё не имеют механического крепления друг к другу и к рельсам. Сварные валики отсутствуют; нагрузочный путь через щеки требует реальных рассчитанных соединений.','В CAD сохраняется условная плоскость опирания рельса, поэтому стойки короче R05 ещё на 12 мм. Интерфейс лента–рельс 170 мм и оси опор остаются допущениями.','13 тел опоры плюс 4 справочных отрезка рельса; это многотельная деталь, не сборка всего транспортёра.'],source_weld_geometry='https://www.twi-global.com/technical-knowledge/job-knowledge/design-part-1-090')
(B/'work/reinforce_r06.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8');(O/'02_Расчеты/ЛТ500_Усиление_опорной_зоны_R06.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'cap_main':sel,'cap_bound':bound,'seat':seatcheck,'weld':selected_weld,'mass':variants[1]['stand_mass_kg'],'added_mass':d['added_mass_main_kg'],'alternatives':alternatives},ensure_ascii=False))
