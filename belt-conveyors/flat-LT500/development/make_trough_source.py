from pathlib import Path
import json
B=Path(__file__).resolve().parent;d=json.loads((B/'trough_r10.json').read_text(encoding='utf8'))
old=(B/'CreateLoadingPrototype.cs').read_text(encoding='utf8');pre=old.split('static object Build(')[0].replace('class LoadingPrototype','class TroughPrototype')
fork=pre[pre.index('static void Fork('):pre.index('static void Rotate(')]
fork=fork.replace('static void Fork(','static void ForkAt(').replace('double x,double z,string name','double x,double y,double z,string name')
for s,v in [('.100','(y-.024)'),('.145','(y+.021)'),('.124','y'),('.1115','(y-.0125)')]:fork=fork.replace(s,v)
rot=pre[pre.index('static void Rotate('):].replace('static void Rotate(','static void WingRotate(').replace('double a){','double a,double y,double z){').replace('name+"_SLOPE"','name+"_WING"').replace('"RotationOriginY",0d','"RotationOriginY",y').replace('"RotationOriginZ",0d','"RotationOriginZ",z').replace('"TransformX",0d','"TransformX",a').replace('"TransformZ",-a','"TransformZ",0d')
extra=fork+rot+'''static void Poly(object app,object doc,object plane,double[,] pts,double depth,double start,string name){object sm,tr;Begin(doc,plane,out sm,out tr);var seg=new List<object>();for(int i=0;i<pts.GetLength(0);i++){int j=(i+1)%pts.GetLength(0);double[]p=Point(app,tr,0,pts[i,1],pts[i,0]),q=Point(app,tr,0,pts[j,1],pts[j,0]);Line(sm,seg,p[0],p[1],q[0],q[1]);}Finish(app,doc,sm,tr,seg,0,depth,start,name);}
'''
build=r'''static object Build(object app){object doc=C(app,"ISldWorks","NewDocument",@"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\gost-part.prtdot",0,0d,0d);R(doc!=null,"New part");var pls=new List<object>();object f=C(doc,"IModelDoc2","FirstFeature");while(f!=null){if(Convert.ToString(C(f,"IFeature","GetTypeName2"))=="RefPlane")pls.Add(f);f=C(f,"IFeature","GetNextFeature");}R(pls.Count>=3,"Planes");
foreach(double z in new double[]{.05,.65})Tube(app,doc,pls[2],0,0,.05,z,.05,.1,.003,.006,.6,-.3,"REF_RAIL_"+(z<.1?"LEFT":"RIGHT"));
Tube(app,doc,pls[0],2,0,.12,0,.04,.04,.003,.006,.7,0,"CROSSBEAM");
'''
for tag,y,z,a in [('CENTRE',184,350,0),('LEFT',d['geometry']['wing_axis_Y_mm'],350-d['geometry']['wing_axis_offset_Z_mm'],20),('RIGHT',d['geometry']['wing_axis_Y_mm'],350+d['geometry']['wing_axis_offset_Z_mm'],-20)]:
 y/=1000;z/=1000
 build+=f'Ring(app,doc,pls[0],0,{y:.16g},.076,.070,.150,{z-.075:.16g},"SHELL_{tag}");Ring(app,doc,pls[0],0,{y:.16g},.025,0,.200,{z-.100:.16g},"SHAFT_{tag}");\n'
 for dz,s in [(-.0825,'MINUS'),(.0825,'PLUS')]:
  build+=f'Ring(app,doc,pls[0],0,{y:.16g},.076,.052,.015,{z+dz-.0075:.16g},"CARRIER_{tag}_{s}");Ring(app,doc,pls[0],0,{y:.16g},.052,.025,.015,{z+dz-.0075:.16g},"BEARING_ENV_{tag}_{s}");\n'
 for dz,s in [(-.096,'MINUS'),(.096,'PLUS')]:build+=f'ForkAt(app,doc,pls[0],0,{y:.16g},{z+dz:.16g},"FORK_{tag}_{s}");\n'
 if a:build+=f'foreach(object b in (Array)C(doc,"IPartDoc","GetBodies2",0,false))if(!Convert.ToString(G(b,"IBody2","Name")).StartsWith("REF_")&&(Convert.ToString(G(b,"IBody2","Name")).EndsWith("_{tag}")||Convert.ToString(G(b,"IBody2","Name")).Contains("_{tag}_")))WingRotate(app,doc,b,{a}*Math.PI/180,{y:.16g},{z:.16g});\n'
def array(pts):return 'new double[,] {'+','.join('{'+','.join(f'{v/1000:.16g}' for v in p)+'}' for p in pts)+'}'
for s in d['geometry']['supports']:build+=f'Poly(app,doc,pls[2],{array(s["points_ZY_mm"])},.060,-.030,"{s["name"]}");\n'
build+=f'Poly(app,doc,pls[2],{array(d["geometry"]["belt_polygon_ZY_mm"])},.180,-.090,"BELT_PROFILE_ENVELOPE");\n'
build+='''foreach(object b in (Array)C(doc,"IPartDoc","GetBodies2",0,false))if(Convert.ToString(G(b,"IBody2","Name"))=="BELT_PROFILE_ENVELOPE")try{S(b,"IBody2","MaterialPropertyValues2",new double[]{.1,.5,.6,.3,.7,.2,.2,.65,0});}catch{}
object[] bs=(object[])C(doc,"IPartDoc","GetBodies2",0,false);R(bs.Length==34,"Body count");foreach(object body in bs)Rotate(app,doc,body,1.5*Math.PI/180);R(Convert.ToBoolean(C(doc,"IModelDoc2","ForceRebuild3",false)),"Rebuild");return doc;}
'''
tail='[STAThread]'+old.split('[STAThread]')[1]
tail=tail.replace('"R09"','"R10"').replace('Four loading rollers at250mm pitch. OD76 face540 shaft25x620. Bearing envelopes25x52x15 only. Open forks lack retainers, seal covers, fits, welds, adjustment. Two reference rail stubs1100. Not integrated with R07. Belt thickness8 and seating-to-belt170 assumed. Geometry only, not strength or safety approval.','Three roller trough20deg, belt500 neutral width, centre180 wing160. Roller OD76 face180 shaft25x200. Crossbeam40x40x3. Seat-to-belt230 centre, thickness8 assumed. One station, two reference rails600, belt coupon180 sharp crease envelope. Not whole conveyor. Retainers seals fits welds adjustment not developed. Geometry only not strength approval.')
tail=tail.replace('C(doc,"IModelDoc2","ViewZoomtofit2");R(Convert.ToBoolean(C(doc,"IModelDoc2","SaveBMP"','C(doc,"IModelDoc2","ViewZoomtofit2");object view=G(doc,"IModelDoc2","ActiveView");S(view,"IModelView","Scale2",Convert.ToDouble(G(view,"IModelView","Scale2"))*.75);C(doc,"IModelDoc2","GraphicsRedraw2");R(Convert.ToBoolean(C(doc,"IModelDoc2","SaveBMP"')
(B/'CreateTroughPrototype.cs').write_text(pre+extra+build+tail,encoding='utf8')
print('R10 source generated')
