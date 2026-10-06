import glob,os,pythoncom,win32com.client as w
out=r'C:\Users\adm\Documents\Codex\2026-09-28\new-chat\outputs\25.SHT.G_parameterized'
path=glob.glob(os.path.join(out,'*Транспортер.SLDASM'))[0]
sw=w.Dispatch('SldWorks.Application');sw.Visible=False
try: print('CLOSE',sw.CloseAllDocuments(True),flush=True)
except Exception as ex: print('CLOSE ERROR',repr(ex),flush=True)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);wa=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
m=sw.OpenDoc6(path,2,1,'',e,wa)
print('OPEN',e.value,wa.value,bool(m),m.GetPathName if m else None,flush=True)
if not m: raise SystemExit
root=m.GetActiveConfiguration.GetRootComponent3(True)
cs=root.GetChildren
print('CHILDREN',len(cs))
for c in cs[:15]:print(c.Name2,c.GetPathName.startswith(out),c.GetPathName)
