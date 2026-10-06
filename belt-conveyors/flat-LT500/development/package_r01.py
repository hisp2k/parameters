from pathlib import Path
import json,hashlib,zipfile,shutil
b=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');o=b/'outputs/Ленточный_транспортер'
for src,dst in [('calculation_qa_r01.json','Расчётные_проверки_R01.json'),('extra_qa_r01.json','Проверки_пуск_и_балка_R01.json')]:shutil.copy2(b/'work'/src,o/'11_Испытания_и_контроль'/dst)
inspect=o/'02_Расчеты/ЛТ500_Расчётный_паспорт_R01.xlsx.inspect.ndjson'
if inspect.exists():shutil.move(inspect,b/'work/xlsx_export_r01.inspect.ndjson')
status='''ЛТ500 — ПРЕДВАРИТЕЛЬНЫЙ ПРОЕКТ R01, 04.10.2026
НЕ ДЛЯ ИЗГОТОВЛЕНИЯ

Начать с 01_Техническое_задание/ЛТ500_Предварительный_проект_R01.pdf.
R01 имеет приоритет над R00 по текущим данным и требованиям.
В R01: реестр 40 исходных параметров, 5 листов расчётов, PDF 5 страниц,
параметрическая исходная деталь SolidWorks и протоколы фактических проверок.

CAD: MASTER_SIDE и MASTER_BELT_PLAN, 12 уравнений, без твёрдых тел.
Это геометрическая основа для следующей стадии, не рабочая сборка.
Длины глобальных параметров заданы в мм; угол — числом в градусах
с явным переводом в радианы внутри tan. Размеры API проверены в метрах.
Временно: 10000 мм как горизонтальная габаритная проекция,
наклон 1,5°, отметка 800 мм в середине. Оси барабанов не назначены.

Проверены: изменение угла 1°/2°, ширины 520/500, сохранение,
повторное открытие, перестроение и восстановление исходных размеров.
Проверены формулы Excel и их пересчёт в Artifact Tool; в Microsoft Excel
тестирование не выполнялось. Все листы книги и страницы PDF просмотрены.

Не выполнены: полный тяговый расчёт, натяжение, окончательная прочность,
ресурс подшипников, выбор ленты/привода/барабанов/сечений,
рабочая сборка и чертежи, DXF, EBOM/MBOM, CAM и УП.
Припуски, режимы станков, опоры и анкеры для изготовления не назначены.
Применимость нормативов и защитных решений до выпуска подлежит проверке.

Нагруженный повторный пуск включён; остаточная масса не согласована.
Порция 15 кг принята суммарной; площадь и частота сброса неизвестны.
Отсутствующие числовые данные оставлены пустыми; это не нули.
300 кг — материал на условных 10 м, не полный вес оборудования.
Сравнение пролётов включает статическую дополнительную порцию 15 кг,
но исключает собственный вес и удар; профили этим расчётом не утверждены.
'''
(o/'СТАТУС_КОМПЛЕКТА_R01.txt').write_text(status,encoding='utf8');(o/'СТАТУС_КОМПЛЕКТА.txt').write_text(status,encoding='utf8')
files=[p for p in o.rglob('*') if p.is_file() and (('R01' in p.name and not p.name.startswith('Реестр_файлов')) or p.name=='Первоначальное_задание.txt')]
registry=[{'path':str(p.relative_to(o)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]
(o/'Реестр_файлов_R01.json').write_text(json.dumps({'revision':'R01','status':'PRELIMINARY NOT FOR MANUFACTURING','files':registry},ensure_ascii=False,indent=2),encoding='utf8')
(o/'Реестр_файлов_R01.txt').write_text('\n'.join(f"{r['path']} | {r['bytes']} байт | SHA256 {r['sha256']}" for r in registry),encoding='utf8')
files.extend([o/'Реестр_файлов_R01.json',o/'Реестр_файлов_R01.txt'])
archive=b/'outputs/Ленточный_транспортер_ЛТ500_R01.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'Ленточный_транспортер/'+str(p.relative_to(o)).replace('\\','/'))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for r in registry:
  assert hashlib.sha256(z.read('Ленточный_транспортер/'+r['path'].replace('\\','/'))).hexdigest()==r['sha256']
 print(json.dumps({'zip_files':len(z.namelist()),'bytes':archive.stat().st_size,'integrity':'passed'},ensure_ascii=False))
