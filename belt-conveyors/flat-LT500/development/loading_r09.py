from pathlib import Path
import json, math, itertools
import numpy as np
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер';g=9.80665;rho=7850;E=200000
q=35.;m=15.;ang=1.5;cs=math.cos(math.radians(ang))
def sag(p,a,s=.01):
 factor=1/(4*s) if a==0 else (2*p-a)/(8*s*p) if a<p else p/(8*s*a)
 return g*cs*(q*p/(8*s)+m*factor)
def roller_fraction(p,a):return 1. if a==0 else 1-a/(4*p) if a<2*p else p/a
cases=[]
for a in [0,.25,.5,.75,1.]:
 tl=sag(.25,a);tr=sag(.75,a)
 cases.append(dict(footprint_m=a,loading_pitch_m=.25,regular_pitch_m=.75,T_loading_N=tl,T_regular_N=tr,T_global_carry_N=max(tl,tr),roller_loading_normal_N=g*cs*(q*.25+m*roller_fraction(.25,a)),roller_regular_normal_N=g*cs*(q*.75+m*roller_fraction(.75,a))))
# Independently integrate Green's function and moving reaction influence line.
integration=[]
for p in [.25,.75]:
 for a in [0,.25,.5,.75,1.]:
  if a==0:
   center_def_coeff=q*p*p/8+m*p/4
   maxreactioncoeff=q*p+m
  else:
   # Integrate the clipped footprint centred on the worst span/support.
   xx=np.linspace(max(0,(p-a)/2),min(p,(p+a)/2),20001)
   G=np.minimum(xx,p-xx)/2
   center_def_coeff=q*p*p/8+(m/a)*np.trapezoid(G,xx)
   xr=np.linspace(max(-p,-a/2),min(p,a/2),20001)
   maxreactioncoeff=q*p+(m/a)*np.trapezoid(1-np.abs(xr)/p,xr)
  T=center_def_coeff*g*cs/(.01*p);R=maxreactioncoeff*g*cs
  assert abs(T-sag(p,a))<1e-5 and abs(R-g*cs*(q*p+m*roller_fraction(p,a)))<1e-5
  integration.append(dict(pitch_m=p,footprint_m=a,T_integrated_N=T,reaction_integrated_N=R))
# Geometric roller candidate: stationary shaft, cylindrical shell and bearing envelopes.
geom=dict(loading_station_centers_mm=[-375,-125,125,375],pitch_mm=250,roller_OD_mm=76,shell_ID_mm=70,shell_length_mm=510,face_length_mm=540,shaft_OD_mm=25,shaft_length_mm=620,shaft_support_spacing_mm=600,bearing_centers_mm=[87.5,612.5],bearing_envelope_mm=[25,52,15],belt_width_mm=500,belt_thickness_assumed_mm=8,seat_to_belt_top_assumed_mm=170,roller_center_height_mm=124,rail_top_height_mm=100,bracket_width_mm=60,bracket_height_mm=45,bracket_thickness_mm=8,bracket_notch_radius_mm=12.5,bracket_bottom_ligament_mm=11.5,rail_reference_length_mm=1100,rail_centers_transverse_mm=[50,650],shell_to_rail_side_clearance_mm=5,angle_deg=1.5)
def ringvol(od,id,L):return math.pi*(od**2-id**2)*L/4/1e9
shellmass=ringvol(76,70,510)*rho;capmass=ringvol(76,52,15)*rho;shaftmass=ringvol(25,0,620)*rho
rotmass=shellmass+2*capmass+.26 # Catalog bearing mass is only an estimate; entire bearing counted with rotating load conservatively.
Ibody=math.pi*(76**4-70**4)/64;Ishaft=math.pi*25**4/64
# Shaft: 600mm simply supported beam, loads at bearing centres 37.5/562.5mm.
# Own mass of 620mm shaft spread over calculation span600mm; protruding ends not modeled.
L=600.;ne=80;dx=L/ne;nd=2*(ne+1);K=np.zeros((nd,nd));qshaft=shaftmass*g/L
ke=E*Ishaft/dx**3*np.array([[12,6*dx,-12,6*dx],[6*dx,4*dx**2,-6*dx,2*dx**2],[-12,-6*dx,12,-6*dx],[6*dx,2*dx**2,-6*dx,4*dx**2]])
fown=np.zeros(nd)
for j in range(ne):
 ids=np.arange(2*j,2*j+4);K[np.ix_(ids,ids)]+=ke;fown[ids]+=qshaft*np.array([dx/2,dx**2/12,dx/2,-dx**2/12])
