from pathlib import Path
import sys,json
import pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base))
import bridge
sw=w.GetActiveObject('SldWorks.Application')
errors=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);warnings=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
previous=sw.CommandInProgress;sw.CommandInProgress=True
try:
    for label,path in [('Прямые подкосы — опора 05.10.2026',bridge.FILES['support']),
                       ('Прямые подкосы — сборка 05.10.2026',bridge.TOP_ASSEMBLY)]:
        doc=sw.GetOpenDocumentByName(str(path));assert doc
        sw.ActivateDoc3(str(path),False,2,errors);assert not errors.value
        doc.ClearSelection2(True);doc.ShowNamedView2('*Isometric',7);doc.ViewZoomtofit2()
        output=base/(label+'.png')
        status=doc.SaveAs3(str(output),0,2)
        assert output.is_file() and output.stat().st_size>1000,(status,output)
        assert Path(doc.GetPathName).resolve()==path.resolve()
        print('Exported native model image',output,output.stat().st_size,flush=True)
    root=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY))
    assert root.Save3(13,errors,warnings) and not errors.value
    proof=json.loads((base/'straight_brace_restore_20261005.json').read_text(encoding='utf-8'))
    trial=Path(proof['trial_root']).parent
    trial_paths=[d.GetPathName for d in sw.GetDocuments if d.GetPathName and Path(d.GetPathName).is_relative_to(trial)]
    assert not [p for p in trial_paths if sw.GetOpenDocumentByName(p).GetSaveFlag]
    for path in sorted(trial_paths,key=lambda p:Path(p).suffix.upper()!='.SLDASM'):
        if sw.GetOpenDocumentByName(path):sw.CloseDoc(path)
finally:
    sw.ActivateDoc3(str(bridge.TOP_ASSEMBLY),False,2,errors);sw.CommandInProgress=previous
