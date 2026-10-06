from pathlib import Path
import json,math
import numpy as np
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер'
g=9.80665;rho=7850;E=200000;alpha=math.radians(1.5)
def clipped(R,a):return 2*(a*math.sqrt(R*R-a*a)+R*R*math.asin(a/R))
def ring(od,id,L):return math.pi*(od*od-id*id)/4*L
def gauss(f,l,r,n=96):
 x,w=np.polynomial.legendre.leggauss(n);xx=(r+l)/2+(r-l)/2*x;return float(np.dot(w,f(xx))*(r-l)/2)
R=12.5;a=10;Af=clipped(R,a);Ifx=gauss(lambda x:2/3*(R*R-x*x)**1.5,-a,a);Ify=gauss(lambda x:2*x*x*np.sqrt(R*R-x*x),-a,a)
assert abs(Ifx-gauss(lambda x:2/3*(R*R-x*x)**1.5,-a,a,192))<1e-8
rh=2.15;lim=math.asin(math.sqrt(12.6**2-12.5**2)/rh)
def cut_integral(power):
 def f(t):
  y=rh*np.sin(t);hi=np.sqrt(18**2-y*y);lo=np.maximum(12.5,np.sqrt(12.6**2-y*y));weight=2*rh*rh*np.cos(t)**2
  return weight*(hi-lo if power==0 else (hi*hi-lo*lo)/2)
 return sum(gauss(f,l,r) for l,r in zip([-math.pi/2,-lim,lim],[ -lim,lim,math.pi/2]))
cutV=cut_integral(0);cutMx=cut_integral(1)
bodies={}
def put(n,V,x,y,z,kind,group):
 p=[x/1000,y/1000,z/1000];bodies[n]=dict(volume_m3=V/1e9,centroid_before_tilt_mm=[x,y,z],centroid_m=[p[0]*math.cos(alpha)+p[1]*math.sin(alpha),-p[0]*math.sin(alpha)+p[1]*math.cos(alpha),p[2]],kind=kind,service_group=group)
def parts(n,ps,kind,group):
 V=sum(v for v,x,y,z in ps);put(n,V,*[sum(v*p[i] for v,*p in ps)/V for i in range(3)],kind,group)
put('SHAFT',math.pi*R*R*620-(math.pi*R*R-Af)*48,0,124,350,'steel','roller')
put('SHELL',ring(76,70,486),0,124,350,'steel','roller')
for side,sgn in [('LEFT',1),('RIGHT',-1)]:
 mirror=lambda z:z if side=='LEFT' else 700-z
 put('CARRIER_'+side,ring(76,52,21),0,124,mirror(96.5),'steel','roller')
 put('BEARING_ENV_'+side,ring(52,25,15),0,124,mirror(99.5),'envelope','roller')
 parts('ROT_CAP_'+side,[(ring(76,72,4),0,124,mirror(82)),(ring(62,26.5,4),0,124,mirror(82)),(ring(76,26.5,2),0,124,mirror(85))],'steel','roller')
 parts('STATOR_'+side,[(ring(36,25.2,10),0,124,mirror(72)),(ring(70,25.2,2),0,124,mirror(78)),(ring(70,64,4),0,124,mirror(81)),(-cutV,cutMx/cutV,124,mirror(72))],'steel','roller')
 put('M4_SET_ENV_'+side,math.pi*4**2/4*6,15.5,124,mirror(72),'envelope','roller')
 # Keeper is a blind double-flat bore in one plate; symbolic bolts are unthreaded solids.
 bhA=math.pi*6.5**2/4;plateA=60*45-2*bhA;holeA=clipped(12.8,10.25)
 parts('KEEPER_'+side,[(plateA*8.5,0,(60*45*122.5-2*bhA*135)/plateA,mirror(41.75)),(-holeA*6.5,0,124.25,mirror(42.75))],'steel','keeper')
 h=145-124.25;b=math.sqrt(12.75**2-10.25**2);J=10.25*b+12.75**2*math.asin(10.25/12.75)
 notchA=2*10.25*h+J;notchM=10.25*(145**2-124.25**2)+124.25*J-(2*10.25*12.75**2-2*10.25**3/3)/2
 V=(60*45-notchA-2*bhA)*8;cy=(60*45*122.5-notchM-2*bhA*135)/(V/8)
 put('FORK_'+side,V,0,cy,mirror(50),'steel','fixed')
 for x,tag in [(-22,'MINUS'),(22,'PLUS')]:
  hexA=math.sqrt(3)*10**2/2
  parts('M6_BOLT_'+side+'_'+tag,[(math.pi*6**2/4*30,x,135,mirror(50.9)),(hexA*4,x,135,mirror(33.9))],'hardware','removed')
  put('M6_NUT_'+side+'_'+tag,(hexA-math.pi*6**2/4)*5,x,135,mirror(58.1),'hardware','removed')
  for zz,nm in [(36.7,'OUT'),(54.8,'IN')]:put('M6_WASH_'+side+'_'+tag+'_'+nm,ring(12,6.5,1.6),x,135,mirror(zz),'hardware','removed')
