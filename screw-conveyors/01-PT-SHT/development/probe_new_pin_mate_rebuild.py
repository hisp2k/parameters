from pathlib import Path
import sys,json,pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');p=json.loads((base/'pin_joint_trial_20261005.json').read_text(encoding='utf-8'))['root'];d=sw.GetOpenDocumentByName(p);e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(p,False,2,e)
print('Trial root rebuild',d.ForceRebuild3(False),flush=True);f=d.FeatureByName('Втулка 2 — ухо 3 — соосность');print('New mate after rebuild',f.GetErrorCode,flush=True);print('Issues',bridge.model_issues(sw,d),flush=True)
sw.ActivateDoc3(str(bridge.TOP_ASSEMBLY),False,2,e)
