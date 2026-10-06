from pathlib import Path
import json,hashlib,zipfile,shutil
from pypdf import PdfReader
from xml.etree import ElementTree as ET
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер'
d=json.loads((B/'work/reinforce_r06.json').read_text(encoding='utf8'));base=json.loads((O/'00_Исходные_данные/Реестр_исходных_данных_R05.json').read_text(encoding='utf8'));base['revision']='R06';base['reinforced_support_candidate']=d;base['active_support_geometry']='R06: наружные пластины и щеки под седлами; R04 и R05 сохранены как история';base['status']='ПРЕДВАРИТЕЛЬНЫЙ ПРОЕКТ — УСИЛЕНИЕ ОПОРНОЙ ЗОНЫ — НЕ ДЛЯ ИЗГОТОВЛЕНИЯ'
(O/'00_Исходные_данные/Реестр_исходных_данных_R06.json').write_text(json.dumps(base,ensure_ascii=False,indent=2),encoding='utf8')
cp=O/'11_Испытания_и_контроль/Проверка_CAD_усиления_R06.json';c=json.loads(cp.read_text(encoding='utf8'));assert c['ok'] and c['save_errors']==0 and c['save_warnings']==0;c['preview_visually_checked']=True;cp.write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf8')
qa=json.loads((B/'work/reinforce_xlsx_qa_r06.json').read_text(encoding='utf8'));qa['visual_review_all_three_sheets_six_images']=True;assert 'matched 0 entries' in (B/'work/reinforce_xlsx_scan_r06.txt').read_text(encoding='utf8');qa['formula_error_scan_zero_matches']=True;f=O/'02_Расчеты/ЛТ500_Расчёт_усиления_R06.xlsx';ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(f) as z:
 assert z.testzip() is None;count=0;errors=[];sheets=0
 for name in z.namelist():
  if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):
   root=ET.fromstring(z.read(name));sheets+=1;count+=len(root.findall('.//m:f',ns));errors.extend([c.attrib.get('r') for c in root.findall('.//m:c',ns) if c.attrib.get('t')=='e'])
 assert sheets==3 and not errors
