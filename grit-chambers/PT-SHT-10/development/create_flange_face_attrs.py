import win32com.client as w,uuid,json
s=w.Dispatch('SldWorks.Application');d=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc
rows={}
for name,coord in [('CFD_inlet_flange_lid-1',(0.2515,0.7195,0.334)),('CFD_outlet_flange_lid-1',(0,0.458,0.354)),('CFD_bottom_flange_lid-1',(0,0.003,0))]:
 u=str(uuid.uuid4());res=d.CreateAttributeOnComponentSolidBodyTopology(name,0,2,*coord,u)
 rows[name]={'uuid':u,'created':bool(res),'point':coord};print(name,u,res,flush=True)
open('work/face_uuids.json','w',encoding='utf-8').write(json.dumps(rows,ensure_ascii=False,indent=2))
