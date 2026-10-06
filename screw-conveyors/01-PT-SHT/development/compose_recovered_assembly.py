"""Compose a uniquely named top assembly from relinked child copies."""
from pathlib import Path
import json
import shutil
import sys

import win32com.client as win32

project = Path(sys.argv[1]).resolve()
new = project / 'CAD_восстановленный'
plan = json.loads((project / 'relink_plan.json').read_text(encoding='utf-8'))
sw = win32.GetActiveObject('SldWorks.Application')

def renamed(path):
    return path.with_name(path.stem + ' — восстановлено' + path.suffix)

affected_codes = ('PT.SHT.01.21.00.00', 'PT.SHT.01.23.00.00', 'PT.SHT.01.25.00.00')
top = next(p for p in map(Path, plan) if 'Шнек 1' in p.name)
top_unique = renamed(top)
if top_unique.exists():
    raise RuntimeError(f'Already exists: {top_unique}')
shutil.copy2(top, top_unique)

for assembly in map(Path, plan):
    if not assembly.name.startswith(affected_codes):
        continue
    replacement = renamed(assembly)
    if replacement.exists():
        raise RuntimeError(f'Already exists: {replacement}')
    shutil.copy2(assembly, replacement)
    before = sw.GetDocumentDependencies2(str(top_unique), False, False, False)
    matches = [old for old in before[1::2] if Path(old).name == assembly.name]
    if len(matches) != 1:
        raise RuntimeError(f'{assembly.name}: expected one reference, found {matches}')
    if not sw.ReplaceReferencedDocument(str(top_unique), matches[0], str(replacement)):
        raise RuntimeError(f'Failed to replace {assembly.name}')
    after = sw.GetDocumentDependencies2(str(top_unique), False, False, False)
    if str(replacement).casefold() not in [str(x).casefold() for x in after[1::2]]:
        raise RuntimeError(f'Replacement not saved: {assembly.name}')
    print('LINKED', assembly.name, '->', replacement.name, flush=True)

all_dependencies = sw.GetDocumentDependencies2(str(top_unique), True, False, False)
paths = [Path(x) for x in all_dependencies[1::2]]
missing = [str(p) for p in paths if not p.is_file()]
print('TOP', top_unique, flush=True)
print('DEPENDENCIES', len(paths), 'MISSING', len(missing), flush=True)
for path in missing:
    print('MISSING_PATH', path, flush=True)
(project / 'recovered_assembly_check.json').write_text(json.dumps({
    'assembly': str(top_unique), 'dependency_count': len(paths), 'missing': missing,
    'paths': list(map(str, paths)),
}, ensure_ascii=False, indent=2), encoding='utf-8')
if missing:
    raise RuntimeError('Recovered assembly still has missing dependencies')