railA=50*100-(4-math.pi)*6**2-44*94+(4-math.pi)*3**2
for z,s in [(50,'LEFT'),(650,'RIGHT')]:put('REF_RAIL_'+s,railA*400,0,50,z,'reference','fixed')
assert len(bodies)==34
shaftmass=bodies['SHAFT']['volume_m3']*rho
rotmass=sum(v['volume_m3'] for n,v in bodies.items() if n.startswith(('SHELL','CARRIER_','ROT_CAP_')))*rho+.26
# Beam with flat sections in first/last14mm of the600mm span. Bearing force locations49.5/550.5mm.
nodes=np.unique(np.r_[np.linspace(0,600,81),14,49.5,300,550.5,586]);nd=len(nodes)*2;K=np.zeros((nd,nd));fown=np.zeros(nd);Ic=math.pi*25**4/64;shaft_normal_weight=shaftmass*g*math.cos(alpha);qs=shaft_normal_weight/600
for j in range(len(nodes)-1):
 L=nodes[j+1]-nodes[j];I=Ifx if (nodes[j]+nodes[j+1])/2<14 or (nodes[j]+nodes[j+1])/2>586 else Ic
 ke=E*I/L**3*np.array([[12,6*L,-12,6*L],[6*L,4*L*L,-6*L,2*L*L],[-12,-6*L,12,-6*L],[6*L,2*L*L,-6*L,4*L*L]])
 ids=np.arange(2*j,2*j+4);K[np.ix_(ids,ids)]+=ke;fown[ids]+=qs*np.array([L/2,L*L/12,L/2,-L*L/12])
free=np.array([i for i in range(nd) if i not in [0,nd-2]]);inv=np.linalg.inv(K[np.ix_(free,free)])
def idx(x):return int(np.where(nodes==x)[0][0])
def interpolate(u,z):
 j=min(len(nodes)-2,int(np.searchsorted(nodes,z,side='right')-1));L=nodes[j+1]-nodes[j];t=(z-nodes[j])/L
 return float(np.dot([1-3*t*t+2*t**3,L*(t-2*t*t+t**3),3*t*t-2*t**3,L*(-t*t+t**3)],u[2*j:2*j+4]))
