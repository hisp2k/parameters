import json
from pathlib import Path
import pythoncom
import win32com.client

pythoncom.CoInitialize()
root = Path.cwd() / 'work' / 'pt-sht-10-working-copy' / 'Модель'
sw = win32com.client.Dispatch('SldWorks.Application')
names = ['Цилиндр внешний','Цилиндр внутренний','Конус обратный','Конус.',
         'Труба входная','Труба внешняя','Труба внутренняя','Отвод.SLDPRT',
         'Фланец присоединительный']
rows=[]
for part in root.glob('*.SLDPRT'):
    if part.name.startswith('~$'):
        continue
    if not any(x in part.name for x in names):
        continue
    errs=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    warns=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    doc=sw.OpenDoc6(str(part),1,64,'',errs,warns)
    row={'name':part.name,'open_error':errs.value,'open_warning':warns.value}
    if not doc:
        rows.append(row); continue
    try: row['box']=list(doc.GetPartBox(True))
    except Exception as e: row['box_error']=str(e)
    try: row['rebuild']=doc.ForceRebuild3(False)
    except Exception as e: row['rebuild_error']=str(e)
    try:
        bodies=doc.GetBodies2(0,False) or []
        row['body_count']=len(bodies)
        row['bodies']=[]
        for body in bodies:
            b={'surfaces':[]}
            try: b['volume']=body.GetVolume()
            except Exception as e: b['volume_error']=str(e)
            for face in body.GetFaces() or []:
                surf=face.GetSurface
                try:
                    if surf.IsCylinder:
                        b['surfaces'].append({'type':'cylinder','params':list(surf.CylinderParams),'area':face.GetArea})
                    elif surf.IsCone:
                        b['surfaces'].append({'type':'cone','params':list(surf.ConeParams),'area':face.GetArea})
                except Exception as e: b.setdefault('surface_errors',[]).append(str(e))
            row['bodies'].append(b)
    except Exception as e: row['bodies_error']=str(e)
    rows.append(row)
print(json.dumps(rows,ensure_ascii=False,indent=2,default=str))
