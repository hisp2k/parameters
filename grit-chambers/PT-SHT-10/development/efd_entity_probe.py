exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
import win32com.client as w
s=w.Dispatch('SldWorks.Application');m=s.ActiveDoc;c=next(c for c in m.GetComponents(False) or [] if c.Name2=='CFD_крышка_боковая-1');face=(c.GetBody.GetFaces() or [])[2]
cdoc=typed(app.GetCAD().GetActiveDoc(),'ICADDocument')
print('cad doc',cdoc.GetPathName())
try:
 entity=cdoc.GetEntity2(face)
 print('entity',entity,entity._oleobj_.GetTypeInfo().GetDocumentation(-1) if entity else None)
 if entity:
  try:print('attr',p.CreateAttribute(entity,None,None))
  except Exception as e:print('attr ERR',repr(e))
except Exception as e:print('entity ERR',repr(e))
