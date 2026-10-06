"""Keep the original end joints and connect them outside the conveyor envelope."""
import math
from brace_clearance_20261005 import dot,unit,world_point,last_profile

def rectangle_feature(part,name,y0,y1,z0,z1,cut=False,cut_depth=.012):
 manager=part.SketchManager;part.ClearSelection2(True)
 assert part.FeatureByName('Справа').Select2(False,0)
 manager.InsertSketch(True);sketch=manager.ActiveSketch
 transform=list(sketch.ModelToSketchTransform.ArrayData)
 a=world_point([0.,min(y0,y1),min(z0,z1)],transform)
 b=world_point([0.,max(y0,y1),max(z0,z1)],transform)
 assert abs(a[2])<1e-8 and abs(b[2])<1e-8
 manager.AddToDB=True
 try:segments=manager.CreateCornerRectangle(a[0],a[1],0.,b[0],b[1],0.)
 finally:manager.AddToDB=False
 assert segments
 profile=last_profile(part,'ProfileFeature');profile.Name=name+' — профиль'
 part.ClearSelection2(True)
 for i,segment in enumerate(segments):assert segment.Select4(i>0,part.SelectionManager.CreateSelectData)
 part.SketchAddConstraints('sgFIXED')
 part.ClearSelection2(True);manager.InsertSketch(True)
 assert profile.Select2(False,0)
 if cut:
  feature=part.FeatureManager.FeatureCut4(False,False,False,0,0,cut_depth,cut_depth,False,False,False,False,0.,0.,False,False,False,False,False,False,True,False,False,False,0,0.,False,True)
 else:
  feature=part.FeatureManager.FeatureExtrusion2(False,False,False,0,0,.015,.015,False,False,False,False,0.,0.,False,False,False,False,True,True,True,0,0.,False)
 assert feature and not feature.GetErrorCode,(name,feature.GetErrorCode if feature else None)
 feature.Name=name
 assert part.ForceRebuild3(False)
 return feature.Name

def create_bypass(sw,part,center,axis,diameter_mm=147,start_margin=.005):
 n=unit(axis);sign=1 if sum([part.GetPartBox(True)[2],part.GetPartBox(True)[5]])>0 else -1
 direction=[0.,-math.cos(math.radians(11)),sign*math.sin(math.radians(11))]
 end=.591/math.cos(math.radians(11))
 unsafe=[]
 for i in range(int(end*1000)+1):
  t=i/1000;p=[direction[k]*t-center[k] for k in range(3)];projection=dot(p,n)
  distance=math.sqrt(sum((p[k]-projection*n[k])**2 for k in range(3)))
  if distance<diameter_mm/2000+math.hypot(.015,.010):unsafe.append(t)
 assert unsafe
 start=unsafe[0]-start_margin;finish=unsafe[-1]+.040
 assert start>=.024 and finish<end-.030,(start,finish,end)
 a=[direction[i]*start for i in range(3)];b=[direction[i]*finish for i in range(3)]
 outward=sign*max(.100,max(abs(a[2]),abs(b[2]))+.050)
 names=[]
 for name,yy0,yy1,zz0,zz1 in [
  ('Обход корпуса — верхний переход',a[1]-.010,a[1]+.010,a[2]-sign*.005,outward+sign*.010),
  ('Обход корпуса — наружная ветвь',b[1]-.010,a[1]+.010,outward-sign*.010,outward+sign*.010),
  ('Обход корпуса — нижний переход',b[1]-.010,b[1]+.010,b[2]-sign*.005,outward+sign*.010),
 ]:names.append(rectangle_feature(part,name,yy0,yy1,zz0,zz1))
 for name,yy0,yy1,zz0,zz1 in [
  ('Полость обхода — верхний переход',a[1]-.007,a[1]+.007,a[2],outward+sign*.007),
  ('Полость обхода — наружная ветвь',b[1]-.007,a[1]+.007,outward-sign*.007,outward+sign*.007),
  ('Полость обхода — нижний переход',b[1]-.007,b[1]+.007,b[2],outward+sign*.007),
 ]:names.append(rectangle_feature(part,name,yy0,yy1,zz0,zz1,True))
 assert len(part.GetBodies2(0,True))==1
 return {'features':names,'start_distance_mm':start*1000,'finish_distance_mm':finish*1000,
         'outward_mm':outward*1000,'section_mm':[30,20,3],
         'end_joint_geometry_retained':True,'strength_verified':False}