qa['exported_formula_count']=count;qa['exported_cached_errors']=errors
(O/'11_Испытания_и_контроль/Проверка_расчётной_книги_R06.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf8')
pdf=O/'01_Техническое_задание/ЛТ500_Усиление_опорной_зоны_R06.pdf';assert len(PdfReader(pdf).pages)==4
(O/'11_Испытания_и_контроль/Проверка_отчёта_R06.json').write_text(json.dumps({'pages':4,'all_pages_rendered_and_visually_checked':True,'native_SolidWorks_preview_included':True,'status':'PRELIMINARY NOT FOR MANUFACTURING'},ensure_ascii=False,indent=2),encoding='utf8')
inspect=Path(str(f)+'.inspect.ndjson')
if inspect.exists():shutil.move(inspect,B/'work/reinforce_export_r06.inspect.ndjson')
status='''ЛТ500 — ПРЕДВАРИТЕЛЬНЫЙ ПРОЕКТ R06, 04.10.2026
НЕ ДЛЯ ИЗГОТОВЛЕНИЯ

Начать с 01_Техническое_задание/ЛТ500_Усиление_опорной_зоны_R06.pdf.
R06 дополняет исходную концепцию R02, балки R03, реакции R04 и седла R05.
Предыдущие документы включены как история и основания расчётов.

Новая работа: наружное усиление под каждым седлом — горизонтальная
пластина 120x80x12 мм и две щеки 6x80x80 мм. Итого 2 пластины и 4 щеки.
Центры щёк ±53 мм от оси опоры, внутренние грани x=±50 мм.
Поперечина 80x100x4 и седла 100x60 мм, t минимум 10 мм, сохранены.
При уклоне 1,5° средняя стойка 518,691 мм, на 12 мм короче R05.
Масса опоры при 7850 кг/м3 — 18,079 кг (+2,913 кг к R05),
с четырьмя справочными рельсами по 300 мм — 26,000 кг.

Модель SLDPRT: 13 тел опоры +4 справочных отрезка рельса.
Это фиксированная многотельная деталь, не сборка транспортёра;
материал в CAD не назначен, связи с Excel нет. В модели нет швов,
фиксаторов седла и рельса, крепежа стыка, анкеров. Рабочий зазор стыка
не назначен, справочные торцы совпадают. Высота ленты 800 мм по середине,
размер 170 мм до опирания рельса и оси 200/2600/5000/7400/9800 мм
остаются компоновочными допущениями до выбора концевых узлов и роликов.

В CAD проверены варианты 1°, 1,5°, 2°, сохранён 1,5°. Для всех 17 тел
сверены независимые объёмы/центры масс, плоскости и площади граней.
136 пар в каждом варианте плюс 136 после повторного открытия:
544 операции пересечения временных копий, объёмных пересечений
выше 1e-10 м3 не найдено. Сохранение/открытие/перестроение успешны,
ошибок/предупреждений сохранения 0/0. Предыдущий документ восстановлен
без изменения признака сохранения. Это геометрия, не проверка прочности.

Расчёт: условная огибающая R04 1418,07 Н плюс вес двух седел,
двух пластин и четырёх щёк — 1458,08 Н целиком на одну площадку.
Совместность q=30 кг/м и местной массы 15 кг неизвестна.
Пуск, удар, ролики и действительные усилия ленты не включены.
Полоса пластины b=38 мм, t=12 мм, опирание по осям щёк L=106 мм:
σ=42,367 МПа, δ=0,03306 мм. Чувствительность L=112 мм:
σ=44,766 МПа, δ=0,03900 мм. E=200000 МПа — допущение.
Предлагаемый частичный ориентир δ≤0,05 мм не является нормативом.
36 случаев толщины/пролёта/ширины сверены с Python.
Центральный прогиб сверён независимой двухэлементной балочной FE-моделью.
Равновесие и максимум изгиба проверены для 1001 положения силы.
Седло пересчитано: полоса t минимум 10 мм, b=38 мм, L=100 мм,
δ=0,04796 мм, σ=57,556 МПа. Контактное давление не решено.
Вклад верхней стенки трубы и совместность слоёв исключены из пути
нагрузки через наружные щеки; этот путь требует реальных соединений.

Номинальная модель швов одной щеки: вся P, эксцентриситет 3 мм,
две вертикальные линии по 54 мм на прямой грани трубы высотой 64 мм.
Катет-кандидат 3 мм, расчётное горло 2,121 мм:
τ=6,364 МПа, σ=2,121 МПа, эквивалентное номинальное 11,226 МПа.
Катет и длина не являются утверждёнными производственными размерами.
Материал, нормативная база, допускаемые сопротивления, WPS, усталость,
местная прочность стенок трубы/щек и соединение пластины со щеками
не проверены. Швы в CAD отсутствуют. Допускаемые напряжения не назначены.
SolidWorks Simulation и трёхмерный контактный расчёт не выполнялись.

При 2° скатывающая составляющая условной P — 50,89 Н,
без неизвестной тяги ленты. Фиксаторы седла и рельса ещё не рассчитаны;
мокрое трение не используется для удержания. Продольные силы могут
определять стык, связи и анкеры, поэтому их нельзя заменить 50,89 Н.

Толстая цельная труба 80x100x8 в отдельной модели R05 верхней стенки
δ≈0,04018 мм, при замене 700 мм поперечины добавляет около 6,18 кг.
Наружное усиление легче по массе, но добавляет детали и сварку.
Полная прочность двух альтернатив этим сравнением не подтверждена.

Excel: 3 листа, 36 случаев и основные результаты сверены с Python,
угол/E/пустое E/катет пересчитаны, исходные данные восстановлены,
формульных ошибок нет. Microsoft Excel не использовался для теста.
PDF 4 страницы и все три листа визуально проверены.

Заготовки усиления, способ резки, припуски, допуски, последовательность
сварки/монтажа, WPS, покрытие и контроль ещё не выпущены.
Лазер 3 кВт не подтверждает резку 12 мм без реальных данных машины.
Рабочие чертежи, DXF, окончательные маршруты, EBOM/MBOM и УП не созданы.
Остаются фиксация седел, продольный стык, общая рама/связи/анкеры,
бетон, нагрузки роликов/ленты/барабанов, тяга/натяжение, скорость и поток.
'''
(O/'СТАТУС_КОМПЛЕКТА_R06.txt').write_text(status,encoding='utf8');(O/'СТАТУС_КОМПЛЕКТА.txt').write_text(status,encoding='utf8')
keep={'Первоначальное_задание.txt','ЛТ500_Предварительный_проект_R02.pdf','ЛТ500_Расчётный_паспорт_R02.xlsx','ЛТ500_MASTER_исходная_геометрия_R01.SLDPRT','master_creation_report_R01.json','master_inspection_report_R01.json','СТАТУС_КОМПЛЕКТА.txt'}
files=[p for p in O.rglob('*') if p.is_file() and ((any(r in p.name for r in ['R03','R04','R05','R06']) and not p.name.startswith('Реестр_файлов')) or p.name in keep)]
registry=[{'path':str(p.relative_to(O)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]
(O/'Реестр_файлов_R06.json').write_text(json.dumps({'revision':'R06','status':'PRELIMINARY NOT FOR MANUFACTURING','files':registry},ensure_ascii=False,indent=2),encoding='utf8')
(O/'Реестр_файлов_R06.txt').write_text('\n'.join(f"{r['path']} | {r['bytes']} байт | SHA256 {r['sha256']}" for r in registry),encoding='utf8');files.extend([O/'Реестр_файлов_R06.json',O/'Реестр_файлов_R06.txt'])
archive=B/'outputs/Ленточный_транспортер_ЛТ500_R06.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'Ленточный_транспортер/'+str(p.relative_to(O)).replace('\\','/'))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for r in registry:assert hashlib.sha256(z.read('Ленточный_транспортер/'+r['path'].replace('\\','/'))).hexdigest()==r['sha256']
 print(json.dumps({'files':len(z.namelist()),'bytes':archive.stat().st_size,'integrity':'passed','xlsx_formula_count':count}))
