"""Rewrite references in the isolated recovered CAD tree."""
from pathlib import Path
import json
import sys

import win32com.client as win32

project = Path(sys.argv[1]).resolve()
plan = json.loads((project / 'relink_plan.json').read_text(encoding='utf-8'))
sw = win32.GetActiveObject('SldWorks.Application')
results = []
for assembly, references in plan.items():
    if sw.GetOpenDocumentByName(assembly) is not None:
        raise RuntimeError(f'Referencing document is open: {assembly}')
    for old, new in references.items():
        already_done = (Path(assembly).name.startswith('PT.SHT.01.20.00.00') and
                        ('Болт М8х25 DIN 933.SLDPRT' in old or
                         "PT.SHT.01.22.00.00 СБ 'Обойма верхняя'.SLDASM" in old))
        if already_done:
            status = 'prior_probe_success'
        else:
            status = 'success' if sw.ReplaceReferencedDocument(assembly, old, new) else 'failed'
        results.append({'assembly': assembly, 'old': old, 'new': new, 'status': status})
        print(status, Path(assembly).name, Path(old).name, flush=True)
        (project / 'relink_results.json').write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
        if status == 'failed':
            raise RuntimeError(f'Relink failed: {assembly}: {old}')
print('SUCCESS', len(results))
