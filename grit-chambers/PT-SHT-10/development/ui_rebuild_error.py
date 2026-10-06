import win32com.client as w
s=w.Dispatch('SldWorks.Application');p=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
for args in [(None,),('',)]:
 try:print('error',p.GetLastRebuildError(*args))
 except Exception as e:print('ERR',repr(e))
