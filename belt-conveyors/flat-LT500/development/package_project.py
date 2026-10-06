from pathlib import Path
import json, hashlib, zipfile
from pypdf import PdfReader
import xml.etree.ElementTree as ET
base=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2')
root=base/'outputs/Ленточный_транспортер'
sidecar=root/'02_Расчеты/ЛТ500_Расчётный_паспорт_R00.xlsx.inspect.ndjson'
if sidecar.exists(): sidecar.replace(base/'work/xlsx_export_inspect.ndjson')
files=[]
for file in sorted(root.rglob('*')):
 if file.is_file() and not file.name.startswith('Реестр_файлов'):
  files.append({'designation':{'pdf':'ЛТ500.ТЗ','xlsx':'ЛТ500.РП','json':'ЛТ500.ИД'}.get(file.suffix[1:],'ЛТ500.ИСТ'),'path':file.relative_to(root).as_posix(),'revision':'R00','status':'ИСТОЧНИК' if file.name=='Первоначальное_задание.txt' else 'ПРЕДВАРИТЕЛЬНО — НЕ ДЛЯ ИЗГОТОВЛЕНИЯ','size_bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
for ext in ['json','txt']:
 files.append({'designation':'ЛТ500.РФ','path':'Реестр_файлов_R00.'+ext,'revision':'R00','status':'РЕЕСТР ПРЕДВАРИТЕЛЬНОГО КОМПЛЕКТА','sha256':None,'hash_note':'Собственный реестр не хешируется во избежание самоссылки.'})
manifest={'project':'ЛТ500','date':'2026-10-04','revision':'R00','release_status':'ПРЕДВАРИТЕЛЬНАЯ КОНЦЕПЦИЯ — НЕ ДЛЯ ИЗГОТОВЛЕНИЯ','files':files,'not_issued':['Нативная модель SolidWorks','Расчёт Simulation','Производственные чертежи','DXF и развёртки','Полные технологические маршруты','Управляющие программы','Производственные EBOM и MBOM','Закупочная спецификация','Электрическая схема','Численные критерии испытаний'],'verification':{'xlsx':'Формулы, исходные значения, пересчёт с временными входами, границы ноль/пусто и изображения проверены в Artifact Tool. В Microsoft Excel не проверялось.','pdf':'7 страниц отрендерены Poppler и проверены визуально.','cad':'Приложение обнаружено; доступ к API не подтверждён, COM 0x8002802B.'}}
(root/'Реестр_файлов_R00.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
lines=['ЛТ500 R00 от 04.10.2026','ПРЕДВАРИТЕЛЬНАЯ КОНЦЕПЦИЯ — НЕ ДЛЯ ИЗГОТОВЛЕНИЯ','']
for record in files: lines.extend([record['designation']+'   '+record['revision'],record['path'],record['status'],''])
lines+=['НЕ ВЫПУЩЕНО:']+manifest['not_issued']
(root/'Реестр_файлов_R00.txt').write_text('\n'.join(lines),encoding='utf8')
pdf=next(root.rglob('*.pdf')); assert len(PdfReader(pdf).pages)==7
xlsx=next(root.rglob('*.xlsx'))
with zipfile.ZipFile(xlsx) as z:
 assert z.testzip() is None
 ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
 sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
 c=sheet.find('.//s:c[@r="B8"]/s:v',ns); assert abs(float(c.text)-300)<1e-9
 assert sheet.find('.//s:c[@r="B17"]/s:f',ns) is not None
archive=base/'outputs/Ленточный_транспортер_ЛТ500_R00.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 z.write(root,root.name+'/')
 for file in sorted(root.rglob('*')): z.write(file,file.relative_to(root.parent).as_posix()+('/' if file.is_dir() else ''))
with zipfile.ZipFile(archive) as z: assert z.testzip() is None
print(json.dumps({'files':len(files),'pdf_pages':7,'zip_bytes':archive.stat().st_size,'archive_integrity':'passed'},ensure_ascii=False))