cases=[];check=[]
for pitch in [.25,.5,.75]:
 for kp in [1,2,3]:
  for ecc in [-250,0,250]:
   base=g*math.cos(alpha)*35*pitch;peak=g*math.cos(alpha)*15*kp
   F1=(base+rotmass*g*math.cos(alpha))/2+peak*(250.5-ecc)/501;F2=(base+rotmass*g*math.cos(alpha))/2+peak*(250.5+ecc)/501
   f=fown.copy();f[2*idx(49.5)]+=F1;f[2*idx(550.5)]+=F2;u=np.zeros(nd);u[free]=inv@f[free];reaction=K@u-f
   Ra=-reaction[0];Rb=-reaction[-2];assert abs(Ra+Rb-F1-F2-shaft_normal_weight)<1e-6
   def moment(z):return Ra*z-qs*z*z/2-F1*np.maximum(0,z-49.5)-F2*np.maximum(0,z-550.5)
   vm=0
   for l,r in zip([0,14,49.5,300,550.5,586],[14,49.5,300,550.5,586,600]):
    I=Ifx if (l+r)/2<14 or (l+r)/2>586 else Ic
    vm+=gauss(lambda z:moment(z)*np.minimum(z,600-z)/2/(E*I),l,r,16)
   err=abs(vm-u[2*idx(300)]);assert err<1e-8
   zz=np.unique(np.r_[np.linspace(0,600,6001),14-1e-8,586+1e-8]);Is=np.where((zz<14)|(zz>586),Ifx,Ic)
   stresses=abs(moment(zz))*12.5/Is
   # Relative displacement of shaft-borne stator and straight rotor axis through bearing centres.
   yl=interpolate(u,49.5);yr=interpolate(u,550.5)
   relative=[]
   for z in [22,28,31,33,567,569,572,578]:
    rotor=yl+(yr-yl)*(z-49.5)/501;relative.append(abs(interpolate(u,z)-rotor))
   cases.append(dict(pitch_m=pitch,local_peak_multiplier_sensitivity=kp,eccentricity_mm=ecc,bearing_left_N=F1,bearing_right_N=F2,support_left_N=Ra,support_right_N=Rb,shaft_max_deflection_mm=float(max(abs(u[::2]))),shaft_max_sigma_MPa=float(max(stresses)),seal_axis_relative_max_mm=max(relative),equilibrium_error_N=float(abs(Ra+Rb-F1-F2-shaft_normal_weight)),midpoint_virtual_work_error_mm=err))
bridge_h=145-124.25-12.8;Icap=8.5*bridge_h**3/12;Wcap=8.5*bridge_h**2/6;Ucases=[dict(uplift_one_keeper_scenario_N=U,bridge_sigma_MPa=U*44/4/Wcap,bridge_deflection_mm=U*44**3/(48*E*Icap),bolt_nominal_shear_stress_on_smooth_6mm_shank_MPa=U/(2*math.pi*6**2/4)) for U in [0,250,500,1000]]
lo=0;hi=math.atan2(7.5,10)
for _ in range(100):
 mid=(lo+hi)/2
 if 10*math.cos(mid)+7.5*math.sin(mid)>10.25:hi=mid
 else:lo=mid
