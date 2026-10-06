from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

import win32com.client as win32

base = next(Path('outputs').glob('Шнек 1 — параметрическая модель')).resolve()
sw = win32.GetActiveObject('SldWorks.Application')
docs = [d for d in (sw.GetDocuments or []) if d.GetType == 2 and
        str(base).casefold() in d.GetPathName.casefold() and
        '— восстановлено' in d.GetPathName]
report = []
for doc in docs:
    errors = []
    feature = doc.FirstFeature
    while feature:
        if feature.GetTypeName2 == 'MateGroup':
            mate_feature = feature.GetFirstSubFeature
            while mate_feature:
                if mate_feature.GetErrorCode:
                    entry = {'name': mate_feature.Name, 'type': mate_feature.GetTypeName2,
                             'code': int(mate_feature.GetErrorCode), 'entities': []}
                    if entry['code'] == 48:
                        mate = mate_feature.GetSpecificFeature2
                        for i in (0, 1):
                            try:
                                entity = mate.MateEntity(i)
                                component = entity.ReferenceComponent
                                entry['entities'].append({
                                    'index': i,
                                    'component': component.Name2 if component else None,
                                    'path': component.GetPathName if component else None,
                                    'reference_present': entity.Reference is not None,
                                    'params': list(entity.EntityParams or []),
                                })
                            except Exception as exc:
                                entry['entities'].append({'index': i, 'exception': str(exc)})
                    errors.append(entry)
                mate_feature = mate_feature.GetNextSubFeature
        elif feature.GetErrorCode and feature.GetTypeName2 != 'MateGroup':
            errors.append({'name': feature.Name, 'type': feature.GetTypeName2,
                           'code': int(feature.GetErrorCode)})
        feature = feature.GetNextFeature
    report.append({'assembly': doc.GetPathName, 'errors': errors})

target = base / 'mate_diagnostics_20261004.json'
target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
for section in report:
    mates = [e for e in section['errors'] if e['code'] == 48]
    print(Path(section['assembly']).name, 'mates', len(mates),
          'missing_ref_patterns', dict(Counter(tuple(not x.get('reference_present')
                                                  for x in e['entities']) for e in mates)))
    components = Counter(Path(x['path']).name for e in mates for x in e['entities']
                         if x.get('path') and not x.get('reference_present'))
    print('missing components', dict(components))
