import glob,os,pythoncom,win32com.client as w
root=r'C:\Users\adm\Documents\Codex\2026-09-28\new-chat\outputs\25.SHT.G_parameterized'
path=glob.glob(os.path.join(root,'*02.00.00.01*Шнек*SLDPRT'))[0]
sw=w.Dispatch('SldWorks.Application');sw.Visible=False
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);wa=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
m=sw.OpenDoc6(path,1,1,'',e,wa)
try:print('active',sw.ActivateDoc2(m.GetTitle,False,e),e.value,flush=True)
except Exception as ex:print('activate error',repr(ex),flush=True)
eq=m.GetEquationMgr
print('add numeric',eq.Add2(-1,'"D4@HELIX_MASTER" = 200',False),'status',eq.Status,flush=True)
f=m.FirstFeature
while f:
    if f.GetTypeName2=='Helix':break
    f=f.GetNextFeature
d=f.GetFirstDisplayDimension
while d:
    di=d.GetDimension2(0)
    print('dim',di.FullName,di.SystemValue,flush=True)
    if 'D4@' in di.FullName:
        print('set',di.SetSystemValue3(0.22,0,None),flush=True)
        print('after',di.SystemValue,flush=True)
        print('rebuild',m.EditRebuild3,flush=True)
        print('bbox',m.GetPartBox(True),flush=True)
        print('reset',di.SetSystemValue3(0.2,0,None),flush=True)
        print('rebuild2',m.EditRebuild3,flush=True)
    d=f.GetNextDisplayDimension(d)
print('save',m.Save3(1,e,wa),e.value,wa.value,flush=True)
sw.CloseDoc(m.GetTitle)
