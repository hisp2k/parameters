from pathlib import Path
import json,math
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер'
th=math.radians(20);al=math.radians(1.5);g=9.80665;rho=7850
def polygon(points):
 a=cx=cy=0
 for (x,y),(u,v) in zip(points,points[1:]+points[:1]):
  k=x*v-u*y;a+=k;cx+=(x+u)*k;cy+=(y+v)*k
 return abs(a/2),cx/(3*a),cy/(3*a)
def rx(p,a,y,z):
 x,v,w=p;v-=y;w-=z
 return [x,y+v*math.cos(a)-w*math.sin(a),z+v*math.sin(a)+w*math.cos(a)]
def rz(p):
 x,y,z=p;return [x*math.cos(al)+y*math.sin(al),-x*math.sin(al)+y*math.cos(al),z]
bodies={}
def add(n,vol,p,a=0,y=0,z=0):
 p=rx(p,a,y,z);bodies[n]={'volume_m3':vol/1e9,'centroid_before_longitudinal_tilt_m':[x/1000 for x in p],'centroid_m':[x/1000 for x in rz(p)]}
def tube(n,w,h,t,r,L,centre):
 A=w*h-(4-math.pi)*r*r-(w-2*t)*(h-2*t)+(4-math.pi)*(r-t)**2
 add(n,A*L,centre);return A
for z,s in [(50,'LEFT'),(650,'RIGHT')]:tube('REF_RAIL_'+s,50,100,3,6,600,[0,50,z])
tube('CROSSBEAM',40,40,3,6,700,[0,120,350])
jb=90+4*math.tan(th/2);jt=90-4*math.tan(th/2)
vc=222+110*math.sin(th)-38*math.cos(th);zc=jb+110*math.cos(th)+38*math.sin(th)
supports=[]
for dz,s in [(-96,'MINUS'),(96,'PLUS')]:
 pts=[(350+dz-4,140),(350+dz+4,140),(350+dz+4,160),(350+dz-4,160)];A,cz,cy=polygon(pts);name='CENTRE_POST_'+s
 add(name,A*60,[0,cy,cz]);supports.append(dict(name=name,points_ZY_mm=pts,plate_thickness_along_roller_axis_mm=8,min_height_mm=20,max_height_mm=20))
for tag,y,z,a in [('CENTRE',184,350,0),('LEFT',vc,350-zc,th),('RIGHT',vc,350+zc,-th)]:
 def ring(n,od,id,L,offset):add(n,math.pi*(od**2-id**2)/4*L,[0,y,z+offset],a,y,z)
 ring('SHELL_'+tag,76,70,150,0);ring('SHAFT_'+tag,25,0,200,0)
 for dz,s in [(-82.5,'MINUS'),(82.5,'PLUS')]:
  ring('CARRIER_'+tag+'_'+s,76,52,15,dz);ring('BEARING_ENV_'+tag+'_'+s,52,25,15,dz)
 for dz,s in [(-96,'MINUS'),(96,'PLUS')]:
  # Rectangle less open neck and lower semicircular notch. Coordinates relative to axis.
  ar=60*45;an=25*21;ac=math.pi*12.5**2/2;af=ar-an-ac
  yf=(ar*(-1.5)-an*10.5-ac*(-4*12.5/(3*math.pi)))/af
  add('FORK_'+tag+'_'+s,af*8,[0,y+yf,z+dz],a,y,z)
  if tag!='CENTRE':
   sign=1 if tag=='RIGHT' else -1;inner=dz==-96*sign
   base=rx([0,y-24,z+dz],a,y,z)
   # Inclined sides follow the fork's axial planes, rather than extending vertically into the carrier.
   top=[];bottom=[]
   for da in [-4,4]:
    pt=rx([0,y-24,z+dz+da],a,y,z);top.append((pt[2],pt[1]))
    dy=(140-y+(dz+da)*math.sin(a))/math.cos(a)
    pb=rx([0,y+dy,z+dz+da],a,y,z);bottom.append((pb[2],pb[1]))
   pts=[bottom[0],bottom[1],top[1],top[0]]
   A,czc,yc=polygon(pts);name=('INNER_WEDGE_' if inner else 'OUTER_PEDESTAL_')+tag
   add(name,A*60,[0,yc,czc]);supports.append(dict(name=name,points_ZY_mm=pts,plate_thickness_along_roller_axis_mm=8,min_height_mm=min(p[1] for p in top)-140,max_height_mm=max(p[1] for p in top)-140))
