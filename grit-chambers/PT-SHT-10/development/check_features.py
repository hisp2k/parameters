import json
from pathlib import Path
import pythoncom
import win32com.client

pythoncom.CoInitialize()
root = Path.cwd() / 'work' / 'pt-sht-10-working-copy' / 'Модель'
sw=win32com.client.Dispatch('SldWorks.Application')
rows=[]
for p in root.iterdir():
    if p.name.startswith('~$') or p.suffix.upper() not in ('.SLDASM','.SLDPRT'):
        continue
    typ=2 if p.suffix.upper()=='.SLDASM' else 1
    e=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    w=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    d=sw.OpenDoc6(str(p),typ,64,'',e,w)
    x={'name':p.name,'open_error':e.value,'open_warning':w.value}
    if d:
        x['rebuild']=d.ForceRebuild3(False)
        errors=[]; n=0
        f=d.FirstFeature
        while f and n<1000:
            n+=1
            try:
                code=f.GetErrorCode
                if code: errors.append({'name':f.Name,'code':code})
            except Exception: pass
            f=f.GetNextFeature
        x['feature_count']=n; x['feature_errors']=errors
    rows.append(x)
print(json.dumps(rows,ensure_ascii=False,indent=2))
