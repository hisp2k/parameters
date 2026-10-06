from pathlib import Path
import json, math, hashlib, zipfile, shutil
from xml.etree import ElementTree as ET
from pypdf import PdfReader
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер';d=json.loads((B/'work/traction_r08.json').read_text(encoding='utf8'))
def write(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
base=json.loads((O/'00_Исходные_данные/Реестр_исходных_данных_R07.json').read_text(encoding='utf8'))
base['revision']='R08';base['active_support_geometry']='R07: геометрический кандидат среднего узла; R08 не изменяет CAD'
base['traction_and_tension_iteration']={k:d[k] for k in ['revision','scope','inputs','extrema','checks','sources','limitations']}
base['traction_and_tension_iteration']['fixed_mean_comparison']={k:v for k,v in d['fixed_mean_comparison'].items() if k!='states'}
base['status']='ПРЕДВАРИТЕЛЬНЫЙ ПРОЕКТ — НЕ ДЛЯ ИЗГОТОВЛЕНИЯ'
write(O/'00_Исходные_данные/Реестр_исходных_данных_R08.json',base)
forces=[]
for key,kind in [('drive_resultant_N','HEAD'),('tail_resultant_N','TAIL')]:
 state=d['fixed_mean_comparison']['extrema'][key]['max_case'];r=next(x for x in d['all486'] if x['id']==state['source_id']);R=state[key];a=math.radians(r['angle_deg']);sign=-1 if kind=='HEAD' else 1
 forces.append(dict(node=kind,model='constant_mean_EA_comparison_only',source_case=r,peak_position_fraction=state['peak_position_fraction'],T_out_N=state['T_out_N'],T_in_N=state['T_in_N'],T_tail_N=state['T_tail_N'],R_belt_N=R,F_X_N=sign*R*math.cos(a),F_Y_N=-sign*R*math.sin(a),F_Z_N=0,own_weight_and_drive_reaction_excluded=True,bearing_reactions=None))
register=dict(revision='R08',status='CONDITIONAL SCENARIOS, NOT DESIGN CAPACITY',axes='X горизонтально к выгрузке; Y вверх; Z поперёк',geometry='2 параллельные ветви, обхват 180°; сила ленты на узел барабана',Fu_scenario_range_N=d['extrema']['Fu_N'],belt_torque_range_at_example_D200_Nm=d['extrema']['belt_torque_example_Nm'],fixed_mean_comparison_T_N=d['fixed_mean_comparison']['T_mean_target_N'],end_forces=forces,jam_output_torque_limit_Nm=None,jam_force_N=None,selected_motor=None,selected_belt=None,selected_bearings=None,selected_tensioner=None,load_transfer_to_single_R07_pin_N=None,requirements=['Определить путь усилий от подшипников через концевые рамы и продольные элементы к опорам и анкерам.','Назначить полную схему фиксированных/подвижных опор; реакции стыка не приравнивать к результирующим на барабанах.','Подтвердить ленту, шаги/провис, мокрое сцепление, сопротивления и реальное натяжение; постоянное среднее T не является настройкой винта.','Добавить вес, реакцию и инерцию головного привода; рассчитать вал/подшипники по фактической геометрии, не R/2 без неё.','Рассчитать ограниченный момент заклинивания, остановку и пуск; проверить общую/местную прочность, усталость и основание.'])
write(O/'02_Расчеты/ЛТ500_Регистр_нагрузок_привода_R08.json',register)
assert all(d['checks'][k] for k in ['force_balance_all486','capstan_and_sag_constraints_all486','single_peak_position_bounds'])
write(O/'11_Испытания_и_контроль/Проверка_механики_тяги_R08.json',dict(revision='R08',**d['checks'],scenarios=486,fixed_mean_states=1458,CAD_updated=False,not_for_manufacturing=True))
f=O/'02_Расчеты/ЛТ500_Расчёт_тяги_и_натяжения_R08.xlsx';qa=json.loads((B/'work/traction_xlsx_qa_r08.json').read_text(encoding='utf8'));assert 'matched 0 entries' in (B/'work/traction_xlsx_scan_r08.txt').read_text(encoding='utf8')
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};count=0;errors=[];sheets=0;empty_caches=[]
with zipfile.ZipFile(f) as z:
 assert z.testzip() is None
 for n in z.namelist():
  if n.startswith('xl/worksheets/sheet') and n.endswith('.xml'):
   root=ET.fromstring(z.read(n));sheets+=1
   for c in root.findall('.//m:c',ns):
    if c.attrib.get('t')=='e':errors.append(c.attrib.get('r'))
    if c.find('m:f',ns) is not None:
     count+=1
     if c.find('m:v',ns) is None:empty_caches.append([n,c.attrib.get('r')])
 assert sheets==3 and not errors and not empty_caches
