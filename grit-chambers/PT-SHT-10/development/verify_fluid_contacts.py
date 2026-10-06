from pathlib import Path
import json,math
src=Path('work/diagnose_void_native.py').read_text(encoding='utf-8').replace(";s.RunCommand(-1,'')",'')
exec(src)
fluid=next(b for b in bodies if .1<b.GetMassProperties(1.)[3]<.3)
faces=[typed(x,'IFace2') for x in fluid.GetFaces()]
report={'method':'Native SOLIDWORKS Boolean fluid extraction, not Flow Check Geometry','volume_m3':fluid.GetMassProperties(1.)[3],'contacts':[]}
for name,pt,axis in [('inlet',(.2515,.7195,.329),2),('main_outlet',(0.,.458,.353),2),('bottom_outlet',(0.,.004,0.),1)]:
 candidates=[]
 for face in faces:
  bb=face.GetBox()
  if any(pt[k]<bb[k]-1e-8 or pt[k]>bb[k+3]+1e-8 for k in range(3)):continue
  su=typed(face.GetSurface(),'ISurface')
  if not su.IsPlane():continue
  near=face.GetClosestPointOn(*pt);dist=math.dist(pt,near[:3])
  if dist<1e-8:candidates.append({'distance_m':dist,'face_area_m2':face.GetArea(),'box':list(bb)})
 row={'port':name,'center_m':pt,'touching_faces':candidates};report['contacts'].append(row)
 print('CONTACT',json.dumps(row),flush=True)
assert all(x['touching_faces'] for x in report['contacts'])
Path('outputs/PT-SHT-10_проверка_полости.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
tes=typed(fluid.GetTessellation(None),'ITessellation')
tes.SurfacePlaneTolerance=.0005;tes.CurveChordTolerance=.0005;tes.NeedFaceFacetMap=True
print('TESSELLATE',tes.Tessellate(),'facets',tes.GetFacetCount(),flush=True)
triangles=[]
for f in faces:
 vals=f.GetTessTriangles(True)
 if vals:triangles.extend(vals)
if not triangles:
 vertices={}
 for idx in range(tes.GetFacetCount()):
  ids=[]
  for fin in tes.GetFacetFins(idx):
   for v in tes.GetFinVertices(fin):
    if v not in ids:ids.append(v)
  if len(ids)!=3:raise RuntimeError('nontriangular tessellation')
  for v in ids:
   if v not in vertices:vertices[v]=tes.GetVertexPoint(v)
   triangles.extend(vertices[v])
print('TESSELLATION',len(triangles)//9,flush=True)
if triangles:
 import struct
 out=Path('outputs/PT-SHT-10_проточная_область.stl')
 with out.open('wb') as fp:
  fp.write(b'Native SOLIDWORKS fluid geometry; units metres'.ljust(80,b' '));fp.write(struct.pack('<I',len(triangles)//9))
  for i in range(0,len(triangles),9):fp.write(struct.pack('<12fH',0.,0.,0.,*triangles[i:i+9],0))
 print('STL',out,flush=True)
