from pathlib import Path
import json,hashlib,zipfile,shutil
from pypdf import PdfReader
from xml.etree import ElementTree as ET
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер'
d=json.loads((B/'work/seat_r05.json').read_text(encoding='utf8'));base=json.loads((O/'00_Исходные_данные/Реестр_исходных_данных_R04.json').read_text(encoding='utf8'));base['revision']='R05';base['inclined_seat_candidate']=d;base['active_support_geometry']='R05: седла, прямые стойки; исторический горизонтальный прототип R04 сохранён отдельно';base['status']='ПРЕДВАРИТЕЛЬНЫЙ ПРОЕКТ — НАКЛОННОЕ ОПИРАНИЕ — НЕ ДЛЯ ИЗГОТОВЛЕНИЯ'
(O/'00_Исходные_данные/Реестр_исходных_данных_R05.json').write_text(json.dumps(base,ensure_ascii=False,indent=2),encoding='utf8')
qa=json.loads((B/'work/seat_xlsx_qa_r05.json').read_text(encoding='utf8'));qa['visual_review_all_sheets']=True;qa['formula_error_scan_zero_matches']=True;f=O/'02_Расчеты/ЛТ500_Расчёт_седел_R05.xlsx';ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(f) as z:
 assert z.testzip() is None;count=0;errors=[]
 for name in z.namelist():
  if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):
   root=ET.fromstring(z.read(name));count+=len(root.findall('.//m:f',ns));errors.extend([c.attrib.get('r') for c in root.findall('.//m:c',ns) if c.attrib.get('t')=='e'])
 assert count>40 and not errors
