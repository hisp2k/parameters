import pythoncom,win32com.client as w
exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
g=typed(p.GetGeneralSettings(),'IGeneralSettings')
print('before',g.GetComputationalDomain(0),flush=True)
b=(-.38,-.02,-.38,.38,.90,.40)
for vt in [pythoncom.VT_ARRAY|pythoncom.VT_R8]:
 try:
  a=w.VARIANT(vt,b)
  print('try',vt,g.SetComputationalDomain(0,a,a),flush=True)
  print('after',g.GetComputationalDomain(0),flush=True)
 except Exception as e:print('ERR',vt,repr(e),flush=True)
print('rebuild',p.Rebuild(True,True,True,False,False,False),flush=True)
print('error',p.GetLastRebuildError(),flush=True)
