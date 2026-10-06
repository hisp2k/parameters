from pathlib import Path
b=Path(__file__).parent;s=(b/'CreateRailPrototype.cs').read_text(encoding='utf8')
s=s.replace('class RailPrototype','class SupportPrototype').replace('double cx,double bw,double h,double r','double cx,double cy,double bw,double h,double r').replace('bt=-h/2,tp=h/2','bt=cy-h/2,tp=cy+h/2').replace('Length==2','Length==5').replace('Expected 2 solid bodies','Expected 5 solid bodies')
pos=s.index('[STAThread]')
helpers=r'''
static double[] Point(object app,object transform,double x,double y,double z){object mu=C(app,"ISldWorks","GetMathUtility");object p=C(mu,"IMathUtility","CreatePoint",new object[]{new double[]{x,y,z}});p=C(p,"IMathPoint","MultiplyTransform",transform);return (double[])G(p,"IMathPoint","ArrayData");}
static void Body(object app,object doc,object plane,bool horizontal,double zcenter,double width,double height,double t,double ro,double depth,double startY,string name){
C(doc,"IModelDoc2","ClearSelection2",true);R(Convert.ToBoolean(C(plane,"IFeature","Select2",false,0)),"Plane selection failed");object sm=G(doc,"IModelDoc2","SketchManager");C(sm,"ISketchManager","InsertSketch",true);object sk=G(sm,"ISketchManager","ActiveSketch");object tr=G(sk,"ISketch","ModelToSketchTransform");double[] center=Point(app,tr,0,0,zcenter);var segs=new List<object>();S(sm,"ISketchManager","AddToDB",true);
if(t>0){RR(sm,segs,center[0],center[1],width,height,ro);RR(sm,segs,center[0],center[1],width-2*t,height-2*t,ro-t);}else{double x=center[0],y=center[1];Line(sm,segs,x-width/2,y-height/2,x+width/2,y-height/2);Line(sm,segs,x+width/2,y-height/2,x+width/2,y+height/2);Line(sm,segs,x+width/2,y+height/2,x-width/2,y+height/2);Line(sm,segs,x-width/2,y+height/2,x-width/2,y-height/2);}
S(sm,"ISketchManager","AddToDB",false);C(doc,"IModelDoc2","ClearSelection2",true);bool add=false;foreach(object sg in segs){R(Convert.ToBoolean(C(sg,"ISketchSegment","Select4",add,null)),"Fix selection failed");add=true;}C(doc,"IModelDoc2","SketchAddConstraints","sgFIXED");C(doc,"IModelDoc2","ClearSelection2",true);
object inv=C(tr,"IMathTransform","Inverse");double[] p0=Point(app,inv,0,0,0),pn=Point(app,inv,0,0,1);double normalY=pn[1]-p0[1];if(horizontal)R(Math.Abs(Math.Abs(normalY)-1)<1e-8,"Unexpected top plane normal");
C(sm,"ISketchManager","InsertSketch",true);object sf=C(doc,"IModelDoc2","FeatureByPositionReverse",0);S(sf,"IFeature","Name",name+"_FIXED_PROFILE");C(sf,"IFeature","Select2",false,0);object fm=G(doc,"IModelDoc2","FeatureManager");object boss=C(fm,"IFeatureManager","FeatureExtrusion3",true,false,horizontal&&normalY<0,0,0,depth,0d,false,false,false,false,0d,0d,false,false,false,false,false,false,true,horizontal?E("swStartConditions_e","swStartOffset"):0,horizontal?Math.Abs(startY):0d,horizontal&&startY*normalY<0);R(boss!=null,"Extrusion failed: "+name);S(boss,"IFeature","Name",name);
}
static List<object> Bodies(object d){var list=new List<object>();foreach(object body in (Array)C(d,"IPartDoc","GetBodies2",0,false)){double[] mp=(double[])C(body,"IBody2","GetMassProperties",7850d);double[] bb=(double[])C(body,"IBody2","GetBodyBox");list.Add(new Dictionary<string,object>{{"volume_m3",mp[3]},{"centroid_m",new double[]{mp[0],mp[1],mp[2]}},{"bounding_box_m",bb}});}return list;}
'''
s=s[:pos]+helpers+s[pos:]
start=s.index('object plane=C(doc');end=s.index('object ext=G(doc',start)
new=r'''var planes=new List<object>();object plane=C(doc,"IModelDoc2","FirstFeature");while(plane!=null){if(Convert.ToString(C(plane,"IFeature","GetTypeName2"))=="RefPlane")planes.Add(plane);plane=C(plane,"IFeature","GetNextFeature");}R(planes.Count>=2,"Default planes absent");
Body(app,doc,planes[0],false,0,.100,.080,.004,.008,.7,0,"CROSSBEAM_80_100_4");
Body(app,doc,planes[1],true,.05,.05,.05,.003,.006,.542,-.582,"LEG_LEFT_50_50_3");
Body(app,doc,planes[1],true,.65,.05,.05,.003,.006,.542,-.582,"LEG_RIGHT_50_50_3");
Body(app,doc,planes[1],true,.05,.120,.150,0,0,.008,-.590,"PLATE_LEFT_NO_HOLES");
Body(app,doc,planes[1],true,.65,.120,.150,0,0,.008,-.590,"PLATE_RIGHT_NO_HOLES");
R(Convert.ToBoolean(C(doc,"IModelDoc2","ForceRebuild3",false)),"Rebuild failed");double expected=.0018086096469458835;double vol=Volume(doc);R(Math.Abs(vol-expected)<1e-9,"Volume mismatch");report["initial_volume_m3"]=vol;report["calculated_mass_kg_at_7850"]=vol*7850;report["bodies"]=Bodies(doc);
'''
s=s[:start]+new+s[end:]
s=s.replace('"R03",replace','"R04",replace').replace('Two rounded hollow rails, 100x50x3, R6/R3, centre spacing 600, L5000. Section fixed; only length equation-driven. No welds, supports, crossmembers, rollers or belt tension loads.','Separate transverse support prototype: crossbeam 80x100x4 L700, two legs 50x50x3 L542, two solid plates 120x150x8 without holes. All geometry fixed. No welds, anchors, braces or rails. Coordinates: x longitudinal, y vertical; z transverse 0..700; foot bottom y=-590, beam top y=40 mm.')
s=s.replace('report["solid_body_count"]=2;report["length_probe_4500_and_restored_5000"]=true;','report["solid_body_count"]=5;report["fixed_geometry_no_parameter_probe"]=true;')
s=s.replace('report["section_shape_fixed_not_dimension_driven"]=true;','report["section_shape_fixed_not_dimension_driven"]=true;report["bodies_after_reopen"]=Bodies(doc);')
(b/'CreateSupportPrototype.cs').write_text(s,encoding='utf8')
print('Created C# source')
