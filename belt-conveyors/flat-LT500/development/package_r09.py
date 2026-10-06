from pathlib import Path
import json,hashlib,zipfile,shutil
from xml.etree import ElementTree as ET
from pypdf import PdfReader
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер';d=json.loads((B/'work/loading_r09.json').read_text(encoding='utf8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
cpath=O/'11_Испытания_и_контроль/Проверка_CAD_роликов_загрузки_R09.json';c=json.loads(cpath.read_text(encoding='utf8'));assert c['ok'];c['preview_visually_checked']=True;write(cpath,c)
base=json.loads((O/'00_Исходные_данные/Реестр_исходных_данных_R08.json').read_text(encoding='utf8'));base['revision']='R09';base['loading_support_candidate']={k:d[k] for k in ['scope','inputs','cases','geometry','mass_estimates','checks','sources','limitations']};base['active_support_geometry']='Средний узелR07; новый самостоятельный участок частых роликовR09, ещё не интегрирован в раму';write(O/'00_Исходные_данные/Реестр_исходных_данных_R09.json',base)
items=[]
for pre,name,q in [('SHELL_','Оболочка Ø76/70×510',4),('CARRIER_','Держатель подшипника, габарит Ø76/52×15',8),('SHAFT_','Стационарная ось Ø25×620, без ступеней/фиксации',4),('FORK_','Опорная вилка60×45×8, открытый пазR12,5',8)]:
 names=[n for n in d['expected_bodies'] if n.startswith(pre)];assert len(names)==q
 items.append(dict(name=name,quantity=q,model_bodies=names,mass_total_kg=sum(d['expected_bodies'][n]['volume_m3'] for n in names)*7850,status='изготавливаемый геометрический кандидат; материал/допуски/швы не выпущены'))