vlow=226+160*math.sin(th)-4*math.cos(th);vtop=226+160*math.sin(th)+4*math.cos(th)
zlow=90+160*math.cos(th)+4*math.sin(th);ztop=90+160*math.cos(th)-4*math.sin(th)
belt=[(350-zlow,vlow),(350-jb,222),(350+jb,222),(350+zlow,vlow),(350+ztop,vtop),(350+jt,230),(350-jt,230),(350-ztop,vtop)]
A,cz,cy=polygon(belt);add('BELT_PROFILE_ENVELOPE',A*180,[0,cy,cz])
def profile(deg):
 t=math.radians(deg);h=160*math.sin(t);w=180+320*math.cos(t);hw=h+4*(math.cos(t)-1);bt=180-8*math.tan(t/2);area=(bt+hw/math.tan(t))*hw/1e6
 z=max(0,hw-20);area20=(bt*z+z*z/math.tan(t))/1e6
 return dict(angle_deg=deg,projected_neutral_width_mm=w,edge_neutral_rise_mm=h,edge_working_rise_mm=hw,centre_working_flat_width_mm=bt,ideal_no_heap_area_m2=area,area_with_20mm_freeboard_m2=area20,required_density_for_q30_full_kg_m3=30/area)
profiles=[profile(x) for x in [20,30,35,45]];act=profiles[0]
trans=[]
for L in [500,750,1000,1500]:
 h=act['edge_neutral_rise_mm'];dz=160*(1-math.cos(th));trans.append(dict(length_mm=L,edge_fibre_straight_line_lower_bound_strain=math.sqrt(1+(h*h+dz*dz)/(L*L))-1))
P=g*math.cos(al)*(35*.75+15)
loads=[]
for label,beta in [('Симметрия 50/25/25',[.5,.25,.25]),('Равные доли',[1/3]*3),('Вся нагрузка на центре',[1,0,0]),('Вся нагрузка на правом',[0,0,1])]:
 nv=[P*beta[0],P*beta[1]/math.cos(th),P*beta[2]/math.cos(th)]
 loads.append(dict(case=label,vertical_shares=beta,P_N=P,normal_only_N=nv,left_right_transverse_N=[-P*beta[1]*math.tan(th),P*beta[2]*math.tan(th)],vertical_resultant_normal_N=[P*beta[0],P*beta[1]*math.cos(th),P*beta[2]*math.cos(th)],vertical_resultant_axial_N=[0,P*beta[1]*math.sin(th),P*beta[2]*math.sin(th)]))
