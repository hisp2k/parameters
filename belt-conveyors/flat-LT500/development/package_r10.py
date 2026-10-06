from pathlib import Path
import json,hashlib,zipfile,shutil
from xml.etree import ElementTree as ET
from pypdf import PdfReader
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер';d=json.loads((B/'work/trough_r10.json').read_text(encoding='utf8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
cp=O/'11_Испытания_и_контроль/Проверка_CAD_желобчатого_узла_R10.json';c=json.loads(cp.read_text(encoding='utf8'));assert c['ok'];c['preview_visually_checked']=True;write(cp,c)
base=json.loads((O/'00_Исходные_данные/Реестр_исходных_данных_R09.json').read_text(encoding='utf8'));base['revision']='R10';base['troughed_conveyor_requirement']='Подтверждено пользователем: транспортёр сделать желобчатым';base['active_trough_candidate']={k:d[k] for k in ['scope','inputs','geometry','profiles','transition_scenarios','load_scenarios','mass_estimate','checks','sources','limitations']};base['active_support_geometry']='Один самостоятельный желобчатый узел R10; полная рама и переходы ещё не интегрированы';base['superseded']={'R09_carrying_roll_support':'Плоские полноширинные ролики исключены из текущей несущей концепции; история','R07_height_interface':'Соединение остаётся кандидатом, прежняя высота посадки/стойки не действует для R10','R08_R09_traction_tension':'Условные расчёты плоской схемы; новая желобчатая схема требует пересчёта'};write(O/'00_Исходные_данные/Реестр_исходных_данных_R10.json',base)
items=[]
for pre,name,q in [('SHELL_','Оболочка Ø76/70×150',3),('CARRIER_','Держатель подшипника: габарит Ø76/52×15',6),('SHAFT_','Ось Ø25×200 без ступеней и фиксации',3),('FORK_','Открытая вилка60×45×8',6),('CROSSBEAM','Поперечина40×40×3 длиной700',1),('CENTRE_POST_','Центральная опорная пластина60×20×8',2),('INNER_WEDGE_','Внутренняя наклонная опорная пластина, толщина8',2),('OUTER_PEDESTAL_','Наружная наклонная опорная пластина, толщина8',2)]:
 names=[n for n in d['expected_bodies'] if n.startswith(pre)];assert len(names)==q
 items.append(dict(name=name,quantity=q,unit='шт.',model_bodies=names,mass_total_kg=sum(d['expected_bodies'][n]['volume_m3'] for n in names)*7850,mass_basis='Геометрия и условная плотность стали7850; масса заготовки не определена',material_status='Ст3 для рамы по ТЗ, марка/исполнение деталей и допуски не выпущены',status='изготавливаемый геометрический кандидат'))
items.append(dict(name='Подшипник25×52×15;6205-2RSH габаритный кандидат',quantity=6,unit='шт.',model_bodies=[n for n in d['expected_bodies'] if n.startswith('BEARING_ENV_')],catalog_mass_estimate_each_kg=.13,mass_total_kg=.78,status='Покупной кандидат: ресурс/водостойкость/уплотнения не утверждены; CAD только сплошной габарит'))
assert abs(sum(x['mass_total_kg'] for x in items)-d['mass_estimate']['station_estimate_kg'])<1e-9
write(O/'08_EBOM_MBOM/ЛТ500_Предварительный_EBOM_желобчатой_опоры_R10.json',dict(revision='R10',scope='Одна трёхроликовая станция;2 справочные трубы и огибающая ленты исключены; количество станций всего транспортёра не определено',items=items,total_mass_estimate_kg=sum(x['mass_total_kg'] for x in items),missing_parts=['осевая и противовращательная фиксация осей, удержание от подъёма','уплотнения/крышки/ступени/посадки','сварные соединения и крепление к общей раме','регулировка и элементы замены роликов'],status='PRELIMINARY NOT FOR MANUFACTURING'))
write(O/'11_Испытания_и_контроль/Проверка_расчёта_желоба_R10.json',dict(revision='R10',**d['checks'],transition_model='Прямолинейная нижняя граница; не допускаемая деформация',roller_load_model='Два отдельных условных контактных подхода; реальные доли неизвестны',shaft_model='Вся нормальная сила и вес в центре192мм, E200000; без контактов/осевого усилия/ресурса',limits=d['limitations']))
f=O/'02_Расчеты/ЛТ500_Расчёт_желобчатой_ленты_R10.xlsx';qa=json.loads((B/'work/trough_xlsx_qa_r10.json').read_text(encoding='utf8'));assert 'matched 0 entries' in (B/'work/trough_xlsx_scan_r10.txt').read_text(encoding='utf8');ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};count=0;sheets=0;errors=[];uncached=[]
with zipfile.ZipFile(f) as z:
 assert z.testzip() is None
 for n in z.namelist():
  if n.startswith('xl/worksheets/sheet') and n.endswith('.xml'):
   root=ET.fromstring(z.read(n));sheets+=1
   for x in root.findall('.//m:c',ns):
    if x.attrib.get('t')=='e':errors.append([n,x.attrib.get('r')])
    if x.find('m:f',ns) is not None:
     count+=1
     if x.find('m:v',ns) is None:uncached.append([n,x.attrib.get('r')])
 assert sheets==2 and not errors and not uncached
