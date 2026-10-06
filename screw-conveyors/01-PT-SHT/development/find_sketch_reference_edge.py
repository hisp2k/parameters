exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
f=doc.FirstFeature
while f and f.Name!='Эскиз1':f=f.GetNextFeature
sketch=f.GetSpecificFeature2;t=list(sketch.ModelToSketchTransform.ArrayData)
def world(p):return [sum((p[i]-t[9+i])*t[j*3+i] for i in range(3)) for j in range(3)]
a=world([1.6451919157906727,-.5003222642753968,0.]);b=world([2.1763767024464675,-.5003222642754064,0.]);n=[(b[i]-a[i]) for i in range(3)];length=sum(v*v for v in n)**.5;n=[v/length for v in n]
print('target',a,b,flush=True)
matches=[]
for comp in doc.GetComponents(False):
 d=comp.GetModelDoc2
 if not d or d.GetType!=1:continue
 mt=list(comp.Transform2.ArrayData)
 for body in d.GetBodies2(0,True) or []:
  for edge in body.GetEdges() or []:
   curve=edge.GetCurve
   if not curve.IsLine:continue
   p=list(curve.LineParams);v=[sum(p[3+j]*mt[j*3+i] for j in range(3)) for i in range(3)]
   if abs(sum(v[i]*n[i] for i in range(3)))<.99999:continue
   o=[sum(p[j]*mt[j*3+i] for j in range(3))+mt[9+i] for i in range(3)];delta=[o[i]-a[i] for i in range(3)];along=sum(delta[i]*n[i] for i in range(3));distance=sum((delta[i]-along*n[i])**2 for i in range(3))**.5
   if distance<.002:matches.append({'component':comp.Name2,'distance_mm':distance*1000,'curve':p})
print('matches',matches,flush=True)
