from pathlib import Path
import sys, json, shutil
import pythoncom, win32com.client as w
from native_ear_saddle import create_saddle, saddle_surfaces

base=Path('outputs/Шнек 1 — параметрическая модель').resolve()
sys.path.insert(0,str(base))
import bridge
sw=w.GetActiveObject('SldWorks.Application')
previous=sw.CommandInProgress
sw.CommandInProgress=True
errors=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
warnings=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
try:
    tube=sw.GetOpenDocumentByName(str(bridge.FILES['tube']))
    ear=next(c for c in tube.GetComponents(True) if 'Ухо' in c.Name2)
    trial=Path('work/ear_saddle_trial/Ухо — параметрическое седло.SLDPRT').resolve()
    trial.parent.mkdir(exist_ok=True)
    opened=sw.GetOpenDocumentByName(str(trial))
    if opened:
        sw.CloseDoc(opened.GetTitle)
    shutil.copy2(ear.GetPathName,trial)
    spec=sw.GetOpenDocSpec(str(trial));spec.DocumentType=1;spec.Silent=True
    part=sw.OpenDoc7(spec)
    sw.ActivateDoc3(str(trial),False,2,errors)
    assert part and not errors.value and sw.ActiveDoc.GetPathName==str(trial)
    dimension,_=create_saddle(sw,part)
    rows=[]
    for diameter in (141,145,141):
        part.Parameter(dimension.split('@',1)[0]+'@Седло корпуса — профиль').SystemValue=diameter/1000
        assert part.ForceRebuild3(False)
        surfaces=saddle_surfaces(part)
        assert surfaces and all(abs(s[6]*2000-diameter)<1e-6 for s in surfaces),surfaces
        rows.append({'diameter_mm':diameter,'surfaces':surfaces})
        print('verified',diameter,surfaces,flush=True)
    assert part.Save3(9,errors,warnings) and not errors.value
    (base/'ear_saddle_trial_20261005.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
finally:
    sw.ActivateDoc3(str(bridge.TOP_ASSEMBLY),False,2,errors)
    sw.CommandInProgress=previous
