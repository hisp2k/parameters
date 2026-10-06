from pathlib import Path
import json,math
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер';old=json.loads((B/'work/support_r04.json').read_text(encoding='utf8'))
E=200000.;rho=7850.;g=9.80665;P=old['chosen_crossbeam']['load_mid_N'];beam=old['chosen_crossbeam']['section'];leg=old['leg'];rail=old['rail']
theta=1.5;angle=math.radians(theta);seatL=100.;seatB=60.;flatRail=rail['b_mm']-2*rail['ro_mm'];flatBeam=beam['b_mm']-2*beam['ro_mm']
assert flatRail==38 and flatBeam==84
comparisons=[]
for t in [6.,8.,10.]:
 tc=t+seatL/2*math.tan(angle);vs=seatL*seatB*tc*1e-9;ps=P+2*vs*rho*g
 # Separate conservative seat strip: central point on edge-supported span of width equal to top straight beam face.
 Is=flatRail*t**3/12;M=ps*flatBeam/4;delta=ps*flatBeam**3/(48*E*Is)
 comparisons.append(dict(t_min_mm=t,t_centre_mm=tc,t_max_mm=t+seatL*math.tan(angle),volume_one_m3=vs,load_one_seat_upper_N=ps,seat_strip_I_mm4=Is,seat_strip_sigma_MPa=6*M/(flatRail*t*t),seat_strip_delta_mm=delta))
chosen=comparisons[-1];tmin=chosen['t_min_mm'];target=.05
variants=[]
for th in [1.,1.5,2.]:
 a=math.radians(th);tc=tmin+50*math.tan(a);depth=.542-tc/1000;vseat=100*60*tc*1e-9
 vstand=beam['A_mm2']*.7e-6+2*leg['A_mm2']*depth*1e-6+2*120*150*8e-9+2*vseat
 refs=4*rail['A_mm2']*.3e-6;stations=[]
 for x in [200,2600,5000,7400,9800]:
  belt=800+(5000-x)*math.tan(a);baseCrossTop=belt-170-tc;lh=baseCrossTop-80-8
  stations.append(dict(x_mm=x,belt_mm=belt,rail_seating_plane_y_mm=belt-170,crossbeam_top_mm=baseCrossTop,leg_length_mm=lh))
 # Wedge centroid from direct polynomial area integration: bottom horizontal, thickness t(x)=tc-x*tan(a).
 xbar=-math.tan(a)*100**2/(12*tc);yb=-tc+(tc/2+math.tan(a)**2*100**2/(24*tc))
 variants.append(dict(angle_deg=th,t_centre_mm=tc,t_max_mm=tmin+100*math.tan(a),leg_depth_m=depth,stand_volume_m3=vstand,stand_mass_kg=vstand*rho,with_reference_rails_volume_m3=vstand+refs,with_reference_rails_mass_kg=(vstand+refs)*rho,wedge_centroid_relative_seat_plane_mm=[xbar,yb],stations=stations))
v=variants[1];ps=chosen['load_one_seat_upper_N'];tw=4.;clear=100-2*tw;loaded=flatBeam
# Local top-wall screen: simply supported unit-width strip, centred uniform patch over 84 mm, effective transverse spreading width 60 mm.
pb=ps/60;moment=pb*(2*clear-loaded)/8;sigWall=6*moment/tw**2
deltaWall=pb*(8*clear**3-4*clear*loaded**2+loaded**3)/(384*E*(tw**3/12))
wall_sens=[]
for spread in [38,60]:
 for span in [84,92]:
  patch=min(flatBeam,span);f=ps/spread;M=f*(2*span-patch)/8
  wall_sens.append(dict(spreading_width_mm=spread,span_mm=span,sigma_MPa=6*M/tw**2,delta_mm=f*(8*span**3-4*span*patch**2+patch**3)/(384*E*(tw**3/12))))
