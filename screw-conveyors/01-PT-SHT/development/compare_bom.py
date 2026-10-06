from pathlib import Path
from collections import Counter
import glob
import json
import re
import openpyxl

source = glob.glob(r"C:\Users\adm\Desktop\РАЗРАБОТКА\01.PT.SHT.01.20.00.00 СБ *\*\*.xlsx")[0]
rows = list(openpyxl.load_workbook(source, read_only=True, data_only=True).active.values)[1:]
assembly = json.loads(Path('work/audit_current_assembly.json').read_text(encoding='utf-8'))

def key(value):
    text = re.sub(r'\s+', ' ', str(value or '')).strip().casefold()
    code = re.match(r'(pt\.sht\.[\d.]+(?:-\d+)?)', text)
    if code:
        return code.group(1)
    text = re.sub(r'\s+а2$', '', text)
    text = re.sub(r'\s+a2$', '', text)
    return re.sub(r'\s+', '', text)

counts = Counter(key(Path(item['path']).stem) for item in assembly['components'])
names = {}
for item in assembly['components']:
    names[key(Path(item['path']).stem)] = Path(item['path']).stem

items = []
for row in rows:
    position, name, material, blank, mass, production, quantity = row
    k = key(name)
    items.append({'position': position, 'designation': name, 'quantity_bom': quantity,
                  'quantity_model': counts.pop(k, 0), 'key': k})

result = {
    'bom_path': source,
    'bom_positions': len(items),
    'bom_quantity_total_including_subassemblies': sum(int(x['quantity_bom']) for x in items),
    'assembly_occurrences': assembly['component_count'],
    'quantity_mismatches': [x for x in items if x['quantity_bom'] != x['quantity_model']],
    'unlisted_in_bom': [{'designation': names[k], 'quantity_model': v} for k, v in counts.items()],
}
Path('work/compare_bom.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: result[k] for k in ('bom_positions','bom_quantity_total_including_subassemblies','assembly_occurrences')}, ensure_ascii=True))
print(json.dumps(result['quantity_mismatches'], ensure_ascii=True))
print(json.dumps(result['unlisted_in_bom'], ensure_ascii=True))
