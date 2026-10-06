import win32com.client as w,uuid
s=w.Dispatch('SldWorks.Application');d=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc
for reg in [0,1]:
 u=str(uuid.uuid4())
 try:print('region',reg,'uuid',u,'result',d.CreateAttributeOnComponentSolidBodyTopology('CFD_inlet_lid-1',reg,2,0.2515,0.7195,0.334,u))
 except Exception as e:print('ERR',reg,repr(e))
