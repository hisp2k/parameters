import win32com.client as w
s=w.Dispatch('SldWorks.Application');a=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI()
for label,o in [('appapi',a),('docapi',a.IActiveDoc),('projapi',a.IActiveDoc.IActiveProject)]:
 print(label,o, o._oleobj_.GetTypeInfo().GetDocumentation(-1) if o else None)
