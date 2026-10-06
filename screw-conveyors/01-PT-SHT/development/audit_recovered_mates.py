from pathlib import Path
import json
import sys

import win32com.client as win32

project = Path(sys.argv[1]).resolve()
top = Path(json.loads((project / 'recovered_assembly_check.json').read_text(encoding='utf-8'))['assembly'])
sw = win32.GetActiveObject('SldWorks.Application')
docs = [sw.GetOpenDocumentByName(str(top))]
docs += [d for d in sw.GetDocuments if '— восстановлено' in d.GetTitle and d.GetPathName != str(top)]
result = []
for doc in docs:
    doc.ForceRebuild3(False)
    features = []
    first = doc.FirstFeature
    while first:
        if first.GetErrorCode:
            features.append({'name': first.Name, 'type': first.GetTypeName2,
                             'code': int(first.GetErrorCode)})
        if first.GetTypeName2 == 'MateGroup':
            mate = first.GetFirstSubFeature
            while mate:
                if mate.GetErrorCode:
                    features.append({'name': mate.Name, 'type': mate.GetTypeName2,
                                     'code': int(mate.GetErrorCode)})
                mate = mate.GetNextSubFeature
        first = first.GetNextFeature
    result.append({'assembly': doc.GetPathName, 'errors': features})
    print(doc.GetTitle, 'ERROR_FEATURES', len(features),
          'MATE_ERRORS', sum(x['type'].startswith('Mate') for x in features), flush=True)

out = project / 'recovered_mate_audit.json'
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
