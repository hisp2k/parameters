import json
from pathlib import Path
import sys

sys.path.insert(0, str((Path('outputs') / 'Шнек 1 — параметрическая модель').resolve()))
import bridge

baseline = json.loads(bridge.STATE.read_text(encoding='utf-8'))['values']
Path('work/baseline_values.json').write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding='utf-8')
candidate = dict(baseline)
candidate['tube_diameter'] += 1
candidate['working_length'] += 10
candidate['screw_diameter'] += 1
candidate['pitch'] += 1
print(json.dumps({'baseline': baseline, 'candidate': candidate}, ensure_ascii=False))
print(json.dumps(bridge.apply(candidate), ensure_ascii=False))