items.append(dict(name='Подшипник25×52×15, габаритный кандидат6205-2RSH',quantity=8,model_bodies=[n for n in d['expected_bodies'] if n.startswith('BEARING_ENV_')],catalog_mass_estimate_each_kg=.13,mass_total_kg=1.04,status='покупной кандидат; исполнение/ресурс/уплотнения не утверждены; CAD представляет сплошной габарит'))
assert abs(sum(x['mass_total_kg'] for x in items)-24.85632147753505)<1e-9
write(O/'08_EBOM_MBOM/ЛТ500_Предварительный_EBOM_роликов_загрузки_R09.json',dict(revision='R09',scope='4 роликовые станции одного типового участка; справочные трубы исключены',items=items,total_mass_estimate_kg=sum(x['mass_total_kg'] for x in items),missing_parts=['фиксаторы оси от подъёма/вращения/осевого перемещения','крышки и уплотнения','осевые упоры и посадочные ступени','регулировка роликов и соединение с общей рамой'],status='PRELIMINARY NOT FOR MANUFACTURING'))
write(O/'11_Испытания_и_контроль/Проверка_расчёта_загрузки_R09.json',dict(revision='R09',**d['checks'],shaft_midpoint_independent_analytic_check=True,limits='Нет подтверждения допускаемых напряжений/контактов/усталости/основания'))
f=O/'02_Расчеты/ЛТ500_Расчёт_опор_загрузки_R09.xlsx';qa=json.loads((B/'work/loading_xlsx_qa_r09.json').read_text(encoding='utf8'));assert 'matched 0 entries' in (B/'work/loading_xlsx_scan_r09.txt').read_text(encoding='utf8');ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};count=0;sheets=0;errors=[];uncached=[]
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
qa.update(all_sheets_visually_checked=True,preview_regions_checked=4,formula_scan_zero_matches=True,formula_count=count,exported_cached_errors=errors,formulas_without_cached_values=uncached);write(O/'11_Испытания_и_контроль/Проверка_расчётной_книги_R09.json',qa)
pdf=O/'01_Техническое_задание/ЛТ500_Опоры_зон_загрузки_R09.pdf';assert len(PdfReader(pdf).pages)==4;write(O/'11_Испытания_и_контроль/Проверка_отчёта_R09.json',dict(pages=4,all_pages_rendered_and_visually_checked=True,native_CAD_preview_checked=True,status='NOT FOR MANUFACTURING'))
ip=Path(str(f)+'.inspect.ndjson')
if ip.exists():shutil.move(ip,B/'work/loading_export_r09.inspect.ndjson')
status='''ЛТ500 — ПРЕДВАРИТЕЛЬНЫЙ ПРОЕКТ R09, 04.10.2026
НЕ ДЛЯ ИЗГОТОВЛЕНИЯ

Начать с 01_Техническое_задание/ЛТ500_Опоры_зон_загрузки_R09.pdf.
Новый самостоятельный участок частых роликовR09:
4роликаØ76, рабочая длина540мм, шаг250мм, ось25×620мм,
8габаритов подшипников25×52×15,8открытых вилок60×45×8.
Две справочные трубы100×50×3 длиной1100мм, уклон1,5°.
R07 остаётся геометрией среднего опорного узла; R09не интегрирован.

Предлагаемый интерфейс170мм от посадки трубы до верха ленты,
толщина ленты8мм условна. Центр ролика124мм, верх оболочки162мм.
Зазор ролик/внутренняя боковая плоскость трубы5мм номинально.
Фиксация оси, удержание от подъёма/вращения, ступени/посадки,
крышки/уплотнения, швы и регулировка отсутствуют.
Открытый паз не является готовым безопасным креплением оси.
Ролик и подшипник — габаритные кандидаты, не утверждённый заказ.

q30кг/м + qB5кг/м + единственная15кг масса,1,5°, провис1%:
точечный случай Tзагрузка4,748кН, Tобычный6,893кН.
Частые ролики только под подачей не распределяют отходы.
При движении компактной15кг порции обычный шаг750мм
сохраняет определяющую потребность6,893кН изR08.
Пятно0,25/0,5/0,75/1м — условные распределённые случаи;
при пятне0,5м глобальная потребность5,668кН.
Реальное пятно неизвестно: меньшие значения не назначены.
Концевые нагрузкиR08около14кН не уменьшены.

Статические нормальные нагрузки от ленты: ролик загрузки232,83Н,
переход250/750мм318,61Н, обычный750мм404,39Н.
Вес роликов и чувствительность к локальной динамике рассмотрены
отдельно. Множители15кг1/2/3 не являются установленным ударом;
высота падения неизвестна. Не умножаем15кг на3решётки.

Ось стационарная: пролёт600мм, нагрузки на37,5/562,5мм,
E200000МПа; осевой/касательный изгиб, фиксация, ступени не включены.
27балочных случаев81узел, поперечная масса±250/0мм:
максимумδ0,179мм, σ13,729МПа в частичной схеме.
Схема всей нагрузки в центре пролёта вExcelотдельная,δдо0,888мм.
Эти результаты не объединяются. Допускаемые напряжения не заданы.
Оболочка проверена отдельно на центральную силу со своим весом;
держатели, вилки, швы, контакты, усталость и ресурс открыты.
Simulation не выполнялась.

CAD34тела: геометрия каждого независимо сверена до/после открытия,
ошибки/предупреждения сохранения0, перестроение выполнено.
1122операции пересечения561парыдо/после: объёмов>1e-10м³ нет.
Это не проверка сборочных допусков/контактной прочности/кинематики.
Сплошные габаритные кольца не моделируют подшипник и его массу.
EBOM4станций: металл23,816кг +8подшипниковпо0,13=24,856кг,
без справочных труб, недостающей фиксации/уплотнений/швов.
Массу и инерцию всей системы роликов ещё надо обновить вR08.

Excel2листа:5случаевпровиса/реакций и9оценокроликасверены,
пустое/нулевое/0,5мпятно, нулевая масса и пустое/половинноеE
проверены, исходные восстановлены, ошибки формул0.
10сочетанийпровиса/реакций проверены численным интегрированием.
Все страницыPDF4и2листа просмотрены; MicrosoftExcelне тестирован.

Далее: фиксация оси и уплотнения, регулировка/замена ролика;
лента/рабочая скорость/падение и реальные зоны загрузки;
полная схема станций и обновление массы/инерции/общей рамы;
концевые рамы/натяжитель/привод/валы/подшипники/анкеры.
Предыдущие размерыR02–R06 — история; действующий среднийузелR07.
Производственный выпуск, материалы/швы/покрытие/DXF/маршруты/УП открыты.
'''
(O/'СТАТУС_КОМПЛЕКТА_R09.txt').write_text(status,encoding='utf8');(O/'СТАТУС_КОМПЛЕКТА.txt').write_text(status,encoding='utf8')
keep={'Первоначальное_задание.txt','ЛТ500_Предварительный_проект_R02.pdf','ЛТ500_Расчётный_паспорт_R02.xlsx','ЛТ500_MASTER_исходная_геометрия_R01.SLDPRT','master_creation_report_R01.json','master_inspection_report_R01.json','СТАТУС_КОМПЛЕКТА.txt'}
files=[p for p in O.rglob('*') if p.is_file() and ((any(r in p.name for r in ['R03','R04','R05','R06','R07','R08','R09']) and not p.name.startswith('Реестр_файлов')) or p.name in keep)]
registry=[dict(path=str(p.relative_to(O)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(files)];write(O/'Реестр_файлов_R09.json',dict(revision='R09',active_CAD='средний узелR07 + самостоятельная зона роликовR09',status='PRELIMINARY NOT FOR MANUFACTURING',files=registry));(O/'Реестр_файлов_R09.txt').write_text('\n'.join(f"{x['path']} | {x['bytes']} байт | SHA256 {x['sha256']}" for x in registry),encoding='utf8');files.extend([O/'Реестр_файлов_R09.json',O/'Реестр_файлов_R09.txt']);archive=B/'outputs/Ленточный_транспортер_ЛТ500_R09.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'Ленточный_транспортер/'+str(p.relative_to(O)).replace('\\','/'))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for x in registry:assert hashlib.sha256(z.read('Ленточный_транспортер/'+x['path'].replace('\\','/'))).hexdigest()==x['sha256']
 print(json.dumps(dict(files=len(z.namelist()),bytes=archive.stat().st_size,integrity='passed',xlsx_formula_count=count)))
