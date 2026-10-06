import glob,os,shutil,pythoncom,win32com.client as w
root=r'C:\Users\adm\Documents\Codex\2026-09-28\new-chat\outputs\25.SHT.G_parameterized'
tmp=r'C:\Users\adm\Documents\Codex\2026-09-28\new-chat\work'
part=glob.glob(os.path.join(root,'*02.00.00.01*Шнек*SLDPRT'))[0]
sw=w.Dispatch('SldWorks.Application');sw.Visible=False
def open_doc(path,kind):
    e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);wa=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    m=sw.OpenDoc6(path,kind,1,'',e,wa)
    if not m:raise RuntimeError((path,e.value,wa.value))
    sw.ActivateDoc2(m.GetTitle,False,e)
    return m
def dims(m):
    found={};f=m.FirstFeature
    while f:
        if f.Name in ('HELIX_MASTER','FLIGHT_SECTION'):
            d=f.GetFirstDisplayDimension
            while d:
                di=d.GetDimension2(0)
                found[di.FullName.split('@')[0]+'@'+f.Name]=di.SystemValue
                d=f.GetNextDisplayDimension(d)
        f=f.GetNextFeature
    return found
for pitch in (180,220):
    dest=os.path.join(tmp,f'screw_pitch_{pitch}.SLDPRT')
    shutil.copy2(part,dest)
    m=open_doc(dest,1);eq=m.GetEquationMgr
    for i in reversed(range(eq.GetCount)):
        if eq.Equation(i).startswith('"SCREW_PITCH"'):
            print('delete pitch',pitch,eq.Delete(i),flush=True)
    print('add pitch',pitch,eq.Add2(0,f'"SCREW_PITCH" = {pitch}',True),flush=True)
    rebuilt=m.EditRebuild3
    found=dims(m)
    print('test',pitch,'rebuild',rebuilt,'dims',found,'bbox',m.GetPartBox(True),flush=True)
    sw.CloseDoc(m.GetTitle)
asm=glob.glob(os.path.join(root,'*Транспортер.SLDASM'))[0]
m=open_doc(asm,2)
comps=m.GetActiveConfiguration.GetRootComponent3(True).GetChildren
print('ASSEMBLY first level',len(comps),flush=True)
bad=[(c.Name2,c.GetPathName,bool(c.IsSuppressed),bool(c.GetModelDoc2)) for c in comps if c.GetPathName and not c.GetPathName.lower().startswith(root.lower())]
print('outside references',len(bad),bad[:5],flush=True)
print('suppressed',sum(bool(c.IsSuppressed) for c in comps),flush=True)
sw.CloseDoc(m.GetTitle)