free=[j for j in range(nd) if j not in [0,2*ne]];inv=np.linalg.inv(K[np.ix_(free,free)])
def beam(F1,F2):
 F=fown.copy();F[10]+=F1;F[150]+=F2;u=np.zeros(nd);u[free]=inv@F[free];reactions=K@u-F
 assert abs(-reactions[0]-reactions[160]-F1-F2-shaftmass*g)<1e-6
 mid=(F1+F2)*37.5*(3*L**2-4*37.5**2)/(48*E*Ishaft)+5*qshaft*L**4/(384*E*Ishaft)
 assert abs(u[80]-mid)<1e-8
 sample=np.linspace(0,L,1201);Ra=-reactions[0];moment=Ra*sample-qshaft*sample**2/2-F1*np.maximum(0,sample-37.5)-F2*np.maximum(0,sample-562.5)
 return dict(deflection_max_mm=float(max(abs(u[::2]))),sigma_max_MPa=float(max(abs(moment))*12.5/Ishaft),left_support_N=Ra,right_support_N=-reactions[160],max_equilibrium_residual_N=float(max(abs((K@u-F)[free]))))
strength=[]
for pitch,kp,ecc in itertools.product([.25,.5,.75],[1,2,3],[-250,0,250]):
 base=g*cs*q*pitch;peak=kp*m*g*cs;P=base+peak
 F1=(base+rotmass*g*cs)/2+peak*(262.5-ecc)/525;F2=(base+rotmass*g*cs)/2+peak*(262.5+ecc)/525
 Pshell=P+rotmass*g*cs
 r=beam(F1,F2);r.update(pitch_m=pitch,local_peak_multiplier_assumed=kp,transverse_peak_position_mm=ecc,belt_normal_N=P,shell_bound_total_force_N=Pshell,rotating_mass_estimate_kg=rotmass,bearing_left_N=F1,bearing_right_N=F2,shell_conservative_sigma_MPa=Pshell*525/4*38/Ibody,shell_conservative_deflection_mm=Pshell*525**3/(48*E*Ibody),shaft_all_load_at_mid_bound_mm=(P+rotmass*g*cs+shaftmass*g)*600**3/(48*E*Ishaft));strength.append(r)
# Geometry volumes and centroids, before tilt.
bodies={}
def put(n,v,x,y,z,kind):
 a=math.radians(ang);bodies[n]=dict(volume_m3=v,centroid_m=[x*math.cos(a)+y*math.sin(a),-x*math.sin(a)+y*math.cos(a),z],kind=kind)
ro=.006;ri=.003;A=50*100-(4-math.pi)*6**2-44*94+(4-math.pi)*3**2
for z in [.05,.65]:put('REF_RAIL_'+('LEFT' if z<.1 else 'RIGHT'),A*1100/1e9,0,.05,z,'reference')
notch_rect=25*21;notch_semi=math.pi*12.5**2/2;platearea=60*45-notch_rect-notch_semi
cy=(60*45*122.5-notch_rect*134.5-notch_semi*(124-4*12.5/(3*math.pi)))/platearea
for n,xmm in enumerate(geom['loading_station_centers_mm'],1):
 x=xmm/1000
 put(f'SHELL_{n}',ringvol(76,70,510),x,.124,.35,'candidate')
 put(f'SHAFT_{n}',ringvol(25,0,620),x,.124,.35,'candidate')
 for side,z0 in [('LEFT',80),('RIGHT',605)]:
  put(f'CARRIER_{n}_{side}',ringvol(76,52,15),x,.124,(z0+7.5)/1000,'candidate')
  put(f'BEARING_ENV_{n}_{side}',ringvol(52,25,15),x,.124,(z0+7.5)/1000,'envelope')
 for side,z in [('LEFT',.05),('RIGHT',.65)]:put(f'FORK_{n}_{side}',platearea*8/1e9,x,cy/1000,z,'candidate')
