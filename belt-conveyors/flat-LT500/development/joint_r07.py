from pathlib import Path
import math,json
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер';r6=json.loads((B/'work/reinforce_r06.json').read_text(encoding='utf8'))
rho=7850.;g=9.80665;E=200000.;a=math.radians(1.5);tc=24+50*math.tan(a);capY=40-tc
V={};C={}
def body(n,v,c):V[n]=v;C[n]=c
body('CROSSBEAM',1334.7964473723105*700e-9,[0,-tc-12,350])
for side,z in [('LEFT',50),('RIGHT',650)]:
 body('LEG_'+side,540.8230016469242*(542-tc-12)*1e-9,[0,-311-tc/2-6,z]);body('PLATE_'+side,120*150*8e-9,[0,-586,z]);body('CAP_'+side,160*120*12e-9,[0,capY-6,z])
 # Integrals over the trapezoidal seat; two transverse holes are fully inside its profile.
 Aw=100*tc;wx=-(math.tan(a)*100**3/12)/Aw;wy=capY+(tc*tc+math.tan(a)**2*100**2/12)/(2*tc);holeA=math.pi*5.25**2
 sv=(Aw-2*holeA)*80e-9;sc=[(Aw*wx)/(Aw-2*holeA),(Aw*wy-2*holeA*(capY+12))/(Aw-2*holeA),z];body('SEAT_'+side,sv,sc)
 for label,x in [('MINUS',-53),('PLUS',53)]:body(f'WEB_{side}_{label}',6*80*80e-9,[x,-tc-12,z])
 ym=lambda x:40+50/math.cos(a)-x*math.tan(a)
 for direction,start,sign in [('IN',-300,-1),('OUT',6,1)]:
  length=294;rx=(start+length/2)*math.cos(a)+50*math.sin(a);ry=40-(start+length/2)*math.sin(a)+50*math.cos(a);bx=sign*35;by=ym(bx);gross=840.8230016469242*length*1e-9;hv=math.pi*10.25**2*6e-9;net=gross-hv;body(f'REF_RAIL_{side}_{direction}_SLOPE',net,[(gross*rx-hv*bx)/net,(gross*ry-hv*by)/net,z])
 holes=[(math.pi*5.25**2,-30,capY+12),(math.pi*5.25**2,30,capY+12),(math.pi*10.5**2,-35,ym(-35)),(math.pi*10.5**2+12*21,35,ym(35))];grossA=160*100;netA=grossA-sum(h[0] for h in holes);cx=-sum(h[0]*h[1] for h in holes)/netA;cy=(grossA*(capY+50)-sum(h[0]*h[2] for h in holes))/netA
 for label,dz in [('MINUS',-45),('PLUS',45)]:body(f'GUIDE_{side}_{label}',netA*6e-9,[cx,cy,z+dz])
 for typ,x,y,bd,od,id,bl,af,hh,nh,wd in [('SEAT_IN',-30,capY+12,6,10,6.5,110,10,4,5,18),('SEAT_OUT',30,capY+12,6,10,6.5,110,10,4,5,18),('MODULE_IN',-35,ym(-35),10,20,11,120,17,6,8,24),('MODULE_OUT',35,ym(35),10,20,11,120,17,6,8,24)]:
  name=side+'_'+typ;body('SLEEVE_'+name,math.pi*(od*od-id*id)/4*97e-9,[x,y,z]);body('SHAFT_'+name,math.pi*bd*bd/4*bl*1e-9,[x,y,z-50.5+bl/2]);ha=math.sqrt(3)/2*af*af;body('HEAD_'+name,ha*hh*1e-9,[x,y,z-50.5-hh/2]);body('NUT_'+name,(ha-math.pi*bd*bd/4)*nh*1e-9,[x,y,z+50.5+nh/2])
  for label,dz in [('MINUS',-49.5),('PLUS',49.5)]:body('WASHER_'+name+'_'+label,math.pi*(wd*wd-id*id)/4*2e-9,[x,y,z+dz])
