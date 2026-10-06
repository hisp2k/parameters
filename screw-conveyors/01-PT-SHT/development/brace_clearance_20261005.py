"""Native editable clearance cut for the approved 55 degree arrangement."""
import math
import pythoncom,win32com.client as w

def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def unit(a):return [x/math.sqrt(dot(a,a)) for x in a]
def world_point(p,t):return [sum(p[j]*t[j*3+i] for j in range(3))+t[9+i] for i in range(3)]
def local_point(p,t):return [sum((p[i]-t[9+i])*t[j*3+i] for i in range(3)) for j in range(3)]
def local_vector(p,t):return [sum(p[i]*t[j*3+i] for i in range(3)) for j in range(3)]
def last_profile(part,kind):
 f=part.FirstFeature;last=None
 while f:
  if f.GetTypeName2==kind:last=f
  f=f.GetNextFeature
 assert last
 return last

def create_clearance(sw,part,center,axis,diameter_mm=147):
 assert not part.FeatureByName('Проход корпуса — выборка для 55 градусов')
 n=unit(axis);u=unit(cross(n,[0.,0.,1.] if abs(n[2])<.9 else [0.,1.,0.]));v=cross(n,u)
 manager=part.SketchManager
 part.ClearSelection2(True);manager.Insert3DSketch(True)
 manager.AddToDB=True
 try:
  points=[manager.CreatePoint(*p) for p in [center,[center[i]+.1*u[i] for i in range(3)],[center[i]+.1*v[i] for i in range(3)]]]
 finally:manager.AddToDB=False
 assert all(points)
 part.ClearSelection2(True)
 for i,p in enumerate(points):assert p.Select4(i>0,part.SelectionManager.CreateSelectData)
 part.SketchAddConstraints('sgFIXED')
 manager.Insert3DSketch(True)
 datum=last_profile(part,'3DProfileFeature');datum.Name='Ось корпуса 55 градусов — базовые точки'
 part.ClearSelection2(True)
 for i,p in enumerate(points):
  selection=part.SelectionManager.CreateSelectData;selection.Mark=i
  assert p.Select4(i>0,selection)
 plane_ref=part.FeatureManager.InsertRefPlane(4,0.,4,0.,4,0.)
 assert plane_ref,'Three-point reference plane creation failed'
 plane=part.SelectionManager.GetSelectedObject6(1,-1)
 f=part.FirstFeature;new_plane=None
 while f:
  if f.GetTypeName2=='RefPlane':new_plane=f
  f=f.GetNextFeature
 assert new_plane;new_plane.Name='Проход корпуса — поперечная плоскость'
 part.ClearSelection2(True);assert new_plane.Select2(False,0)
 manager.InsertSketch(True);sketch=manager.ActiveSketch
 transform=list(sketch.ModelToSketchTransform.ArrayData)
 point=world_point(center,transform);assert abs(point[2])<1e-7,point
 manager.AddToDB=True
 try:circle=manager.CreateCircleByRadius(point[0],point[1],0.,diameter_mm/2000)
 finally:manager.AddToDB=False
 assert circle
 part.ClearSelection2(True);assert circle.GetCenterPoint2.Select4(False,part.SelectionManager.CreateSelectData)
 part.SketchAddConstraints('sgFIXED')
 part.ClearSelection2(True);assert circle.Select4(False,part.SelectionManager.CreateSelectData)
 preference=sw.GetUserPreferenceToggle(10)
 try:
  sw.SetUserPreferenceToggle(10,False);assert not sw.GetUserPreferenceToggle(10)
  dimension=part.AddDiameterDimension2(point[0]+.09,point[1],0.)
 finally:sw.SetUserPreferenceToggle(10,preference)
 assert dimension;dimension.GetDimension2(0).SystemValue=diameter_mm/1000
 profile=last_profile(part,'ProfileFeature');profile.Name='Проход корпуса — профиль'
 part.ClearSelection2(True);manager.InsertSketch(True)
 assert profile.Select2(False,0)
 cut=part.FeatureManager.FeatureCut4(False,False,False,1,1,.1,.1,False,False,False,False,0.,0.,False,False,False,False,False,False,True,False,False,False,0,0.,False,True)
 assert cut and not cut.GetErrorCode
 cut.Name='Проход корпуса — выборка для 55 градусов'
 assert part.ForceRebuild3(False)
 return {'cut':cut.Name,'diameter_mm':diameter_mm,'center':center,'axis':axis,'profile':profile.Name,'datum':datum.Name,'plane':new_plane.Name}