qa.update(all_sheets_visually_checked=True,preview_regions_checked=5,formula_scan_zero_matches=True,formula_count=count,exported_cached_errors=errors,formulas_without_cached_values=uncached);write(O/'11_Испытания_и_контроль/Проверка_расчётной_книги_R10.json',qa)
pdf=O/'01_Техническое_задание/ЛТ500_Желобчатый_вариант_R10.pdf';assert len(PdfReader(pdf).pages)==4;write(O/'11_Испытания_и_контроль/Проверка_отчёта_R10.json',dict(pages=4,all_pages_rendered_and_visually_checked=True,native_CAD_preview_checked=True,status='NOT FOR MANUFACTURING'))
ip=Path(str(f)+'.inspect.ndjson')
if ip.exists():shutil.move(ip,B/'work/trough_export_r10.inspect.ndjson')
status=f'''ЛТ500 — ЖЕЛОБЧАТАЯ КОНЦЕПЦИЯ R10, 04.10.2026
ПРЕДВАРИТЕЛЬНО — НЕ ДЛЯ ИЗГОТОВЛЕНИЯ

Начать с 01_Техническое_задание/ЛТ500_Желобчатый_вариант_R10.pdf.
Требование пользователя: сделать транспортёр желобчатым.
Лента500 мм; полная длина10 000 мм; продольный спуск1–2°.
В прототипе приняты1,5° и желоб20°; толщина8 мм условна.
Средняя часть нейтрального слоя180 мм, крылья160+160 мм.
Проекция нейтральной ширины480,702 мм; верх края выше середины54,482 мм.
При условной привязке середины к800 мм край около854,5 мм в местной плоскости.

Сохранён самостоятельный нативный узел SolidWorks:
3 роликаØ76×180, осиØ25×200, опорный пролёт192 мм;
6 габаритов подшипников25×52×15,6 открытых вилок60×45×8;
поперечина40×40×3 длиной700 мм,6 опорных пластин толщиной8 мм;
2 справочные трубы100×50×3 длиной600 мм;
огибающая профиля ленты длиной180 мм с идеальными изломами.
Это одна многотельная деталь, не сборка и не полный транспортёр.
Удержание осей, ступени/посадки, крышки, уплотнения, швы и регулировка отсутствуют.
Изломы огибающей не являются реальным изгибом выбранной ленты.

Интерфейс от посадки трубы до середины верха ленты230 мм вместо170 мм в R09.
Высоту стоек общей рамы требуется пересмотреть; новые длины не выпущены.
Геометрия соединенияR07 остаётся кандидатом, прежняя высотная привязка не действует.
Плоские несущие роликиR09 заменены текущей желобчатой концепцией; R09 — история.
Плоская обратная ветвь и концевые/переходные опоры ещё не разработаны.
Фактическая общая ширина700 мм является кандидатом рамы, не подтверждённым габаритом.

Площадь до края по верхней поверхности идеального профиля:
{d['profiles'][0]['ideal_no_heap_area_m2']:.6f} м² без горки/запаса;
{d['profiles'][0]['area_with_20mm_freeboard_m2']:.6f} м² при условном запасе20 мм.
Для q30 кг/м до края требуется плотность около1677 кг/м³.
Плотность и скорость неизвестны: грузовместимость/производительность не подтверждены.
Q=3,6·A·ρ·v т/ч; q=A·ρ кг/м.
Нагрузочный ориентир30 кг/м + qB5 кг/м + одна порция15 кг — условное сочетание.
Порция15 кг не умножается на количество решёток; удар и пятно неизвестны.

Резерв переходов750 мм с каждого конца — компоновочный сценарий.
Его нельзя считать разрешённой длиной по будущей ленте.
Прямолинейная нижняя граница удлинения края при Lt750 мм0,274%.
Это не допускаемая деформация и не переходные напряжения.
Подачу предлагается разместить после завершения перехода.
Барабанные оси и полезная длина ещё не определены из полных10 м.

P при обычном шаге750 мм404,386 Н, при шаге250 мм232,828 Н без удара/веса роликов.
Доли поперечной нагрузки неизвестны. Рассмотрены4 условных распределения.
Две отдельные модели: только нормальный контакт либо вертикальная результирующая
с разложением на нормальную и осевую части. Они не складываются.
Схема оси с силой в середине пролёта192 мм:σ14,205 МПа,δ0,017455 мм;
E200000 МПа условно; допускаемые, ослабления, контакты/ресурс не проверены.
Расчёты тяги/натяженияR08/R09 плоской схемы не подтверждают новый желоб.
Требуется пересчитать трение, массу/инерцию, переходы, натяжение и провис полос.

CAD34 тела: объёмы/центры масс каждого независимо сверены до/после открытия.
Перестроение и сохранение выполнены; ошибки/предупреждения0.
561×2=1122 операции пересечения: объёмов больше1e-10 м³ нет.
Это не подтверждает контакты, допуски, прочность и сборочные сопряжения.
SolidWorks Simulation не выполнялась.
EBOM одной станции: металл{d['mass_estimate']['metal_without_refs_bearing_envelopes_belt_kg']:.6f} кг
+6 подшипников по0,13 кг = {d['mass_estimate']['station_estimate_kg']:.6f} кг.
Справочные трубы, огибающая ленты и недостающие детали в массу не включены.
Число станций всей машины ещё не назначено.

Excel2 листа: геометрия/переходы/4 распределения/оценка оси сверены;
проверены неизвестные плотность/скорость, примерные1000кг/м³ и0,2м/с,
угол30° и запас выше края. Исходные восстановлены, ошибки формул0.
Все5 областей книги и4 страницыPDF просмотрены. Microsoft Excel не тестировался.

Следующий этап: подбор желобчатой ленты; переходные опоры/барабаны;
общая компоновка и корректировка высот стоек;
натяжение/тяга/инерция, поперечина/пластины/швы и фиксация/ресурс роликов.
Рабочие чертежи, допуски, технология, DXF, УП и производственная MBOM не выпущены.
'''
(O/'СТАТУС_КОМПЛЕКТА_R10.txt').write_text(status,encoding='utf8');(O/'СТАТУС_КОМПЛЕКТА.txt').write_text(status,encoding='utf8')
keep={'Первоначальное_задание.txt','ЛТ500_Предварительный_проект_R02.pdf','ЛТ500_Расчётный_паспорт_R02.xlsx','ЛТ500_MASTER_исходная_геометрия_R01.SLDPRT','master_creation_report_R01.json','master_inspection_report_R01.json','СТАТУС_КОМПЛЕКТА.txt'}
files=[p for p in O.rglob('*') if p.is_file() and ((any(r in p.name for r in ['R03','R04','R05','R06','R07','R08','R09','R10']) and not p.name.startswith('Реестр_файлов')) or p.name in keep)]
registry=[dict(path=str(p.relative_to(O)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(files)];write(O/'Реестр_файлов_R10.json',dict(revision='R10',active_CAD='Один самостоятельный желобчатый узелR10; прежняя геометрияR01–R09 сохранена как история или частичные кандидаты',status='PRELIMINARY NOT FOR MANUFACTURING',files=registry));(O/'Реестр_файлов_R10.txt').write_text('\n'.join(f"{x['path']} | {x['bytes']} байт | SHA256 {x['sha256']}" for x in registry),encoding='utf8');files.extend([O/'Реестр_файлов_R10.json',O/'Реестр_файлов_R10.txt']);archive=B/'outputs/Ленточный_транспортер_ЛТ500_R10.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'Ленточный_транспортер/'+str(p.relative_to(O)).replace('\\','/'))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for x in registry:assert hashlib.sha256(z.read('Ленточный_транспортер/'+x['path'].replace('\\','/'))).hexdigest()==x['sha256']
 print(json.dumps(dict(files=len(z.namelist()),bytes=archive.stat().st_size,integrity='passed',xlsx_formula_count=count)))