# Numerical independent virtual-work integration for the chosen strip case (EI removed).
N=200000;dx=clear/N;num=0;qa=pb/loaded;left=(clear-loaded)/2
for j in range(N):
 x=(j+.5)*dx;active=max(0,min(x-left,loaded));M=pb/2*x-qa*active**2/2
 if x>left+loaded:M=pb/2*x-pb*(x-clear/2)
 m=min(x,clear-x)/2;num+=M*m*dx
numeric_delta=num/(E*(tw**3/12));assert abs(numeric_delta-deltaWall)<1e-8
contacts={'rail_flat_width_mm':flatRail,'seat_bottom_supported_straight_width_mm':flatBeam,'seat_bottom_area_mm2':flatBeam*seatB,'rail_half_seat_surface_area_mm2':50*flatRail/math.cos(angle),'mean_pressure_full_load_on_half_contact_MPa':ps*math.cos(angle)/(50*flatRail/math.cos(angle)),'scope':'Площадь номинального контакта в идеальной геометрии; не фактическое распределение давления и не расчёт контакта в Simulation.'}
d=dict(revision='R05',scope='Геометрия наклонного седла, местная жёсткость и узел стыка; предварительный расчёт',constants=dict(E_MPa_assumed=E,rho_kg_m3=rho,g=g),load_from_R04_N=P,seat=dict(length_mm=seatL,width_mm=seatB,t_min_mm=tmin,theta_deg=theta,deflection_target_mm_proposed=target,selected=chosen),seat_candidates=comparisons,variants=variants,contacts=contacts,top_wall=dict(clear_span_mm=clear,loaded_width_mm=loaded,effective_transverse_width_mm=60,t_mm=tw,sigma_MPa=sigWall,delta_mm=deltaWall,scope='Одномерный упругий ориентир: опирание полосы по краям, равномерная центральная площадка. Реальный контакт, углы трубы и распределение по ширине не решены.'),top_wall_sensitivity=wall_sens,restraint=dict(sliding_component_N_at_2deg=ps*math.sin(math.radians(2)),belt_axial_force_N=None,friction_assumed=False,positive_restraint_required=True),blank_proposal=dict(size_mm=[104,64,16],minimum_top_allowance_at_2deg_mm=16-variants[2]['t_max_mm'],scope='Кандидат заготовки для обсуждения фрезеровки; не заказ и не выпущенный маршрут.'),checks=dict(independent_top_wall_virtual_work_delta_mm=numeric_delta,closed_form_matches_virtual_work=True,manufacturing_approved=False,simulation_performed=False),assumptions=['Седла сплошные, верх наклонён вдоль транспортёра, нижняя поверхность горизонтальна. В CAD отсутствуют фиксаторы седел и крепления балок.','Минимальная толщина 10 мм выбрана по предлагаемому пределу прогиба отдельного седла 0,05 мм, не по утверждённому нормативу. Сравнены 6/8/10 мм.','Условная нагрузка 1418,07 Н из R04 плюс вес двух седел целиком направлена на одно седло; совместность q и локальных 15 кг неизвестна.','Радиусы трубы ограничивают плоскую опорную поверхность: нижняя плоскость рельса 38 мм вместо наружных 50 мм, верх трубы 84 мм вместо наружных 100 мм.','На стыке контакт каждой половины седла имеет номинальную длину по горизонтали 50 мм. Торцы рельсов в CAD лежат в одной плоскости без заданного эксплуатационного зазора.','Предложенные высоты исправлены на толщину седла; 170 мм между рабочей поверхностью ленты и плоскостью опирания рельса остаётся допущением.','Прочность верхней стенки поперечины не подтверждена. Одномерный расчёт показан как ориентир для выбора следующей проверки, а не как заменитель контактов/Simulation.','Полная рама, барабаны, привод, натяжение, связи, швы, болты, анкеры и бетон пока не рассчитаны.','Сборочный узел представлен многотельной деталью: семь тел опоры и четыре коротких справочных участка рельса. Они не являются деталями полного транспортёра.'])
(B/'work/seat_r05.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8');(O/'02_Расчеты/ЛТ500_Наклонное_опирание_R05.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'candidates':comparisons,'stand_main':v,'wall':d['top_wall'],'restraint':d['restraint']},ensure_ascii=False))
