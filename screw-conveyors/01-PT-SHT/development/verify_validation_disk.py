from pathlib import Path
import json
import win32com.client as win32

report = json.loads(Path('work/validation_report.json').read_text(encoding='utf-8'))
base = (Path('work') / 'validation_model' / 'CAD').resolve()
specs = {
    'tube_part': (next(base.rglob("PT.SHT.01.21.00.09 'Труба шнека'.SLDPRT")), 1),
    'screw_part': (next(base.rglob("PT.SHT.01.24.00.05 'Винт шнека'.SLDPRT")), 1),
    'tube_assembly': (next(base.rglob("PT.SHT.01.21.00.00 СБ 'Труба в сборе'.SLDASM")), 2),
    'screw_assembly': (next(base.rglob("PT.SHT.01.24.00.00 СБ 'Шнековый вал'.SLDASM")), 2),
}
sw = win32.DispatchEx('SldWorks.Application')
sw.Visible = False
result = {}
try:
    for key, (path, kind) in specs.items():
        spec = sw.GetOpenDocSpec(str(path))
        spec.DocumentType = kind
        spec.ReadOnly = True
        spec.Silent = True
        doc = sw.OpenDoc7(spec)
        result[key] = {'box': doc.GetPartBox(True) if kind == 1 else None}
        if kind == 2:
            mgr = doc.GetEquationMgr
            result[key]['globals'] = [mgr.Equation(i) for i in range(mgr.GetCount) if '@' not in mgr.Equation(i).split('=')[0]]
finally:
    sw.ExitApp()
report['reopened_files'] = result
Path('work/validation_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('tube_box', result['tube_part']['box'])
print('screw_box', result['screw_part']['box'])
print('tube_globals', len(result['tube_assembly']['globals']))
print('screw_globals', len(result['screw_assembly']['globals']))
