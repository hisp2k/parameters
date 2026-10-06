"""Produce traceable occurrence reconciliation and preliminary purchase register."""
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import sys

sys.path.append(r'C:\Users\adm\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages')
import openpyxl
import win32com.client as win32

root = Path(__file__).resolve().parents[1]
project = root / 'outputs' / 'Шнек 1 — параметрическая модель'
audit = root / 'outputs' / 'Шнек 1 — аудит производственного комплекта'
source = next(root.glob("outputs/Шнек 1 —*/CAD/PT.SHT.01.20.00.00 СБ 'Шнек 1'.SLDASM"))
bom_path = audit / '05_BOM — проектная правка.xlsx'
source_folder = Path(r"C:\Users\adm\Desktop\РАЗРАБОТКА\01.PT.SHT.01.20.00.00 СБ 'Шнек 1'\01.PT.SHT.01.20.00.00 СБ 'Шнек 1'")
now = datetime.now(timezone(timedelta(hours=4))).strftime('%d.%m.%Y %H:%M UTC+4')


def key(raw: str) -> str:
    text = Path(raw).name if '\\' in raw else raw
    for extension in ('.SLDPRT', '.SLDASM'):
        if text.upper().endswith(extension):
            text = text[:-len(extension)]
    text = text.upper().replace('А2', 'A2').replace('Х', 'X').replace('×', 'X')
    code = re.match(r'^(?:01\.)?(PT\.SHT\.\d+(?:\.\d+)+(?:-\d+)?)', text)
    if code:
        return code.group(1)
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'A2$', '', text)
    return text.replace('DIN127B', 'DIN127')


rows = list(openpyxl.load_workbook(bom_path, read_only=True, data_only=True).active.values)
bom_count = Counter()
procurement = []
for position, row in enumerate(rows[1:], 1):
    name, material, qty = str(row[1] or '').strip(), str(row[2] or '').strip(), int(row[6] or 0)
    bom_count[key(name)] += qty
    if not name.startswith('PT.SHT.'):
        procurement.append((position, name, material or 'не указан', qty))

sw = win32.GetActiveObject('SldWorks.Application')
doc = sw.GetOpenDocumentByName(str(source))
if doc is None:
    spec = sw.GetOpenDocSpec(str(source))
    spec.DocumentType = 2
    spec.Silent = True
    doc = sw.OpenDoc7(spec)
components = doc.GetComponents(False) or []
cad_count = Counter(key(c.GetPathName) for c in components)
missing = Counter(Path(c.GetPathName).name for c in components
                  if c.GetPathName and not Path(c.GetPathName).is_file())
local_names = {p.name.casefold() for p in (project / 'CAD').rglob('*') if p.is_file()}
provided_names = {p.name.casefold() for p in source_folder.rglob('*') if p.is_file()}
discrepancies = [(name, bom_count[name], cad_count[name])
                 for name in sorted(bom_count.keys() | cad_count.keys()) if bom_count[name] != cad_count[name]]
active_config = doc.ConfigurationManager.ActiveConfiguration.Name

lines = [
    '# Сверка проектной BOM и дерева CAD', '',
    f'**Проверка:** {now}. **Конфигурация:** `{active_config}`. **Объект:** `{source.name}`.', '',
    f'- Строк проектной BOM: **{len(rows)-1}**; сумма количеств: **{sum(bom_count.values())}**.',
    f'- Вхождений в дереве SolidWorks: **{len(components)}**; разных нормализованных ключей: **{len(cad_count)}**.',
    f'- Построчных расхождений обозначения/количества после нормализации: **{len(discrepancies)}**.',
    f'- Неразрешённых ссылок: **{sum(missing.values())} вхождений / {len(missing)} имён файлов**.', '',
    'Метод: для обозначенных деталей и сборок сравнивался код `PT.SHT...`; для стандартных изделий — имя без пробелов, суффикса A2 и различий написания `DIN 127 B`/`DIN127` для одной выбранной шайбы. Нормализация не проверяет форму, материал, конфигурацию детали или пригодность замен. Совпадение общей суммы не подменяет эту построчную проверку.', '',
]
if discrepancies:
    lines += ['| Ключ | BOM | CAD |', '|---|---:|---:|']
    lines += [f'| {name} | {b} | {c} |' for name,b,c in discrepancies]
    lines.append('')
lines += [
    '## Неразрешённые пути', '',
    '| Файл из ссылки сборки | Вхождений | Совпадающее имя в рабочем CAD | В указанной папке |',
    '|---|---:|---|---|',
]
for name, qty in sorted(missing.items()):
    lines.append(f'| {name} | {qty} | {"да" if name.casefold() in local_names else "нет"} | {"да" if name.casefold() in provided_names else "нет"} |')
lines += ['', 'Сборка остаётся частичной. Внешний путь к «Сбрасывателю» пока не перепривязан; наличие файла с тем же именем не доказывает геометрическую идентичность без отдельной проверки.', '']
(audit / '08_Сверка BOM и CAD.md').write_text('\n'.join(lines), encoding='utf-8')

purchase = [
    '# Плановая ведомость покупных и стандартных изделий', '',
    f'**Источник:** `05_BOM — проектная правка.xlsx`, {now}. **Объём:** одно изделие «Шнек 1»; количество на заказ не задано.', '',
    'Это перечень для уточнения закупки, не заказ поставщику. Значения материала переписаны из BOM и не подтверждены паспортами изделий. Для позиций со стандартами DIN необходимо сверить точное исполнение, действующую редакцию и применимость.', '',
    '| Поз. BOM | Наименование | Материал в BOM | Шт. на изделие |',
    '|---:|---|---|---:|',
]
for position, name, material, qty in procurement:
    purchase.append(f'| {position} | {name} | {material} | {qty} |')
purchase += ['', f'**Итого строк:** {len(procurement)}. Суммировать штуки разных номенклатур как одно изделие нельзя.', '',
             'До закупки требуется подтвердить: исполнение шайбы М8 DIN 127 B A2, замены отсутствующего крепежа, паспорт привода и подшипников, материал уплотнений, количество изделий на заказ и редакцию спецификации.', '']
(audit / '09_Плановая закупка.md').write_text('\n'.join(purchase), encoding='utf-8')
print(f'config={active_config}; bom={len(rows)-1}; occurrences={len(components)}; discrepancies={len(discrepancies)}; missing={sum(missing.values())}/{len(missing)}; purchase_rows={len(procurement)}')