metal=sum(v['volume_m3'] for k,v in bodies.items() if not k.startswith(('REF_','BEARING_ENV_','BELT_')))*rho
rot=sum(v['volume_m3'] for k,v in bodies.items() if k.startswith(('SHELL_CENTRE','CARRIER_CENTRE')))*rho+.26
shaft=bodies['SHAFT_CENTRE']['volume_m3']*rho
N=P/math.cos(th)+g*(rot+shaft);I=math.pi*25**4/64
screen=dict(all_load_at_centre_N=N,shaft_support_span_mm=192,E_assumed_MPa=200000,shaft_sigma_MPa=N*192/4*12.5/I,shaft_deflection_mm=N*192**3/(48*200000*I),meaning='Одна крайняя схема нормальной силы и веса в центре. Не расчёт контактов, осевого усилия, фиксации или ресурса.')
# Independent numerical quadrature of cross-section and polygon volume checks.
step=act['edge_working_rise_mm']/100000;num=sum((act['centre_working_flat_width_mm']+2*(i+.5)*step/math.tan(th))*step for i in range(100000))/1e6
assert abs(num-act['ideal_no_heap_area_m2'])<1e-12 and len(bodies)==34
assert min(x['min_height_mm'] for x in supports)>0
d=dict(revision='R10',scope='Трёхроликовый желоб вместо плоской несущей ветви R09; один самостоятельный опорный узел',inputs=dict(belt_width_mm=500,overall_length_mm=10000,centre_working_height_assumed_mm=800,longitudinal_downhill_deg=1.5,trough_angle_candidate_deg=20,belt_thickness_assumed_mm=8,centre_neutral_width_mm=180,wing_neutral_width_mm=160,material_q_orientation_kg_m=30,belt_q_assumed_kg_m=5,one_peak_kg=15,density_actual_kg_m3=None,speed_actual_m_s=None,regular_pitch_candidate_m=.75,loading_pitch_candidate_m=.25),geometry=dict(face_mm=180,diameter_mm=76,shell_ID_mm=70,shell_length_mm=150,shaft_diameter_mm=25,shaft_length_mm=200,shaft_support_span_mm=192,bearing_centres_span_mm=165,roller_virtual_crease_gap_mm=20,centre_axis_Y_mm=184,wing_axis_Y_mm=vc,wing_axis_offset_Z_mm=zc,seat_to_centre_working_belt_mm=230,previous_interface_mm=170,crossbeam='40×40×3; длина700, радиусы6/3',reference_rails='100×50×3; длина600, центрыZ50/650',belt_polygon_ZY_mm=belt,belt_polygon_area_mm2=A,supports=supports),profiles=profiles,transition_scenarios=trans,load_scenarios=loads,shaft_screen=screen,mass_estimate=dict(metal_without_refs_bearing_envelopes_belt_kg=metal,six_bearings_candidate_kg=.78,station_estimate_kg=metal+.78,one_rotating_supported_mass_kg=rot,one_shaft_mass_kg=shaft),expected_bodies=bodies,checks=dict(body_count=34,area_independent_quadrature_error_m2=abs(num-act['ideal_no_heap_area_m2']),all_pedestal_min_heights_positive=True),sources=[dict(title='Habasit · Fabric Conveyor Belts Engineering Guide, стр.56: желоб и переходы; относится к лёгким тканевым лентам',url='https://www.habasit.com/-/media/Project/Habasit/NewWebsite/Downloads/Products/General-conveyor-belts/Fabric-Conveyor-Belts-Engineering-Guide.pdf'),dict(title='Rulmeca · каталог роликов и роликоопор для насыпных материалов',url='https://rulmecacorp.com/conveyor-roller-catalog/'),dict(title='SKF · подшипники: габаритный кандидат25×52×15 и масса0,13кг',url='https://cdn.skfmediahub.skf.com/api/public/0901d196802809de/pdf_preview_medium/0901d196802809de_pdf_preview_medium.pdf')],limitations=['Угол20°, толщина8мм, опорные размеры и шаги — кандидаты; лента не выбрана и желобчатость не подтверждена','Геометрия резких складок ленты — огибающая, не реальная форма изгиба','Длина перехода750мм только резерв компоновки, не разрешённая длина по поставщику','Плотность, производительность, скорость, падение и фактические зоны неизвестны','R08/R09 не подтверждают натяжение/привод новой желобчатой схемы','Высоту стоек и переходные/концевые опоры ещё требуется обновить','Открытые вилки без фиксации и уплотнений; нет чертежей/допусков/швов/производственного выпуска','Общая сборка10000мм и Simulation не выполнены'])
(B/'work/trough_r10.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
(O/'02_Расчеты/ЛТ500_Желобчатый_узел_R10.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(body_count=len(bodies),profile=act,mass=d['mass_estimate'],shaft=screen),ensure_ascii=False))
