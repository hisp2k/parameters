"""Compare the current active assembly occurrence counts with the corrected BOM."""
from collections import Counter
from pathlib import Path
import re
import sys

sys.path.append(r'C:\Users\adm\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages')
import openpyxl
import win32com.client as win32

project = Path(sys.argv[1])
bom = Path(sys.argv[2])
assembly = next((project / 'CAD').glob("*20.00.00*Шнек 1*.SLDASM"))


def key(raw: str) -> str:
    text = Path(raw).name if '\\' in raw else raw
    for extension in ('.SLDPRT', '.SLDASM'):
        if text.upper().endswith(extension):
            text = text[:-len(extension)]
    text = text.upper().replace('А2', 'A2').replace('Х', 'X').replace('×', 'X')
    match = re.match(r'^(?:01\.)?(PT\.SHT\.\d+(?:\.\d+)+(?:-\d+)?)', text)
    if match:
        return match.group(1)
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'A2$', '', text)
    text = text.replace('DIN127B', 'DIN127')
    return text


sheet = openpyxl.load_workbook(bom, read_only=True, data_only=True).active
bom_counts = Counter()
names = {}
for row in list(sheet.values)[1:]:
    name, qty = row[1], row[6]
    if name:
        bom_counts[key(str(name))] += int(qty or 0)
        names[key(str(name))] = str(name)

sw = win32.GetActiveObject('SldWorks.Application')
doc = sw.GetOpenDocumentByName(str(assembly))
if doc is None:
    spec = sw.GetOpenDocSpec(str(assembly))
    spec.DocumentType = 2
    spec.Silent = True
    doc = sw.OpenDoc7(spec)
components = doc.GetComponents(False) or []
cad_counts = Counter(key(c.GetPathName) for c in components)
print('BOM_ROWS', len(list(sheet.values))-1, 'BOM_COUNT', sum(bom_counts.values()))
print('CAD_COMPONENTS', len(components), 'CAD_KEYS', len(cad_counts))
for identifier in sorted(bom_counts.keys() | cad_counts.keys()):
    if bom_counts[identifier] != cad_counts[identifier]:
        print('MISMATCH', identifier, 'BOM', bom_counts[identifier], 'CAD', cad_counts[identifier], names.get(identifier,''))
