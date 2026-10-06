import win32com.client as w
s=w.Dispatch('SldWorks.Application');a=s.ActiveDoc
for c in a.GetComponents(False) or []:
 if not c.Name2.startswith('CFD_') or c.GetSuppression==0:continue
 box=c.GetBox(False,False)
 print('\n',c.Name2,box,flush=True)
 try:
  body=c.GetBody
  if not body:continue
  for i,f in enumerate(body.GetFaces() or []):
   surf=f.GetSurface
   if surf.IsPlane:print(i,'plane',f.GetArea, f.GetBox,surf.PlaneParams,flush=True)
 except Exception as e:print('ERR',repr(e),flush=True)
