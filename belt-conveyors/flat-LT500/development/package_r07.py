from pathlib import Path
import json,hashlib,zipfile,shutil
from pypdf import PdfReader
from xml.etree import ElementTree as ET
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер';d=json.loads((B/'work/joint_r07.json').read_text(encoding='utf8'))
base=json.loads((O/'00_Исходные_данные/Реестр_исходных_данных_R06.json').read_text(encoding='utf8'));base['revision']='R07';base['joint_and_seat_fixation_candidate']=d;base['active_support_geometry']='R07: отверстия, втулки, крепёж и пазы. Все предыдущие геометрии — история, не актуальные производственные размеры';base['status']='ПРЕДВАРИТЕЛЬНЫЙ ПРОЕКТ — НЕ ДЛЯ ИЗГОТОВЛЕНИЯ';(O/'00_Исходные_данные/Реестр_исходных_данных_R07.json').write_text(json.dumps(base,ensure_ascii=False,indent=2),encoding='utf8')
cp=O/'11_Испытания_и_контроль/Проверка_CAD_крепления_и_стыка_R07.json';c=json.loads(cp.read_text(encoding='utf8'));assert c['ok'] and c['save_errors']==0;c['preview_visually_checked']=True;c['preview_recovered_by_explicit_document_activation']=True;cp.write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf8')
f=O/'02_Расчеты/ЛТ500_Расчёт_крепления_и_стыка_R07.xlsx';qa=json.loads((B/'work/joint_xlsx_qa_r07.json').read_text(encoding='utf8'));assert 'matched 0 entries' in (B/'work/joint_xlsx_scan_r07.txt').read_text(encoding='utf8');qa['formula_scan_zero_matches']=True;qa['all_sheets_visually_checked']=True;ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(f) as z:
 assert z.testzip() is None;count=0;errors=[];sheets=0
 for n in z.namelist():
  if n.startswith('xl/worksheets/sheet') and n.endswith('.xml'):
   root=ET.fromstring(z.read(n));sheets+=1;count+=len(root.findall('.//m:f',ns));errors.extend([x.attrib.get('r') for x in root.findall('.//m:c',ns) if x.attrib.get('t')=='e'])
 assert sheets==2 and not errors
qa['exported_formula_count']=count;qa['exported_cached_errors']=errors;(O/'11_Испытания_и_контроль/Проверка_расчётной_книги_R07.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf8')
pdf=O/'01_Техническое_задание/ЛТ500_Крепление_седел_и_стык_R07.pdf';assert len(PdfReader(pdf).pages)==4;(O/'11_Испытания_и_контроль/Проверка_отчёта_R07.json').write_text(json.dumps({'pages':4,'all_pages_rendered_and_visually_checked':True,'native_preview_checked':True,'status':'NOT FOR MANUFACTURING'},ensure_ascii=False,indent=2),encoding='utf8')
ip=Path(str(f)+'.inspect.ndjson')
if ip.exists():shutil.move(ip,B/'work/joint_export_r07.inspect.ndjson')
items=[('Поперечина 80×100×4, L700',1,['CROSSBEAM'],'изготавливаемая'),('Стойка 50×50×3, L504,691',2,['LEG_LEFT','LEG_RIGHT'],'изготавливаемая'),('Опорная плита 120×150×8',2,['PLATE_LEFT','PLATE_RIGHT'],'изготавливаемая'),('Седло 100×80, t минимум24; отверстия Ø10,5',2,['SEAT_LEFT','SEAT_RIGHT'],'изготавливаемая'),('Пластина 160×120×12',2,['CAP_LEFT','CAP_RIGHT'],'изготавливаемая'),('Щека 6×80×80',4,[n for n in d['expected_bodies'] if n.startswith('WEB_')],'изготавливаемая'),('Направляющая 160×100×6; Ø21/паз33×21; 2×Ø10,5',4,[n for n in d['expected_bodies'] if n.startswith('GUIDE_')],'изготавливаемая')]
for typ,kind,desc in [('MODULE','M10','M10×120'),('SEAT','M6','M6×110')]:
 bolt=[n for n in d['expected_bodies'] if typ in n and (n.startswith('SHAFT_') or n.startswith('HEAD_'))];items.append(('Болт '+desc,4,bolt,'покупной кандидат, поставщик/исполнение не утверждены'))
 items.append(('Втулка '+('Ø20/11×97' if typ=='MODULE' else 'Ø10/6,5×97'),4,[n for n in d['expected_bodies'] if n.startswith('SLEEVE_') and typ in n],'изготавливаемая'))
 items.append(('Гайка '+kind,4,[n for n in d['expected_bodies'] if n.startswith('NUT_') and typ in n],'покупной кандидат, стопорение не утверждено'))
 items.append(('Шайба '+('Ø24/11×2' if typ=='MODULE' else 'Ø18/6,5×2'),8,[n for n in d['expected_bodies'] if n.startswith('WASHER_') and typ in n],'условная геометрия, тип/поставщик не утверждены'))