assert len(V)==69
support_mass=sum(v for n,v in V.items() if not n.startswith('REF_RAIL'))*rho
addedmass=support_mass-r6['variants'][1]['stand_mass_kg'];P=r6['load_screen_N']+max(0,addedmass)*g;H=P*math.sin(math.radians(2))
cases=[]
for typ,bd,pitch,As,od,id,thickness in [('MODULE',10,1.5,58.,20,11,3),('SEAT',6,1,20.1,10,6.5,80)]:
 I=math.pi*(od**4-id**4)/64;Ib=math.pi*bd**4/64
 for F in [H,500.,1000.,2000.,5000.]:
  cases.append(dict(type=typ,F_N=F,bolt_d_mm=bd,thread_area_mm2=As,sleeve_OD_mm=od,sleeve_ID_mm=id,span_mm=90,sleeve_sigma_MPa=F*90/4*(od/2)/I,sleeve_delta_mm=F*90**3/(48*E*I),bolt_thread_double_shear_MPa=F/(2*As),bare_bolt_bending_screen_MPa=F*90/4*(bd/2)/Ib,guide_bearing_MPa=F/(2*6*od),rail_or_seat_bearing_MPa=F/(2*3*od) if typ=='MODULE' else F/(80*od)))
slot=[]
for deg in [1,1.5,2]:slot.append(dict(angle_deg=deg,travel_one_side_mm=6,normal_clearance_mm=.5,vertical_shift_mm=6*math.tan(math.radians(deg)),remaining_vertical_clearance_mm=.5-6*math.tan(math.radians(deg))))
cap=dict(P_N=P,span_mm=112,b_mm=38,t_mm=12,sigma_MPa=6*(P*112/4)/(38*12**2),delta_mm=P*112**3/(48*E*(38*12**3/12)))
d=dict(revision='R07',scope='Поперечные втулки/болты для крепления седел и независимых концов модулей; один круглый фиксатор, один продольный паз',constants=dict(E_MPa=E,rho_kg_m3=rho,g=g),angle_deg=1.5,seat=dict(length_mm=100,width_mm=80,t_min_mm=24,t_centre_mm=tc,transverse_hole_d_mm=10.5,pin_axis_from_bottom_mm=12,min_bottom_ligament_mm=6.75),cap_mm=[160,120,12],guide_mm=[160,100,6],guide_inside_width_mm=84,guide_outside_width_mm=96,sleeve_length_mm=97,washer_face_gap_to_guide_mm=.5,module_hole_mm=21,module_slot_mm=[33,21],rail_hole_mm=20.5,module_pin_x_mm=[-35,35],seat_pin_x_mm=[-30,30],end_gap_along_rail_mm=12,leg_mid_mm=542-tc-12,support_with_fasteners_mass_kg=support_mass,with_stubs_mass_kg=sum(V.values())*rho,added_mass_vs_R06_kg=addedmass,load_screen_N=P,gravity_component_2deg_N=H,capacity_for_actual_belt_forces=None,cases=cases,slot_geometry=slot,cap_recheck=cap,expected_bodies={n:dict(volume_m3=V[n],centroid_mm=C[n]) for n in V},sources=dict(thread_area='https://media.bossard.com/de-de/-/media/bossard-group/website/documents/technical-resources/de/f-041-de.pdf'),limitations=['Все продольные силы ленты/пуска/заклинивания неизвестны; несущая способность соединения не утверждена.','Швы направляющих с пластиной, пластины с щеками и щек с трубой не подтверждены.','Один модуль в данном узле фиксирован, второй может перемещаться ±6 мм вдоль паза; у каждого полного модуля необходима своя единственная фиксированная опора. Полная схема фиксированных/подвижных опор пока не выпущена.','Передача момента между модулями не используется в расчёте R04; контактные площадки и штифты создают реальную местную жесткость, которую требуется проверить.','Шайбы опираются на торцы втулок, не на направляющие: номинальный зазор 0,5 мм сохраняет перемещение в пазу без зажима. Допуски/покрытие и усилие затяжки ещё не назначены.','В CAD резьбы заменены цилиндрами, головы/гайки имеют условный шестигранник. Это проверка расположения, не библиотечные детали поставщика.','Седло утолщено до 24 мм для размещения отверстий и геометрических перемычек; это не нормативное обоснование минимальной толщины.','Измененные сечения отверстий продольной трубы, контакт втулок, усталость, коррозия и силы от сборочных зазоров не проверены.','Условный прогиб пластины пересчитан с новой массой. Допускаемые напряжения и частичные коэффициенты не назначены.'])
(B/'work/joint_r07.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8');(O/'02_Расчеты/ЛТ500_Крепление_седел_и_стык_R07.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:d[k] for k in ['support_with_fasteners_mass_kg','added_mass_vs_R06_kg','load_screen_N','gravity_component_2deg_N','cap_recheck','leg_mid_mm']},ensure_ascii=False))
