import win32com.client as w
s=w.Dispatch('SldWorks.Application');a=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}')
print('check geometry start',flush=True)
try:print('result',a.TB_CheckGeometry(),flush=True)
except Exception as e:print('ERR',repr(e),flush=True)