out=[]
for j,(name,q,names,status) in enumerate(items,1):out.append(dict(position=j,name=name,quantity=q,status=status,model_bodies=names,mass_sum_kg=sum(d['expected_bodies'][n]['volume_m3'] for n in names)*7850))
assert abs(sum(x['mass_sum_kg'] for x in out)-d['support_with_fasteners_mass_kg'])<1e-9
(O/'08_EBOM_MBOM').mkdir(exist_ok=True)
(O/'08_EBOM_MBOM/ЛТ500_Предварительный_EBOM_узла_R07.json').write_text(json.dumps({'revision':'R07','scope':'Одна средняя поперечная опора с креплением; справочные рельсы исключены из EBOM','status':'PRELIMINARY NOT FOR MANUFACTURING','material_and_fastener_specification_unconfirmed':True,'CAD_threads_replaced_by_cylinders':True,'items':out,'support_mass_kg':d['support_with_fasteners_mass_kg']},ensure_ascii=False,indent=2),encoding='utf8')
status=f'''ЛТ500 — ПРЕДВАРИТЕЛЬНЫЙ ПРОЕКТ R07, 04.10.2026
НЕ ДЛЯ ИЗГОТОВЛЕНИЯ

Начать с 01_Техническое_задание/ЛТ500_Крепление_седел_и_стык_R07.pdf.
Предыдущие R02–R06 — история и основания, не актуальные размеры узла.

Новая геометрия: два седла 100x80 мм с минимумом толщины 24 мм,
две пластины 160x120x12 мм, четыре направляющие 160x100x6 мм.
Каждое седло удерживается двумя поперечными втулками Ø10/6,5x97
с M6x110; концы модулей — по одной связи Ø20/11x97 с M10x120.
Всего 4 болта каждого размера, 8 втулок, 8 гаек, 16 шайб.
Крепёж — условная геометрия; поставщик, исполнения и класс неизвестны.
В CAD отсутствуют резьбы, швы, анкеры и сборочные сопряжения.

Номинальные круглые отверстия Ø21 и паз 33x21 дают ход ±6 мм по X.
Втулка 97 мм при наружной ширине направляющих 96 мм оставляет
по 0,5 мм между направляющей и шайбой. Шайбы опираются на торцы
втулки; затяжка не должна зажимать направляющие и тонкие стенки труб.
Это геометрический кандидат: допуски, покрытие, изгиб, затяжка,
стопорение и реальные температурные перемещения не назначены.
Торцевой зазор 12 мм вдоль оси рельса; справочные участки по 294 мм,
не полные модули. У каждого полного модуля нужна одна фиксированная
опора и подходящие подвижные опоры; полная схема пока не выпущена.
Через стык не используется передача момента в расчёте R04;
реальная контактная жесткость всё ещё требует проверки.

Средняя стойка 504,691 мм. Масса опоры с условным крепежом
{d['support_with_fasteners_mass_kg']:.3f} кг (+{d['added_mass_vs_R06_kg']:.3f} кг к R06).
Условная P={d['load_screen_N']:.2f} Н. Ролики, лента, барабаны,
реальные тяговые усилия, пуск и заклинивание в неё не включены.
Совместность q=30 кг/м и местной массы 15 кг неизвестна.
Скатывающая составляющая при 2°={d['gravity_component_2deg_N']:.2f} Н,
не фактическая продольная сила транспортёра.
Пластина, полоса38 мм, t12, L112: σ47,105 МПа, δ0,04103 мм.
Ориентир 0,05 мм — частичная предлагаемая жёсткость, не норматив.
Приведены примеры силы 500/1000/2000/5000 Н и только скатывания.
Расчёт втулок — отдельный изгиб на пролёте 90 мм;
также крайний изгиб голого стержня, двойной срез и смятие.
Распределение нагрузки между втулкой и болтом не решено.
Допускаемые сопротивления и коэффициенты не назначены,
несущая способность на действительные усилия не утверждена.

69 CAD-тел: объёмы/центры масс каждого сверены независимыми формулами
с учётом отверстий/пазов. Сохранение без ошибок/предупреждений,
повторное открытие и перестроение выполнены. Модель фиксирована1,5°.
2346 пар до сохранения +2346 после открытия +2346 в каждом
крайнем положении временных тел: 9384 операции пересечения.
Пересечений больше1e-10 м3 не найдено. Крайние положения dx=±6 мм,
dy=−dx*tan1,5°; исходная модель сохранена в среднем положении.
Для1°/2° аналитически проверен зазор втулки в пазу,
отдельные CAD этих углов R07 не строились. Simulation не выполнялась.
Реальная кинематика, контакты, зазоры по допускам и доступ инструмента
не доказаны отсутствием объёмных пересечений.

Excel: два листа;10 примеров сверены с Python, действительная сила
оставлена пустой («не задано»), отдельно проверены нулевая и1000 Н,
E/2 и пустое E. Исходные данные восстановлены; ошибки формул0.
Microsoft Excel для тестирования не использовался.
PDF4 страницы и оба листа просмотрены; нативный вид CAD проверен.
Предварительный EBOM JSON только на данный узел, без справочных труб.

Следующий определяющий этап — действительные усилия ленты/натяжения,
пуск/остановка/заклинивание с ограничением момента, затем проверка
поперечных соединений и ослабленных отверстиями продольных труб,
усталости, местной прочности, направляющих/втулок/шайб и швов.
Общая рама, поперечина, связи, анкеры и бетон требуют обновления
с новой массой. Материал, покрытие, чертежи, DXF, маршруты и УП
не утверждены. Высота ленты800 по середине и интерфейс170 до рельса
остаются допущениями. Скорость и поток отходов пока неизвестны.
'''
(O/'СТАТУС_КОМПЛЕКТА_R07.txt').write_text(status,encoding='utf8');(O/'СТАТУС_КОМПЛЕКТА.txt').write_text(status,encoding='utf8')
keep={'Первоначальное_задание.txt','ЛТ500_Предварительный_проект_R02.pdf','ЛТ500_Расчётный_паспорт_R02.xlsx','ЛТ500_MASTER_исходная_геометрия_R01.SLDPRT','master_creation_report_R01.json','master_inspection_report_R01.json','СТАТУС_КОМПЛЕКТА.txt'}
files=[p for p in O.rglob('*') if p.is_file() and ((any(r in p.name for r in ['R03','R04','R05','R06','R07']) and not p.name.startswith('Реестр_файлов')) or p.name in keep)]
registry=[{'path':str(p.relative_to(O)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]
(O/'Реестр_файлов_R07.json').write_text(json.dumps({'revision':'R07','status':'PRELIMINARY NOT FOR MANUFACTURING','files':registry},ensure_ascii=False,indent=2),encoding='utf8');(O/'Реестр_файлов_R07.txt').write_text('\n'.join(f"{x['path']} | {x['bytes']} байт | SHA256 {x['sha256']}" for x in registry),encoding='utf8');files.extend([O/'Реестр_файлов_R07.json',O/'Реестр_файлов_R07.txt']);archive=B/'outputs/Ленточный_транспортер_ЛТ500_R07.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'Ленточный_транспортер/'+str(p.relative_to(O)).replace('\\','/'))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for x in registry:assert hashlib.sha256(z.read('Ленточный_транспортер/'+x['path'].replace('\\','/'))).hexdigest()==x['sha256']
 print(json.dumps({'files':len(z.namelist()),'bytes':archive.stat().st_size,'integrity':'passed','EBOM_mass_matches':True,'xlsx_formula_count':count}))
