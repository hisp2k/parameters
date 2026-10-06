from pathlib import Path
import json
from pypdf import PdfReader
root = Path(__file__).resolve().parents[1]
base = root/'outputs'/'История_R10'/'Ленточный_транспортер'
registry = json.loads((base/'00_Исходные_данные'/'Реестр_исходных_данных_R10.json').read_text(encoding='utf-8-sig'))
print('REGISTRY KEYS:', list(registry))
for key, value in registry.items():
    if key not in ['active_trough_candidate']:
        if key in ['inputs','issues','assumptions','clarification_r02','cad_access','superseded']:
            print(key, json.dumps(value,ensure_ascii=False,indent=2))
        else:
            print(key, 'large historical section; keys:',list(value) if isinstance(value,dict) else type(value).__name__)
pdf = next((base/'01_Техническое_задание').glob('*R10.pdf'))
reader = PdfReader(pdf)
texts = [p.extract_text() for p in reader.pages]
(root/'work'/'report_R10_extracted.txt').write_text('\n\n'.join(texts),encoding='utf-8')
print('PDF:',len(reader.pages),'pages')
for p in (base/'11_Испытания_и_контроль').glob('*R10.json'):
    d=json.loads(p.read_text(encoding='utf-8-sig'))
    print('CHECK:',p.name, 'KEYS:',list(d))
    if p.stat().st_size < 18000:
        print(json.dumps(d,ensure_ascii=False,indent=2))
