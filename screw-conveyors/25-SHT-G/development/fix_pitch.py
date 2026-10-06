import glob,os,pythoncom,win32com.client as w
root=r'C:\Users\adm\Documents\Codex\2026-09-28\new-chat\outputs\25.SHT.G_parameterized'
path=glob.glob(os.path.join(root,'*02.00.00.01*Шнек*SLDPRT'))[0]
sw=w.Dispatch('SldWorks.Application');sw.Visible=False
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);wa=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
m=sw.OpenDoc6(path,1,1,'',e,wa);sw.ActivateDoc2(m.GetTitle,False,e)
eq=m.GetEquationMgr
for i in reversed(range(eq.GetCount)):
    if eq.Equation(i).startswith('"D4@HELIX_MASTER"'):
        print('delete',i,eq.Delete(i),flush=True)
print('add pitch',eq.Add2(-1,'"D4@HELIX_MASTER" = "SCREW_PITCH"',True),flush=True)
print('rebuild',m.EditRebuild3,flush=True)
print('equations',[(eq.Equation(i),eq.Value(i)) for i in range(eq.GetCount)],flush=True)
f=m.FirstFeature
while f:
    if f.Name=='HELIX_MASTER' or f.Name=='FLIGHT_SECTION':
        d=f.GetFirstDisplayDimension
        while d:
            dim=d.GetDimension2(0)
            print('DIM',dim.FullName,dim.SystemValue,flush=True)
            d=f.GetNextDisplayDimension(d)
    f=f.GetNextFeature
print('save',m.Save3(1,e,wa),e.value,wa.value,flush=True)
sw.CloseDoc(m.GetTitle)
