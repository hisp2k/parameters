using System;using System.IO;using System.Collections.Generic;using System.Reflection;using System.Runtime.InteropServices;using System.Threading;using System.Web.Script.Serialization;
class SupportPrototype{
[DllImport("ole32.dll",CharSet=CharSet.Unicode,PreserveSig=false)]static extern void CLSIDFromProgID(string p,out Guid g);
[DllImport("oleaut32.dll",PreserveSig=false)]static extern void GetActiveObject(ref Guid g,IntPtr r,[MarshalAs(UnmanagedType.IUnknown)]out object o);
static Assembly api,enums;
static object C(object o,string f,string m,params object[]a){var mi=api.GetType("SolidWorks.Interop.sldworks."+f).GetMethod(m);if(mi==null)throw new Exception("Missing "+f+"."+m);return mi.Invoke(o,a);}
static object G(object o,string f,string p,params object[]a){return api.GetType("SolidWorks.Interop.sldworks."+f).GetProperty(p).GetValue(o,a.Length==0?null:a);}
static void S(object o,string f,string p,object v){api.GetType("SolidWorks.Interop.sldworks."+f).GetProperty(p).SetValue(o,v,null);}
static int E(string t,string v){return Convert.ToInt32(Enum.Parse(enums.GetType("SolidWorks.Interop.swconst."+t),v));}
static void R(bool v,string m){if(!v)throw new Exception(m);}
static Dictionary<string,object> State(object d){return new Dictionary<string,object>{{"path",C(d,"IModelDoc2","GetPathName")},{"dirty",C(d,"IModelDoc2","GetSaveFlag")}};}
static void Line(object sm,List<object>segs,double x1,double y1,double x2,double y2){object s=C(sm,"ISketchManager","CreateLine",x1,y1,0d,x2,y2,0d);R(s!=null,"Line failed");segs.Add(s);}
static void Arc(object sm,List<object>segs,double x1,double y1,double x2,double y2,double xm,double ym){object s=C(sm,"ISketchManager","Create3PointArc",x1,y1,0d,x2,y2,0d,xm,ym,0d);R(s!=null,"Arc failed");segs.Add(s);}
static void RR(object sm,List<object>segs,double cx,double cy,double bw,double h,double r){double l=cx-bw/2,rt=cx+bw/2,bt=cy-h/2,tp=cy+h/2,k=r/Math.Sqrt(2);
Line(sm,segs,l+r,bt,rt-r,bt);Arc(sm,segs,rt-r,bt,rt,bt+r,rt-r+k,bt+r-k);
Line(sm,segs,rt,bt+r,rt,tp-r);Arc(sm,segs,rt,tp-r,rt-r,tp,rt-r+k,tp-r+k);
Line(sm,segs,rt-r,tp,l+r,tp);Arc(sm,segs,l+r,tp,l,tp-r,l+r-k,tp-r+k);
Line(sm,segs,l,tp-r,l,bt+r);Arc(sm,segs,l,bt+r,l+r,bt,l+r-k,bt+r-k);}
static double Volume(object d){object bs=C(d,"IPartDoc","GetBodies2",0,false);R(bs!=null&&((Array)bs).Length==5,"Expected 5 solid bodies");double v=0;foreach(object body in (Array)bs){object raw=C(body,"IBody2","GetMassProperties",7850d);double[] mp=(double[])raw;v+=mp[3];}return v;}

static double[] Point(object app,object transform,double x,double y,double z){object mu=C(app,"ISldWorks","GetMathUtility");object p=C(mu,"IMathUtility","CreatePoint",new object[]{new double[]{x,y,z}});p=C(p,"IMathPoint","MultiplyTransform",transform);return (double[])G(p,"IMathPoint","ArrayData");}
static void Body(object app,object doc,object plane,bool horizontal,double zcenter,double width,double height,double t,double ro,double depth,double startY,string name){
C(doc,"IModelDoc2","ClearSelection2",true);R(Convert.ToBoolean(C(plane,"IFeature","Select2",false,0)),"Plane selection failed");object sm=G(doc,"IModelDoc2","SketchManager");C(sm,"ISketchManager","InsertSketch",true);object sk=G(sm,"ISketchManager","ActiveSketch");object tr=G(sk,"ISketch","ModelToSketchTransform");double[] center=Point(app,tr,0,0,zcenter);var segs=new List<object>();S(sm,"ISketchManager","AddToDB",true);
if(t>0){RR(sm,segs,center[0],center[1],width,height,ro);RR(sm,segs,center[0],center[1],width-2*t,height-2*t,ro-t);}else{double x=center[0],y=center[1];Line(sm,segs,x-width/2,y-height/2,x+width/2,y-height/2);Line(sm,segs,x+width/2,y-height/2,x+width/2,y+height/2);Line(sm,segs,x+width/2,y+height/2,x-width/2,y+height/2);Line(sm,segs,x-width/2,y+height/2,x-width/2,y-height/2);}
S(sm,"ISketchManager","AddToDB",false);C(doc,"IModelDoc2","ClearSelection2",true);bool add=false;foreach(object sg in segs){R(Convert.ToBoolean(C(sg,"ISketchSegment","Select4",add,null)),"Fix selection failed");add=true;}C(doc,"IModelDoc2","SketchAddConstraints","sgFIXED");C(doc,"IModelDoc2","ClearSelection2",true);
object inv=C(tr,"IMathTransform","Inverse");double[] p0=Point(app,inv,0,0,0),pn=Point(app,inv,0,0,1);double normalY=pn[1]-p0[1];if(horizontal)R(Math.Abs(Math.Abs(normalY)-1)<1e-8,"Unexpected top plane normal");
C(sm,"ISketchManager","InsertSketch",true);object sf=C(doc,"IModelDoc2","FeatureByPositionReverse",0);S(sf,"IFeature","Name",name+"_FIXED_PROFILE");C(sf,"IFeature","Select2",false,0);object fm=G(doc,"IModelDoc2","FeatureManager");object boss=C(fm,"IFeatureManager","FeatureExtrusion3",true,false,horizontal&&normalY<0,0,0,depth,0d,false,false,false,false,0d,0d,false,false,false,false,false,false,true,horizontal?E("swStartConditions_e","swStartOffset"):0,horizontal?Math.Abs(startY):0d,horizontal&&startY*normalY<0);R(boss!=null,"Extrusion failed: "+name);S(boss,"IFeature","Name",name);
}
static List<object> Bodies(object d){var list=new List<object>();foreach(object body in (Array)C(d,"IPartDoc","GetBodies2",0,false)){double[] mp=(double[])C(body,"IBody2","GetMassProperties",7850d);double[] bb=(double[])C(body,"IBody2","GetBodyBox");list.Add(new Dictionary<string,object>{{"volume_m3",mp[3]},{"centroid_m",new double[]{mp[0],mp[1],mp[2]}},{"bounding_box_m",bb}});}return list;}

[STAThread]static int Main(string[]args){using(var mx=new Mutex(false,@"Global\SolidWorksCodex_COM_Mutex")){bool held=false;object app=null,previous=null;string prevTitle=null;try{held=mx.WaitOne(10000);R(held,"Connector busy");api=Assembly.LoadFrom(@"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist\SolidWorks.Interop.sldworks.dll");Guid clsid;CLSIDFromProgID("SldWorks.Application",out clsid);GetActiveObject(ref clsid,IntPtr.Zero,out app);previous=G(app,"ISldWorks","IActiveDoc2");if(previous!=null)prevTitle=Convert.ToString(C(previous,"IModelDoc2","GetTitle"));object[] a={Path.GetFullPath(args[0]),1,1,"",0,0};object d=C(app,"ISldWorks","OpenDoc6",a);R(d!=null&&Convert.ToInt32(a[4])==0,"Open failed");object[] act={Convert.ToString(C(d,"IModelDoc2","GetTitle")),true,0};C(app,"ISldWorks","ActivateDoc2",act);C(d,"IModelDoc2","ShowNamedView2","*Isometric",7);C(d,"IModelDoc2","ViewZoomtofit2");R(Convert.ToBoolean(C(d,"IModelDoc2","SaveBMP",Path.GetFullPath(args[1]),1200,1000)),"BMP failed");Console.WriteLine("PREVIEW_SAVED");return 0;}catch(Exception e){Console.WriteLine(e.ToString());return 1;}finally{if(previous!=null&&prevTitle!=null&&app!=null){object[] a={prevTitle,true,0};C(app,"ISldWorks","ActivateDoc2",a);}if(held)mx.ReleaseMutex();}}}
}

