import glob,os,shutil,pythoncom,win32com.client as w
root=r'C:\Users\adm\Documents\Codex\2026-09-28\new-chat\outputs\25.SHT.G_parameterized'
src=glob.glob(os.path.join(root,'*02.00.00.01*Шнек*SLDPRT'))[0]
dst=r'C:\Users\adm\Documents\Codex\2026-09-28\new-chat\work\test_seteq.SLDPRT'
shutil.copy2(src,dst)
sw=w.Dispatch('SldWorks.Application');sw.Visible=False
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);wa=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
m=sw.OpenDoc6(dst,1,1,'',e,wa);sw.ActivateDoc2(m.GetTitle,False,e)
eq=m.GetEquationMgr
print('eq before',eq.Equation(0),type(eq.Equation),flush=True)
for meth in (1,2,3):
    try:
        if meth==1: eq.Equation[0]='"SCREW_PITCH" = 220'
        if meth==2: eq.Equation(0,'"SCREW_PITCH" = 220')
        if meth==3:
            dispid=eq._oleobj_.GetIDsOfNames('Equation')
            print('dispid',dispid,flush=True)
            eq._oleobj_.Invoke(dispid,0,pythoncom.DISPATCH_PROPERTYPUT,0,0,'"SCREW_PITCH" = 220')
        print('set success',meth,eq.Equation(0),flush=True)
    except Exception as ex:print('set error',meth,repr(ex),flush=True)
print('rebuild',m.EditRebuild3,flush=True)
print('eq final',eq.Equation(0),eq.Value(0),flush=True)
f=m.FirstFeature
while f:
    if f.Name=='HELIX_MASTER':
        d=f.GetFirstDisplayDimension
        while d:
            di=d.GetDimension2(0)
            if 'D4@' in di.FullName:print('pitch dim',di.SystemValue,flush=True)
            d=f.GetNextDisplayDimension(d)
    f=f.GetNextFeature
print('bbox',m.GetPartBox(True),flush=True)
sw.CloseDoc(m.GetTitle)
