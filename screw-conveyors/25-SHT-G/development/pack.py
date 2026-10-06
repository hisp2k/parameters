import glob, os, pythoncom
import win32com.client as win32
base=r'C:\Users\adm\Desktop\25.SHT.G.00.00.00.00'
out=r'C:\Users\adm\Documents\Codex\2026-09-28\new-chat\outputs'
os.makedirs(out,exist_ok=True)
path=glob.glob(os.path.join(base,'**','*Транспортер.SLDASM'),recursive=True)[0]
sw=win32.Dispatch('SldWorks.Application');sw.Visible=False
e=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);w=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
m=sw.OpenDoc6(path,2,1,'',e,w)
print('open',e.value,w.value, bool(m),flush=True)
pg=m.Extension.GetPackAndGo()
print('pg', bool(pg),flush=True)
pg.IncludeDrawings=False
pg.IncludeSimulationResults=False
pg.FlattenToSingleFolder=True
print('names',len(pg.GetDocumentNames()),flush=True)
target=os.path.join(out,'25.SHT.G-parametric-source.zip')
print('set',pg.SetSaveToName(True,target),flush=True)
print('save',m.Extension.SavePackAndGo(pg),flush=True)
print('target',target,os.path.getsize(target) if os.path.exists(target) else 'missing',flush=True)
