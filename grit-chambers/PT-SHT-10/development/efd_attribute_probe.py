exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
import win32com.client as w
s=w.Dispatch('SldWorks.Application');m=s.ActiveDoc
print('active',m.GetPathName,'project',p.GetName())
c=next(c for c in m.GetComponents(False) or [] if c.Name2=='CFD_крышка_боковая-1')
face=(c.GetBody.GetFaces() or [])[2]
for args in [(face,None,None),(face,'','')]:
 try:print('CreateAttribute',p.CreateAttribute(*args))
 except Exception as e:print('ERR',repr(e))
