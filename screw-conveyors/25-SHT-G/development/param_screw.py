import glob,os,pythoncom,win32com.client as w
import json
root=r'C:\Users\adm\Documents\Codex\2026-09-28\new-chat\outputs\25.SHT.G_parameterized'
path=glob.glob(os.path.join(root,'*02.00.00.01*Шнек*SLDPRT'))[0]
sw=w.Dispatch('SldWorks.Application');sw.Visible=False
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);wa=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
m=sw.OpenDoc6(path,1,1,'',e,wa)
print('open',e.value,wa.value,bool(m),flush=True)
if not m: raise SystemExit(1)
sw.ActivateDoc2(m.GetTitle,False,e)
eq=m.GetEquationMgr
print('count before',eq.GetCount,flush=True)
try:print('configs',m.GetConfigurationNames,flush=True)
except Exception as ex:print('config error',repr(ex),flush=True)
existing=[eq.Equation(i).split('=')[0].strip() for i in range(eq.GetCount)]
if '"TEST"' in existing:
    print('delete TEST',eq.Delete(existing.index('"TEST"')),flush=True)
existing=[eq.Equation(i).split('=')[0].strip() for i in range(eq.GetCount)]
for s in ['"SCREW_PITCH" = 200','"SCREW_FLIGHT_LENGTH" = 2885','"SCREW_OD" = 200','"SCREW_CORE_OD" = 76','"FLIGHT_THK" = 12']:
    if s.split('=')[0].strip() in existing: continue
    try:print('add',s,eq.Add2(-1,s,True),flush=True)
    except Exception as ex:print('add error',repr(ex),flush=True)
features={}
f=m.FirstFeature
while f:
    if f.GetTypeName2=='Helix':features['helix']=f.Name
    if f.GetTypeName2=='ProfileFeature':
        d=f.GetFirstDisplayDimension
        vals=[]
        while d:
            try: vals.append(round(d.GetDimension2(0).SystemValue,6))
            except Exception:pass
            d=f.GetNextDisplayDimension(d)
        if 0.076 in vals and 0.2 in vals and 0.012 in vals:features['flight_sketch']=f.Name
    f=f.GetNextFeature
print('features',features,flush=True)
print('featuresjson',json.dumps(features,ensure_ascii=True),flush=True)
f=m.FirstFeature
while f:
    if f.Name==features['helix']:f.Name='HELIX_MASTER'
    if f.Name==features['flight_sketch']:f.Name='FLIGHT_SECTION'
    f=f.GetNextFeature
features={'helix':'HELIX_MASTER','flight_sketch':'FLIGHT_SECTION'}
for s in [
    f'"D4@{features["helix"]}" = "SCREW_PITCH"',
    f'"D3@{features["helix"]}" = "SCREW_FLIGHT_LENGTH"',
    f'"D2@{features["flight_sketch"]}" = "SCREW_OD"',
    f'"D1@{features["flight_sketch"]}" = "SCREW_CORE_OD"',
    f'"D3@{features["flight_sketch"]}" = "FLIGHT_THK"',
]:
    try: print('link',json.dumps(s,ensure_ascii=True),eq.Add2(-1,s,False),'status',eq.Status,flush=True)
    except Exception as ex:print('link error',repr(ex),flush=True)
print('count after',eq.GetCount,flush=True)
try:print('eval',eq.EvaluateAll,flush=True)
except Exception as ex:print('eval error',repr(ex),flush=True)
for i in range(eq.GetCount):
    try: print('equation',i,eq.Equation(i),eq.Value(i),flush=True)
    except Exception as ex:print('read error',repr(ex),flush=True)
try: print('save',m.Save3(1,e,wa),e.value,wa.value,flush=True)
except Exception as ex:print('save error',repr(ex),flush=True)
print('bbox',m.GetPartBox(True),flush=True)
sw.CloseDoc(m.GetTitle)
