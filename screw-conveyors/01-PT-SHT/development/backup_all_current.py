from pathlib import Path
import json,shutil
base=Path('outputs/Шнек 1 — параметрическая модель').resolve()
r=json.loads((base/'recovered_assembly_check.json').read_text(encoding='utf-8'))
backup=base/'snapshots'/'20261004-all-interferences-before';files=[Path(r['assembly'])]+[Path(p) for p in r['paths']]
for path in files:
 target=backup/path.relative_to(base)
 if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
print('backup files',len(files))
