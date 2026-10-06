import win32com.client as w
s=w.Dispatch('SldWorks.Application');p=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
try:
 x=p.EnumFeatures();print('features',x,type(x),len(x) if x else 0)
except Exception as e:print('ERR',repr(e))