d=dict(revision='R11_FLAT',scope='Одна плоская роликовая станция: наружная фиксация оси и геометрический лабиринт; развитие R09, отдельно от желоба R10',inputs=dict(belt_width_mm=500,overall_length_mm=10000,nominal_seat_to_belt_top_mm=170,belt_thickness_assumed_mm=8,roller_centre_height_mm=124,downhill_example_deg=1.5,q_material_orientation_kg_m=30,q_belt_assumed_kg_m=5,one_peak_kg=15,actual_drop_height_m=None,actual_uplift_N=None,actual_axis_drag_torque_Nm=None,actual_wash_pressure=None),geometry=dict(roller_OD_mm=76,face_length_mm=540,shell_length_mm=486,shaft_diameter_mm=25,shaft_length_mm=620,shaft_flats_width_mm=20,shaft_flats_length_each_mm=24,fork_and_keeper_bore_width_mm=20.5,fork_bore_radius_mm=12.75,keeper_bore_radius_mm=12.8,bore_centre_height_mm=124.25,loaded_shaft_height_mm=124,keeper_size_mm=[60,45,8.5],blind_end_wall_mm=2,shaft_axial_end_clearance_each_mm=.5,shaft_lift_clearance_mm=.55,keeper_M6_holes_pitch_mm=44,bearing_centres_mm=[99.5,600.5],bearing_span_mm=501,shaft_support_span_mm=600,carrier_length_each_mm=21,minimum_labyrinth_radial_gap_mm=1,minimum_labyrinth_axial_gap_mm=1,rotating_cap_shaft_radial_gap_mm=.75,static_shield_to_reference_rail_gap_mm=2,nominal_anti_rotation_angular_clearance_each_deg=math.degrees(hi)),section=dict(shaft_flat_area_mm2=Af,I_vertical_bending_flat_mm4=Ifx,I_horizontal_bending_flat_mm4=Ify,I_circular_mm4=Ic),mass=dict(one_station_steel_excluding_refs_hardware_envelopes_kg=sum(v['volume_m3'] for v in bodies.values() if v['kind']=='steel')*rho,shaft_kg=shaftmass,rotating_mass_with_bearing_pair_estimate_kg=rotmass,bearing_pair_catalog_estimate_kg=.26),shaft_cases=cases,keeper_uplift_sensitivity=Ucases,expected_bodies=bodies,service_sequence=['Снять натяжение и обеспечить локальный подъём/отвод ленты; источник движения отключён','Снять4 болта M6 и гайки/шайбы; конкретный инструмент и доступ ещё не подтверждены','Вывести каждую торцевую крышку наружу на15мм; это проверяемое геометрическое положение','Поднять ролик с осью и неподвижными крышками на35мм; лента должна быть поднята/отведена минимум на эту величину','Проверить регулировку и фиксацию после обратной сборки; порядок в составе полной машины ещё не отработан'],checks=dict(body_count=34,shaft_cases_count=27,beam_nodes_count=len(nodes),shaft_midpoint_virtual_work_independent=True,beam_equilibrium_passed=True,flat_section_gauss96_192_match=True,minimum_gap_not_tolerance_approved=True,simulation_performed=False),sources=[dict(title='Rulmeca PSV: назначение уплотнений роликов; источник принципа, не геометрии R11',url='https://www.rulmeca.com/en/steel-rollers---psv/11/p'),dict(title='SKF: направление воды в зазор и необходимость отвода загрязнений; не проверка R11',url='https://metalchallenges.skf.com/africa/mainpage_all_challenge17_africa_metals_MetalChallenges'),dict(title='Bossard: номинальная площадь резьбы M6 20,1мм²',url='https://www.bossard.com/global-en/-/media/bossard-group/website/documents/technical-resources/en/f-004-en.pdf')],limitations=['Кандидат одной плоской станции, не четырёхроликовая зона или полная сборка','Контур лабиринта металлический и бесконтактный; нет подтверждения водостойкости, загрязнения/фильтрата, защиты от наматывания и необходимости контактного барьера/смазки','Номинальные зазоры не включают допуски, биение, тепловые перемещения, люфты и наклон осей','Неподвижные лабиринтные части условно закреплены M4; резьба/контакт/момент фиксации и покрытие не проверены','Посадки и внутреннее осевое удержание колец подшипников ещё открыты; габаритные кольца не моделируют реальные кольца/уплотнения','Оценка оси включает вертикальный изгиб и лыски; концентраторы, горизонтальная нагрузка, кручение и усталость не проверены','Реальная сила подъёма и момент на оси неизвестны; U0/250/500/1000Н только чувствительность, не принятие расчётной нагрузки','Балочная оценка верхней перемычки крышки и дополнительной силы болтов исключает местный контакт, изгиб стенки2мм, осевую нагрузку, преднатяг и отрыв/податливость соединения','Модель не имеет реальных резьб; отверстие4,3мм обозначает только освобождённый габарит резьбы M4, не размер сверления для изготовления','Не обновлены общая рама, подача, привод, натяжение, инерция всей системы и R08','Материалы, посадки, чертежи/DXF/технология/УП не выпущены'])
(B/'work/flat_roller_r11.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8');(O/'02_Расчеты/ЛТ500_Фиксация_и_защита_плоского_ролика_R11.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(count=len(bodies),nodes=len(nodes),mass=d['mass'],max_sigma=max(x['shaft_max_sigma_MPa'] for x in cases),max_deflection=max(x['shaft_max_deflection_mm'] for x in cases),max_seal_axis_offset=max(x['seal_axis_relative_max_mm'] for x in cases),angular_play=d['geometry']['nominal_anti_rotation_angular_clearance_each_deg']),ensure_ascii=False))