assert len(bodies)==34
d=dict(revision='R09',scope='Опоры зон загрузки; провис при перемещении единственной локальной массы; геометрический роликовый кандидат',inputs=dict(material_q_kg_m=30,belt_q_assumed_kg_m=5,one_peak_kg=15,angle_deg=1.5,relative_sag_proposed=.01,regular_pitch_assumed_m=.75,loading_pitch_candidate_m=.25,actual_footprint_m=None,drop_height_m=None,actual_dynamic_factor=None,actual_loading_zone_positions=None),cases=cases,geometry=geom,shaft_and_shell_screening=strength,expected_bodies=bodies,mass_estimates=dict(shell_kg=shellmass,carrier_each_kg=capmass,shaft_kg=shaftmass,bearings_pair_catalog_estimate_kg=.26,rotating_supported_mass_estimate_kg=rotmass,candidate_steel_without_envelopes_and_references_kg=sum(x['volume_m3'] for x in bodies.values() if x['kind']=='candidate')*rho,total_CAD_mass_at_uniform_7850_kg=sum(x['volume_m3'] for x in bodies.values())*rho),checks=dict(green_function_cases=integration,green_and_influence_match=True,shaft_81_nodes_cases=27,shaft_equilibrium_passed=True,simulation_performed=False),sources=[dict(title='Habasit Fabric Conveyor Belts Engineering Guide, 6039, pp9–10,38',url='https://www.habasit.com/-/media/Project/Habasit/NewWebsite/Downloads/Products/General-conveyor-belts/Fabric-Conveyor-Belts-Engineering-Guide.pdf',use='Принципы опоры, влияние влаги на сплошное скольжение и организация загрузки; не подбор ленты для отбросов и не источник численных коэффициентов R09.'),dict(title='SKF Single row deep groove ball bearings, 6205-2RSH',url='https://cdn.skfmediahub.skf.com/api/public/0901d196802809de/pdf_preview_medium/0901d196802809de_pdf_preview_medium.pdf',use='Габарит25×52×15мм и масса0,13кг только для компоновочного кандидата. Исполнение/ресурс/уплотнения не утверждены.')],limitations=['Частые ролики только под загрузкой не уменьшают глобальное натяжение, если15кг сохраняются компактной порцией на обычных пролётах. Сценарий точечной массы R08 остаётся действующим.','Длина пятна0,25–1м — предположение, не измеренная длина порции. Масса15кг учитывается единственная и не множится на3решётки.','Множители локальной нагрузки1/2/3 — чувствительность, не установленная ударная нагрузка. Высота падения неизвестна.','Ролик76×540, ось25×620 и подшипник25×52×15 — кандидат габаритов; не производственная конструкция или каталог выбранного ролика.','Открытые вилки показывают посадочное место; удержание оси от подъёма/вращения, осевая фиксация, крышки/уплотнения/посадки/швы и регулировка ещё не разработаны.','Колечки подшипников — сплошные габаритные тела; масса CAD при7850 не равна реальной массе подшипника. В оценке массы использовано0,13кг/шт из каталога.','Собственный вес оси620 распределён по расчётным600мм; консоли по10мм, осевые/касательные нагрузки и ослабления не моделируются.','Прочность/ресурс конструкции, контакт ленты, очистка, скрытые зазоры, коррозия/вода, фиксация и безопасность обслуживания не подтверждены.','Высота170мм от плоскости посадки трубы до верха ленты и толщина8мм условны. Новый участок не интегрирован в общую модель или средний узел R07.'])
(B/'work/loading_r09.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8');(O/'02_Расчеты/ЛТ500_Опоры_загрузки_R09.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(cases=cases,mass=d['mass_estimates'],shaft_max_delta=max(x['deflection_max_mm'] for x in strength),shaft_max_sigma=max(x['sigma_max_MPa'] for x in strength)),ensure_ascii=False))