qa.update(all_three_sheets_visually_checked=True,preview_regions_checked=8,formula_scan_zero_matches=True,exported_formula_count=count,exported_cached_errors=errors,formulas_without_cached_values=empty_caches)
write(O/'11_Испытания_и_контроль/Проверка_расчётной_книги_R08.json',qa)
pdf=O/'01_Техническое_задание/ЛТ500_Тяга_натяжение_и_привод_R08.pdf';assert len(PdfReader(pdf).pages)==5
write(O/'11_Испытания_и_контроль/Проверка_отчёта_R08.json',dict(pages=5,all_pages_rendered_and_visually_checked=True,diagram='расчётная схема параллельных ветвей, без масштаба',status='NOT FOR MANUFACTURING'))
ip=Path(str(f)+'.inspect.ndjson')
if ip.exists():shutil.move(ip,B/'work/traction_export_r08.inspect.ndjson')
status='''ЛТ500 — ПРЕДВАРИТЕЛЬНЫЙ ПРОЕКТ R08, 04.10.2026
НЕ ДЛЯ ИЗГОТОВЛЕНИЯ

Начать с 01_Техническое_задание/ЛТ500_Тяга_натяжение_и_привод_R08.pdf.
R08 — тяга, натяжение, пуск, остановка и нагрузки барабанов.
Действующая геометрия среднего узла и EBOM остаются R07;
предыдущие R02–R06 — история и основания, не новые размеры.

Подтверждено: лента500, полная длина10000, высота рабочей поверхности
около800 мм, уклон вниз1–2°, мокрые отбросы до3 решёток, 24ч/сут,
помещение/вода/380В, пуск с материалом. Точные зоны подачи неизвестны.
q30 кг/м + единственные15 кг совместно — условное сочетание.
15 кг не превращены в3 одновременные порции и не заданы как удар.

Допущения: L прямой ветви10 м (не утверждённые оси барабанов),
qB5 кг/м, дополнительная инерционная масса60 кг по30 на ветвь,
без инерции головного привода. Коэффициенты c0,01/0,03/0,06,
дополнительное сопротивление0/100/200Н и μ0,1/0,2/0,3 условны.
Скорости0,1/0,2/0,3 м/с и D200 мм — примеры, не выбор компонентов.
Обхват180°, параллельные ветви. Провис рабочей1% и обратной2%
предлагается для сравнения, не утверждённый норматив.

Шаг рабочей0,75 м, q+qB35 кг/м и точечные15 кг в середине:
Tпровис6,893 кН для7,5 мм. Без локальных15 кг:3,217 кН.
Опоры/площадка зоны загрузки и реальное распределение порции
могут изменить определяющую схему; сопротивление нужно обновить.
Итог486 примеров Fu−209,64…754,81Н; момент ленты при D200
−20,96…75,48Н·м. Отрицательные значения требуют удерживающего
момента в заданном режиме. Мощность Fu*v — мгновенная мощность
ленты, не номинал мотора; тормоз/редуктор ещё не выбраны.

Минимум T рассчитан заново по каждому режиму — это не настройка
винтового натяжителя. Дополнительно отдельная упругая модель:
постоянные EA и длина пути, среднееT7,049 кН, 1458 случаев.
Силы от ленты: голова13,782…14,136 кН, хвост13,940…14,206 кН.
Они не являются утверждённым пределом машины и исключают вес,
реакцию/инерцию головного привода, заклинивание и удар.
Температура, ползучесть и изменение длины от провиса не учтены.

Силы барабанов нельзя напрямую назначить одной связи M10 R07.
Нужен полный путь усилий от подшипников через концевые рамы
и продольные элементы к опорам/анкерам, общая схема закрепления.
Разделение R/2 между подшипниками без геометрии не назначено.
Фактический ограниченный момент заклинивания неизвестен;
термореле не принимается механическим ограничителем.

Проверки:486 общих/ветвевых балансов, сцепление/провис,
границы положения локальной массы; независимая нить1001узел;
1458 сравнения постоянного среднегоT. Simulation не выполнялась.
Excel3листа:3+27 случаев сверены с Python, изменённые/пустые
исходные проверены и восстановлены; ошибок формул0.
PDF5страниц и8областей Excel просмотрены. Microsoft Excel не тестирован.

Следующая итерация: опоры загрузки/лента/ролики, скорость и привод,
реальное натяжение, концевые рамы/валы/подшипники, общая рама/стыки,
опоры/анкеры/основание. Допускаемые сопротивления, усталость,
материалы, швы, крепёж, покрытие и производственный выпуск открыты.
Высота800 по середине и интерфейс170 мм до рельса остаются допущениями.
'''
(O/'СТАТУС_КОМПЛЕКТА_R08.txt').write_text(status,encoding='utf8');(O/'СТАТУС_КОМПЛЕКТА.txt').write_text(status,encoding='utf8')
keep={'Первоначальное_задание.txt','ЛТ500_Предварительный_проект_R02.pdf','ЛТ500_Расчётный_паспорт_R02.xlsx','ЛТ500_MASTER_исходная_геометрия_R01.SLDPRT','master_creation_report_R01.json','master_inspection_report_R01.json','СТАТУС_КОМПЛЕКТА.txt'}
files=[p for p in O.rglob('*') if p.is_file() and ((any(r in p.name for r in ['R03','R04','R05','R06','R07','R08']) and not p.name.startswith('Реестр_файлов')) or p.name in keep)]
registry=[dict(path=str(p.relative_to(O)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(files)]
write(O/'Реестр_файлов_R08.json',dict(revision='R08',active_CAD_revision='R07',status='PRELIMINARY NOT FOR MANUFACTURING',files=registry))
(O/'Реестр_файлов_R08.txt').write_text('\n'.join(f"{x['path']} | {x['bytes']} байт | SHA256 {x['sha256']}" for x in registry),encoding='utf8')
files.extend([O/'Реестр_файлов_R08.json',O/'Реестр_файлов_R08.txt']);archive=B/'outputs/Ленточный_транспортер_ЛТ500_R08.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'Ленточный_транспортер/'+str(p.relative_to(O)).replace('\\','/'))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for x in registry:assert hashlib.sha256(z.read('Ленточный_транспортер/'+x['path'].replace('\\','/'))).hexdigest()==x['sha256']
 print(json.dumps(dict(files=len(z.namelist()),bytes=archive.stat().st_size,integrity='passed',xlsx_formula_count=count,active_CAD='R07')))
