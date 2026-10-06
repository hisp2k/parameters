"""Create a separate working CAD tree and exact reference migration plan."""
from pathlib import Path
import json
import shutil
import sys

import win32com.client as win32

project = Path(sys.argv[1]).resolve()
old = project / 'CAD'
new = project / 'CAD_восстановленный'
assert old.is_dir() and not new.exists()
source_top = next(old.glob("*Шнек 1*.SLDASM"))
sw = win32.GetActiveObject('SldWorks.Application')
top = sw.GetOpenDocumentByName(str(source_top))
assert top is not None and not top.GetSaveFlag

shutil.copytree(old, new)
recovered = new / 'Восстановленные из STEP'
recovered.mkdir()
for part in sorted((project / 'recovered_from_step').glob('*.SLDPRT')):
    shutil.copy2(part, recovered / part.name)
assert len(list(recovered.glob('*.SLDPRT'))) == 14

plan = {}
for component in top.GetComponents(False) or []:
    parent = component.GetParent
    source_parent = Path(parent.GetPathName) if parent else source_top
    assert source_parent.is_relative_to(old)
    assert not sw.GetOpenDocumentByName(str(source_parent)).GetSaveFlag
    target_parent = new / source_parent.relative_to(old)
    source_child = Path(component.GetPathName)
    if source_child.is_file():
        assert source_child.is_relative_to(old), source_child
        target_child = new / source_child.relative_to(old)
    elif (recovered / source_child.name).is_file():
        target_child = recovered / source_child.name
    else:
        candidates = list(new.rglob(source_child.name))
        if len(candidates) != 1:
            raise RuntimeError(f'{source_child}: local candidate count {len(candidates)}')
        target_child = candidates[0]
    assert target_parent.is_file() and target_child.is_file()
    key = str(target_parent)
    plan.setdefault(key, {})[str(source_child)] = str(target_child)

path = project / 'relink_plan.json'
path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
print('ASSEMBLIES', len(plan), 'UNIQUE_REFERENCES', sum(map(len, plan.values())))
print('MISSING_REFERENCES', sum(not Path(source).is_file() for rows in plan.values() for source in rows))
print('PLAN', path)
