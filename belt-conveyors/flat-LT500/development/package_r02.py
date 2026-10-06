from pathlib import Path
import json,hashlib,zipfile,shutil
b=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');o=b/'outputs/Ленточный_транспортер'
for src,dst in [('calculation_qa_r02.json','Расчётные_проверки_R02.json'),('extra_qa_r02.json','Проверки_пуск_и_балка_R02.json')]:shutil.copy2(b/'work'/src,o/'11_Испытания_и_контроль'/dst)
inspect=o/'02_Расчеты/ЛТ500_Расчётный_паспорт_R02.xlsx.inspect.ndjson'
if inspect.exists():shutil.move(inspect,b/'work/xlsx_export_r02.inspect.ndjson')
status='''ЛТ500 — ПРЕДВАРИТЕЛЬНЫЙ ПРОЕКТ R02, 04.10.2026
НЕ ДЛЯ ИЗГОТОВЛЕНИЯ

Начать с 01_Техническое_задание/ЛТ500_Предварительный_проект_R02.pdf.
Последнее уточнение пользователя имеет приоритет:
15 кг — пиковая масса отходов в ОДНОЙ ЗОНЕ ЗАГРУЗКИ.
Прежняя трактовка как суммарной разовой порции отменена.
Масса одновременно падающего сброса и частота подачи НЕ определены.
Длина нагруженного пятна неизвестна; вопрос пользователю задан отдельно.

R02 содержит реестр 42 параметров, Excel 5 листов и PDF 5 страниц.
Проверки формул прошли в Artifact Tool; нативный Excel не тестировался.
Все листы и страницы визуально проверены.
Формулы удара не используют местные 15 кг как массу падения:
масса падающего сброса задана отдельной пустой ячейкой.
Рама: раздельные нагрузки q=30 кг/м и P=15*g.
Их сумма — только условная комбинация для сравнения:
совместность и отсутствие двойного учёта пока не подтверждены.
Собственный вес, удар, прочность реального профиля не проверены.
300 кг — условные q*10 м из исходного задания, не вывод из местных 15 кг.

Исходная геометрия CAD R01 включена без изменений:
2 эскиза, 12 уравнений, без твёрдых тел и рабочей сборки.
Проверки создания/перестроения/сохранения и повторного открытия из R01
сохранены; новых CAD-изменений в R02 нет.
Временно: 10000 мм как горизонтальная габаритная проекция,
1,5° вниз, 800 мм в середине; монтажные отметки не утверждены.

Полный тяговый расчёт и подбор ленты/привода/барабанов/роликов/рамы,
рабочая сборка, чертежи, DXF, EBOM/MBOM и УП остаются открытыми.
Для окончательного выпуска нужны данные потока, зоны загрузки,
включений, опор, основания и проверка применимых норм и защит.
'''
(o/'СТАТУС_КОМПЛЕКТА_R02.txt').write_text(status,encoding='utf8');(o/'СТАТУС_КОМПЛЕКТА.txt').write_text(status,encoding='utf8')
files=[p for p in o.rglob('*') if p.is_file() and (('R02' in p.name and not p.name.startswith('Реестр_файлов')) or p.name=='Первоначальное_задание.txt' or (p.parent.name=='03_Модели_SolidWorks' and 'R01' in p.name))]
registry=[{'path':str(p.relative_to(o)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]
(o/'Реестр_файлов_R02.json').write_text(json.dumps({'revision':'R02','status':'PRELIMINARY NOT FOR MANUFACTURING','cad_revision_retained':'R01','files':registry},ensure_ascii=False,indent=2),encoding='utf8')
(o/'Реестр_файлов_R02.txt').write_text('\n'.join(f"{r['path']} | {r['bytes']} байт | SHA256 {r['sha256']}" for r in registry),encoding='utf8')
files.extend([o/'Реестр_файлов_R02.json',o/'Реестр_файлов_R02.txt'])
archive=b/'outputs/Ленточный_транспортер_ЛТ500_R02.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'Ленточный_транспортер/'+str(p.relative_to(o)).replace('\\','/'))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for r in registry:assert hashlib.sha256(z.read('Ленточный_транспортер/'+r['path'].replace('\\','/'))).hexdigest()==r['sha256']
 print(json.dumps({'zip_files':len(z.namelist()),'bytes':archive.stat().st_size,'integrity':'passed'}))
