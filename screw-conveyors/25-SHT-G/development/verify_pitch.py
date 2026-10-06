import glob,os,shutil,pythoncom,win32com.client as w
root=r'C:\Users\adm\Documents\Codex\2026-09-28\new-chat\outputs\25.SHT.G_parameterized'
tmp=r'C:\Users\adm\Documents\Codex\2026-09-28\new-chat\work'
src=glob.glob(os.path.join(root,'*02.00.00.01*Шнек*SLDPRT'))[0]
sw=w.Dispatch('SldWorks.Application');sw.Visible=False
for pitch in (180,200,220):
    dst=os.path.join(tmp,f'pitch_validation_{pitch}.SLDPRT')
    shutil.copy2(src,dst)
    e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);wa=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    m=sw.OpenDoc6(dst,1,1,'',e,wa);sw.ActivateDoc2(m.GetTitle,False,e)
    eq=m.GetEquationMgr
    eq.Equation(0,f'"SCREW_PITCH" = {pitch}')
    ok=m.EditRebuild3
    f=m.FirstFeature
    actual=None
    while f:
        if f.Name=='HELIX_MASTER':
            d=f.GetFirstDisplayDimension
            while d:
                di=d.GetDimension2(0)
                if di.FullName.startswith('D4@'):actual=di.SystemValue*1000
                d=f.GetNextDisplayDimension(d)
        f=f.GetNextFeature
    print(pitch,'mm: rebuild',ok,'measured pitch',actual,'mm','bbox',m.GetPartBox(True),flush=True)
    sw.CloseDoc(m.GetTitle)