qa['exported_formula_count']=count;qa['exported_cached_errors']=errors
(O/'11_Испытания_и_контроль/Проверка_расчётной_книги_R05.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf8')
pdf=O/'01_Техническое_задание/ЛТ500_Наклонное_опирание_и_стык_R05.pdf';assert len(PdfReader(pdf).pages)==4
(O/'11_Испытания_и_контроль/Проверка_отчёта_R05.json').write_text(json.dumps({'pages':4,'all_pages_rendered_and_visually_checked':True,'native_SolidWorks_preview_included':True,'status':'PRELIMINARY NOT FOR MANUFACTURING'},ensure_ascii=False,indent=2),encoding='utf8')
inspect=Path(str(f)+'.inspect.ndjson')
if inspect.exists():shutil.move(inspect,B/'work/seat_export_r05.inspect.ndjson')
status='''ЛТ500 — ПРЕДВАРИТЕЛЬНЫЙ ПРОЕКТ R05, 04.10.2026
НЕ ДЛЯ ИЗГОТОВЛЕНИЯ

Начать с 01_Техническое_задание/ЛТ500_Наклонное_опирание_и_стык_R05.pdf.
R05 дополняет исходную концепцию R02, балки R03 и схему реакций R04.
Ранние документы включены в архив как история и основания.

Новая работа: два наклонных седла 100x60 мм над горизонтальной
поперечиной; минимум толщины 10 мм. При 1,5° центр 11,309 мм,
максимум 12,619 мм. Средняя стойка укорочена до 530,691 мм,
чтобы сохранить плоскость опирания рельса на высоте 630 мм.
Высота ленты 800 мм по середине и размер 170 мм до опирания рельса
остаются допущениями до выбора роликов. Оси 200/2600/5000/7400/9800
не являются утверждёнными монтажными координатами.

CAD — многотельный SLDPRT: 7 тел опоры и 4 справочных участка
рельса по 300 мм. Не сборка транспортёра. Масса опоры при 7850 кг/м3
15,167 кг; вместе с короткими рельсами 23,087 кг.
В модели нет креплений седла, болтов/накладок стыка, швов и анкеров.
Торцы справочных балок совпадают без назначенного рабочего зазора.

Проверены отдельные CAD-варианты 1°, 1,5°, 2°; сохранён 1,5°.
Для всех 11 тел каждого варианта сверены объёмы и центры масс.
По реальным плоским граням проверены нормали, совпадение плоскостей
рельсов/седел и площади. 55 пар в каждом варианте + 55 после
повторного открытия: 220 операций пересечения временных копий.
Объёмных пересечений выше 1e-10 м3 не найдено. Сохранение,
повторное открытие и перестроение успешны. Материал CAD не назначен,
геометрия фиксирована, связи с Excel нет. Simulation не выполнялась.

Расчёт: вся условная огибающая R04 1418,07 Н плюс вес двух седел
направлена на одно седло. Совместность q и 15 кг неизвестна.
Сравнены минимальные толщины 6/8/10 мм. По частичной модели полосы
при 10 мм прогиб 0,02785 мм; предлагаемый ориентир 0,05 мм
не является нормативом и не подтверждает прочность узла.

Новая определяющая проверка: местная работа верхней стенки трубы.
При условном распределении по ширине 60 мм получены σ=111,603 МПа
и δ=0,24562 мм; в чувствительности к ширине/пролёту значения выше.
Одномерный ориентир не заменяет контактный расчёт и не доказывает
прочность. Формула прогиба сверена независимой виртуальной работой
по 200000 участкам. Допускаемые напряжения не назначены.

При 2° скатывающая составляющая условной нагрузки около 49,85 Н,
без неизвестной тяги ленты. Требуется механическая фиксация;
удержание трением мокрых поверхностей не принимается.

Предварительная заготовка седла 104x64x16 мм — только кандидат.
Не проверены припуски, инструмент, оснастка, допуски и режимы.
Лазерная резка 16 мм, постпроцессор и УП не подтверждены/не созданы.
Рабочие чертежи, DXF, EBOM/MBOM и окончательные маршруты не выпущены.

Excel R05: 2 листа, формулы и кэш без ошибок, сравнение с Python,
пересчёт угла/массы/высот и E/пустого E выполнены.
Microsoft Excel не использовался для тестирования. PDF 4 страницы
и все листы визуально просмотрены.
Полная прочность, устойчивость, натяжение, пуск, связи, сварка,
крепёж, анкеры и бетон пока не проверены. Поток и скорость неизвестны.
'''
(O/'СТАТУС_КОМПЛЕКТА_R05.txt').write_text(status,encoding='utf8');(O/'СТАТУС_КОМПЛЕКТА.txt').write_text(status,encoding='utf8')
keep={'Первоначальное_задание.txt','ЛТ500_Предварительный_проект_R02.pdf','ЛТ500_Расчётный_паспорт_R02.xlsx','ЛТ500_MASTER_исходная_геометрия_R01.SLDPRT','master_creation_report_R01.json','master_inspection_report_R01.json'}
files=[p for p in O.rglob('*') if p.is_file() and ((any(r in p.name for r in ['R03','R04','R05']) and not p.name.startswith('Реестр_файлов')) or p.name in keep)]
registry=[{'path':str(p.relative_to(O)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]
(O/'Реестр_файлов_R05.json').write_text(json.dumps({'revision':'R05','status':'PRELIMINARY NOT FOR MANUFACTURING','files':registry},ensure_ascii=False,indent=2),encoding='utf8')
(O/'Реестр_файлов_R05.txt').write_text('\n'.join(f"{r['path']} | {r['bytes']} байт | SHA256 {r['sha256']}" for r in registry),encoding='utf8');files.extend([O/'Реестр_файлов_R05.json',O/'Реестр_файлов_R05.txt'])
archive=B/'outputs/Ленточный_транспортер_ЛТ500_R05.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'Ленточный_транспортер/'+str(p.relative_to(O)).replace('\\','/'))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for r in registry:assert hashlib.sha256(z.read('Ленточный_транспортер/'+r['path'].replace('\\','/'))).hexdigest()==r['sha256']
 print(json.dumps({'files':len(z.namelist()),'bytes':archive.stat().st_size,'integrity':'passed','xlsx_formula_count':count}))
