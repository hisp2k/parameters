from pathlib import Path
import json,hashlib,zipfile,shutil
b=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');o=b/'outputs/Ленточный_транспортер'
base=json.loads((b/'work/project_data_r02.json').read_text(encoding='utf8'));base['revision']='R03';base['structural_candidate']=json.loads((b/'work/structure_r03.json').read_text(encoding='utf8'));base['status']='ПРЕДВАРИТЕЛЬНЫЙ ПРОЕКТ — РАСЧЁТНЫЙ КАНДИДАТ РАМЫ — НЕ ДЛЯ ИЗГОТОВЛЕНИЯ'
(o/'00_Исходные_данные/Реестр_исходных_данных_R03.json').write_text(json.dumps(base,ensure_ascii=False,indent=2),encoding='utf8')
cad=json.loads((b/'work/rail_prototype_report_r03.json').read_text(encoding='utf8'));assert cad['ok'];cad['prior_document_unchanged']=cad.get('previous_before')==cad.get('previous_after');cad.pop('previous_before',None);cad.pop('previous_after',None)
(o/'11_Испытания_и_контроль/Проверка_CAD_балок_R03.json').write_text(json.dumps(cad,ensure_ascii=False,indent=2),encoding='utf8');shutil.copy2(b/'work/frame_xlsx_qa_r03.json',o/'11_Испытания_и_контроль/Проверка_расчётной_книги_R03.json')
inspect=o/'02_Расчеты/ЛТ500_Сравнение_балок_R03.xlsx.inspect.ndjson'
if inspect.exists():shutil.move(inspect,b/'work/frame_export_r03.inspect.ndjson')
status='''ЛТ500 — ПРЕДВАРИТЕЛЬНЫЙ ПРОЕКТ R03, 04.10.2026
НЕ ДЛЯ ИЗГОТОВЛЕНИЯ

Начать с 01_Техническое_задание/ЛТ500_Рама_расчётный_кандидат_R03.pdf.
R03 дополняет базовую концепцию R02. В архиве сохранены PDF и Excel R02
для исходных размеров, расчётных зависимостей потока и требований.
15 кг — пиковая масса в одной зоне, не масса разовой падающей порции.

Новая работа: характеристики трёх труб со скруглениями; 24 случая
упругого вертикального изгиба с собственным весом; чувствительность
к радиусу и толщине; нативный прототип двух балок модуля 5 м.
Расчётный кандидат: 100x50x3 мм, наружный радиус 6, внутренний 3 мм,
межосевое расстояние 600 мм; предлагаемый пролёт не более 2,5 м.
Это проектный вариант для следующей модели, не утверждённое сечение.

Прототип CAD: 2 полых твёрдых тела; длина управляется уравнением.
Сечение и межосевое расстояние фиксированы; изменение этих параметров
не проверено. Объём 0,008408230 м3 и масса при плотности 7850 кг/м3
66,005 кг совпали с аналитикой. Материал в SolidWorks не назначен.
Проверены изменение 4500/5000 мм, перестроение, сохранение,
повторное открытие и объём. Исходный MASTER R01 включён отдельно.
Сборка транспортёра, поперечины, стойки и стыки ещё не построены.

Условная сумма вертикальных нагрузок для кандидата при L=2,5 м, β=1:
прогиб 1,082 мм, напряжение 17,488 МПа.
Включены: q=30 кг/м на одну балку, вес балки, местные 15 кг в середине.
Сумма q и 15 кг служит только сценарием сравнения: возможен двойной учёт.
Не включены: масса остальных узлов, натяжение, удар, кручение,
горизонтальный изгиб, устойчивость, соединения и основание.
Предлагаемые 2 мм прогиба — проектный ориентир; допускаемые напряжения
и коэффициенты прочности не заданы. Полная прочность НЕ подтверждена.

E=200000 МПа — допущение; свойства конкретного Ст3 и паспорт трубы
не получены. Радиусы/толщина в чувствительности не объявлены ГОСТ-допусками.
Опоры: вариант пяти расчётных станций; точные монтажные оси,
концевые отступы, размеры баз и анкеры пока открыты.

Excel R03: 3 листа, 24 случая сверены с Python, проверен пересчёт E
и дополнительной массы. В Microsoft Excel тесты не выполнялись.
PDF 4 страницы и все листы книги визуально проверены.
Simulation, полный тяговый расчёт и окончательный подбор компонентов,
рабочие чертежи, DXF, EBOM/MBOM и УП ещё не выполнены.
'''
(o/'СТАТУС_КОМПЛЕКТА_R03.txt').write_text(status,encoding='utf8');(o/'СТАТУС_КОМПЛЕКТА.txt').write_text(status,encoding='utf8')
keep={'Первоначальное_задание.txt','ЛТ500_Предварительный_проект_R02.pdf','ЛТ500_Расчётный_паспорт_R02.xlsx','ЛТ500_MASTER_исходная_геометрия_R01.SLDPRT','master_creation_report_R01.json','master_inspection_report_R01.json'}
files=[p for p in o.rglob('*') if p.is_file() and (('R03' in p.name and not p.name.startswith('Реестр_файлов')) or p.name in keep)]
registry=[{'path':str(p.relative_to(o)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]
(o/'Реестр_файлов_R03.json').write_text(json.dumps({'revision':'R03','status':'PRELIMINARY NOT FOR MANUFACTURING','references':['Concept R02','Skeleton R01'],'files':registry},ensure_ascii=False,indent=2),encoding='utf8')
(o/'Реестр_файлов_R03.txt').write_text('\n'.join(f"{r['path']} | {r['bytes']} байт | SHA256 {r['sha256']}" for r in registry),encoding='utf8');files.extend([o/'Реестр_файлов_R03.json',o/'Реестр_файлов_R03.txt'])
archive=b/'outputs/Ленточный_транспортер_ЛТ500_R03.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'Ленточный_транспортер/'+str(p.relative_to(o)).replace('\\','/'))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for r in registry:assert hashlib.sha256(z.read('Ленточный_транспортер/'+r['path'].replace('\\','/'))).hexdigest()==r['sha256']
 print(json.dumps({'files':len(z.namelist()),'bytes':archive.stat().st_size,'integrity':'passed'}))
