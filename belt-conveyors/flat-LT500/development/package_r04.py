from pathlib import Path
import json,hashlib,zipfile,shutil
from pypdf import PdfReader
from xml.etree import ElementTree as ET
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер'
d=json.loads((B/'work/support_r04.json').read_text(encoding='utf8'));base=json.loads((O/'00_Исходные_данные/Реестр_исходных_данных_R03.json').read_text(encoding='utf8'));base['revision']='R04';base['support_candidate']=d;base['status']='ПРЕДВАРИТЕЛЬНЫЙ ПРОЕКТ — ОПОРЫ И СТЫК — НЕ ДЛЯ ИЗГОТОВЛЕНИЯ'
(O/'00_Исходные_данные/Реестр_исходных_данных_R04.json').write_text(json.dumps(base,ensure_ascii=False,indent=2),encoding='utf8')
qa=json.loads((B/'work/support_xlsx_qa_r04.json').read_text(encoding='utf8'));qa['visual_review_all_sheets']=True;qa['formula_error_scan_zero_matches']=True
file=O/'02_Расчеты/ЛТ500_Расчёт_опор_R04.xlsx';ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(file) as z:
 assert z.testzip() is None
 formulas=0;cachedErrors=[]
 for n in z.namelist():
  if n.startswith('xl/worksheets/sheet') and n.endswith('.xml'):
   root=ET.fromstring(z.read(n));formulas+=len(root.findall('.//m:f',ns));cachedErrors.extend([c.attrib.get('r') for c in root.findall('.//m:c',ns) if c.attrib.get('t')=='e'])
 assert formulas>80 and not cachedErrors
qa['exported_xlsx_formula_count']=formulas;qa['exported_cached_errors']=cachedErrors
(O/'11_Испытания_и_контроль/Проверка_расчётной_книги_R04.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf8')
pdf=O/'01_Техническое_задание/ЛТ500_Опоры_и_стык_R04.pdf';assert len(PdfReader(pdf).pages)==4
(O/'11_Испытания_и_контроль/Проверка_отчёта_R04.json').write_text(json.dumps({'pages':4,'all_pages_rendered_and_visually_checked':True,'native_SolidWorks_preview_included':True,'status':'PRELIMINARY NOT FOR MANUFACTURING'},ensure_ascii=False,indent=2),encoding='utf8')
inspect=Path(str(file)+'.inspect.ndjson')
if inspect.exists():shutil.move(inspect,B/'work/support_export_r04.inspect.ndjson')
status='''ЛТ500 — ПРЕДВАРИТЕЛЬНЫЙ ПРОЕКТ R04, 04.10.2026
НЕ ДЛЯ ИЗГОТОВЛЕНИЯ

Начать с 01_Техническое_задание/ЛТ500_Опоры_и_стык_R04.pdf.
R04 дополняет расчёт балок R03 и исходную концепцию R02; они включены
в архив как основания. R03 — прототип балок, R04 — отдельная опора.
Сборка полного транспортёра, ролики, лента и барабаны ещё не построены.

Новая схема: пять предполагаемых осей 200/2600/5000/7400/9800 мм,
два непрерывных двухпролётных модуля со стыком над общей опорой.
Пролёт 2400 мм, отступы 200 мм — компоновочные допущения.
При равномерной нагрузке промежуточная реакция 5wL/4:
на 25% больше, чем по схеме двух отдельных шарнирных пролётов.
Для местных 15 кг проверены 1001 позиция и равновесие реакций.
Трубы длиной 5000 мм R03 не превращены в окончательные детали:
длина нового каркаса около 9600 мм требует увязки с концевыми узлами.

Прототип опоры: труба 80x100x4 L700, две стойки 50x50x3 L542,
две сплошные плиты 120x150x8 без отверстий. Это 5 тел в SLDPRT,
не SLDASM. Геометрия фиксирована, материал CAD не назначен.
Объём 0,001808610 м3 и масса при 7850 кг/м3 14,198 кг.
Сверены объёмы и центры масс каждого тела; сохранение, повторное
открытие, перестроение и нативный вид проверены.

Условная вертикальная огибающая q+трубы+15 кг: 1418,07 Н на раму.
Вся сила в середине верхней балки даёт δ=0,0246 мм, σ=6,525 МПа.
15 кг — масса в одной зоне, не подтверждённая масса падающего сброса.
Сумма q и 15 кг условная, возможен двойной учёт материала.
Пять максимумов не действуют одновременно. Допускаемые напряжения
не назначены; полная прочность и устойчивость НЕ подтверждены.

Высоты: условно 800 мм до ленты по середине, 170 мм от ленты
до верха опоры. Это интерфейсное допущение, роликами не подтверждено.
В CAD верхняя балка горизонтальна. Для наклонного каркаса нужна
согласованная наклонная опорная поверхность: на 100 мм при 2°
перепад 3,49 мм. Номинальные площадки по 50 мм не доказывают контакт.

Excel R04: три листа, значения сверены с Python, проверен пересчёт E,
пустое E, угол, добавленная масса и восстановление исходных значений.
Нет формульных ошибок; формулы сохранены в XLSX.
Microsoft Excel не использовался для проверки. PDF 4 страницы
и все листы визуально просмотрены.

Не рассчитаны массы остальных узлов, натяжение и пусковая тяга,
горизонтальные силы, связи, общая устойчивость, швы, болты и анкеры,
местная прочность и бетон. Simulation не выполнялась.
Болты/накладки стыка, рабочие чертежи, DXF, EBOM/MBOM и УП
ещё не выпущены. Для полного расчёта нужны скорость/поток,
данные ленты и роликов, свойства отходов и нагрузка подачи.
'''
(O/'СТАТУС_КОМПЛЕКТА_R04.txt').write_text(status,encoding='utf8');(O/'СТАТУС_КОМПЛЕКТА.txt').write_text(status,encoding='utf8')
keep={'Первоначальное_задание.txt','ЛТ500_Предварительный_проект_R02.pdf','ЛТ500_Расчётный_паспорт_R02.xlsx','ЛТ500_MASTER_исходная_геометрия_R01.SLDPRT','master_creation_report_R01.json','master_inspection_report_R01.json'}
files=[p for p in O.rglob('*') if p.is_file() and ((('R04' in p.name or 'R03' in p.name) and not p.name.startswith('Реестр_файлов')) or p.name in keep)]
registry=[{'path':str(p.relative_to(O)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]
(O/'Реестр_файлов_R04.json').write_text(json.dumps({'revision':'R04','status':'PRELIMINARY NOT FOR MANUFACTURING','references':['Support R04','Rail prototype R03','Concept R02','Skeleton R01'],'files':registry},ensure_ascii=False,indent=2),encoding='utf8')
(O/'Реестр_файлов_R04.txt').write_text('\n'.join(f"{r['path']} | {r['bytes']} байт | SHA256 {r['sha256']}" for r in registry),encoding='utf8');files.extend([O/'Реестр_файлов_R04.json',O/'Реестр_файлов_R04.txt'])
archive=B/'outputs/Ленточный_транспортер_ЛТ500_R04.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'Ленточный_транспортер/'+str(p.relative_to(O)).replace('\\','/'))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for r in registry:assert hashlib.sha256(z.read('Ленточный_транспортер/'+r['path'].replace('\\','/'))).hexdigest()==r['sha256']
 print(json.dumps({'files':len(z.namelist()),'bytes':archive.stat().st_size,'integrity':'passed','xlsx_formulas':formulas}))
