using System;
using System.IO;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Threading;
using System.Web.Script.Serialization;

class CreateMaster {
  [DllImport("ole32.dll",CharSet=CharSet.Unicode,PreserveSig=false)] static extern void CLSIDFromProgID(string p,out Guid g);
  [DllImport("oleaut32.dll",PreserveSig=false)] static extern void GetActiveObject(ref Guid g,IntPtr r,[MarshalAs(UnmanagedType.IUnknown)]out object o);
  static Assembly api, enums;
  static object C(object o,string f,string m,params object[] a){if(o==null)throw new Exception("Null target "+f+"."+m);var method=api.GetType("SolidWorks.Interop.sldworks."+f,true).GetMethod(m);if(method==null)throw new Exception("Missing API method "+f+"."+m);return method.Invoke(o,a);}
  static object G(object o,string f,string p,params object[] a){return api.GetType("SolidWorks.Interop.sldworks."+f,true).GetProperty(p).GetValue(o,a.Length==0?null:a);}
  static void S(object o,string f,string p,object v){api.GetType("SolidWorks.Interop.sldworks."+f,true).GetProperty(p).SetValue(o,v,null);}
  static int E(string t,string v){return Convert.ToInt32(Enum.Parse(enums.GetType("SolidWorks.Interop.swconst."+t,true),v));}
  static Dictionary<string,object> State(object d){return new Dictionary<string,object>{{"title",C(d,"IModelDoc2","GetTitle")},{"path",C(d,"IModelDoc2","GetPathName")},{"dirty",C(d,"IModelDoc2","GetSaveFlag")}};}
  static void Require(bool ok,string msg){if(!ok)throw new Exception(msg);}
  static object MakeDim(object doc,object seg,string method,double x,double y,string label){
    C(doc,"IModelDoc2","ClearSelection2",true);
    Require(Convert.ToBoolean(C(seg,"ISketchSegment","Select4",false,null)),"selection failed");
    object dd=C(doc,"IModelDoc2",method,x,y,0.0);Require(dd!=null,"dimension failed "+label);
    object dim=C(dd,"IDisplayDimension","GetDimension2",0);S(dim,"IDimension","Name",label);
    C(doc,"IModelDoc2","ClearSelection2",true);return dim;
  }
  static double Val(object dim){return Convert.ToDouble(G(dim,"IDimension","SystemValue"));}
  static object Line(object sm,double x1,double y1,double x2,double y2){object s=C(sm,"ISketchManager","CreateLine",x1,y1,0.0,x2,y2,0.0);Require(s!=null,"line failed");return s;}
  static void StartSketch(object doc,object plane,object sm){C(doc,"IModelDoc2","ClearSelection2",true);Require(Convert.ToBoolean(C(plane,"IFeature","Select2",false,0)),"plane failed");C(sm,"ISketchManager","InsertSketch",true);}
  static void FixStart(object doc,object segment){object p=C(segment,"ISketchLine","GetStartPoint2");C(doc,"IModelDoc2","ClearSelection2",true);C(p,"ISketchPoint","Select4",false,null);C(doc,"IModelDoc2","SketchAddConstraints","sgFIXED");C(doc,"IModelDoc2","ClearSelection2",true);}
  static void Eq(object mgr,string text){int i=Convert.ToInt32(C(mgr,"IEquationMgr","GetCount"));Require(Convert.ToInt32(C(mgr,"IEquationMgr","Add2",-1,text,false))>=0,"Equation failed: "+text);}
  [STAThread] static int Main(string[] args){
    object app=null,doc=null,previous=null;string previousTitle=null,createdTitle=null;bool saved=false;int inputPreference=0;bool oldInputPreference=false,preferenceChanged=false;
    var report=new Dictionary<string,object>(); string reportPath=args[1];
    using(var mutex=new Mutex(false,"Global\\SolidWorksCodex_COM_Mutex")){
      bool held=false;
      try{
        held=mutex.WaitOne(10000);Require(held,"Connector busy");
        api=Assembly.LoadFrom(@"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist\SolidWorks.Interop.sldworks.dll");
        enums=Assembly.LoadFrom(@"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist\SolidWorks.Interop.swconst.dll");
        Guid clsid;CLSIDFromProgID("SldWorks.Application",out clsid);GetActiveObject(ref clsid,IntPtr.Zero,out app);
        report["revision"]=C(app,"ISldWorks","RevisionNumber");
        previous=G(app,"ISldWorks","IActiveDoc2");
        if(previous!=null){previousTitle=Convert.ToString(C(previous,"IModelDoc2","GetTitle"));report["previous_before"]=State(previous);}
        string output=Path.GetFullPath(args[0]);Require(!File.Exists(output),"Destination already exists");
        Require(output.StartsWith(@"C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2\outputs\",StringComparison.OrdinalIgnoreCase),"Output outside task");
        string template=Convert.ToString(C(app,"ISldWorks","GetUserPreferenceStringValue",E("swUserPreferenceStringValue_e","swDefaultTemplatePart")));
        if(!File.Exists(template))template=@"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\gost-part.prtdot";
        Require(File.Exists(template),"Part template not found");report["template"]=template;
        doc=C(app,"ISldWorks","NewDocument",template,0,0.0,0.0);Require(doc!=null,"NewDocument failed");createdTitle=Convert.ToString(C(doc,"IModelDoc2","GetTitle"));
        var planes=new List<object>();object feature=C(doc,"IModelDoc2","FirstFeature");
        while(feature!=null){if(Convert.ToString(C(feature,"IFeature","GetTypeName2"))=="RefPlane")planes.Add(feature);feature=C(feature,"IFeature","GetNextFeature");}
        Require(planes.Count>=2,"Template planes missing");
        inputPreference=E("swUserPreferenceToggle_e","swInputDimValOnCreate");oldInputPreference=Convert.ToBoolean(C(app,"ISldWorks","GetUserPreferenceToggle",inputPreference));C(app,"ISldWorks","SetUserPreferenceToggle",inputPreference,false);preferenceChanged=true;
        object sm=G(doc,"IModelDoc2","SketchManager");
        double L=10.0,W=0.5,H=0.8,theta=1.5,drop=L*Math.Tan(theta*Math.PI/180),hin=H+drop/2,hout=H-drop/2;
        StartSketch(doc,planes[0],sm);
        object baseline=Line(sm,0,0,L,0);object right=Line(sm,L,0,L,hout);object top=Line(sm,L,hout,0,hin);object left=Line(sm,0,hin,0,0);
        FixStart(doc,baseline);
        object dimL=MakeDim(doc,baseline,"AddHorizontalDimension2",L/2,-0.2,"AI_L_GAB");
        object dimOut=MakeDim(doc,right,"AddVerticalDimension2",L+0.25,hout/2,"AI_H_OUT");
        object dimIn=MakeDim(doc,left,"AddVerticalDimension2",-0.25,hin/2,"AI_H_IN");
        C(sm,"ISketchManager","InsertSketch",true);
        object sideFeature=C(doc,"IModelDoc2","FeatureByPositionReverse",0);S(sideFeature,"IFeature","Name","MASTER_SIDE");
        StartSketch(doc,planes[1],sm);
        object a=Line(sm,0,0,L,0);object b=Line(sm,L,0,L,W);Line(sm,L,W,0,W);Line(sm,0,W,0,0);FixStart(doc,a);
        object dimPlanL=MakeDim(doc,a,"AddHorizontalDimension2",L/2,-0.1,"AI_L_PLAN");
        object dimW=MakeDim(doc,b,"AddVerticalDimension2",L+0.15,W/2,"AI_B_BELT");
        C(sm,"ISketchManager","InsertSketch",true);
        object planFeature=C(doc,"IModelDoc2","FeatureByPositionReverse",0);S(planFeature,"IFeature","Name","MASTER_BELT_PLAN");
        object mgr=C(doc,"IModelDoc2","GetEquationMgr");
        Eq(mgr,"\"L_GAB\" = 10000");Eq(mgr,"\"B_BELT\" = 500");Eq(mgr,"\"H_MID_DRAFT\" = 800");Eq(mgr,"\"THETA_DOWN_DRAFT\" = 1.5");
        // SOLIDWORKS equations use radians for the unitless tangent argument.
        Eq(mgr,"\"DROP_DRAFT\" = \"L_GAB\" * tan(\"THETA_DOWN_DRAFT\" * 3.141592653589793 / 180)");
        Eq(mgr,"\"H_IN_DRAFT\" = \"H_MID_DRAFT\" + \"DROP_DRAFT\" / 2");
        Eq(mgr,"\"H_OUT_DRAFT\" = \"H_MID_DRAFT\" - \"DROP_DRAFT\" / 2");
        Eq(mgr,"\""+G(dimL,"IDimension","FullName")+"\" = \"L_GAB\"");
        Eq(mgr,"\""+G(dimPlanL,"IDimension","FullName")+"\" = \"L_GAB\"");
        Eq(mgr,"\""+G(dimW,"IDimension","FullName")+"\" = \"B_BELT\"");
        Eq(mgr,"\""+G(dimIn,"IDimension","FullName")+"\" = \"H_IN_DRAFT\"");
        Eq(mgr,"\""+G(dimOut,"IDimension","FullName")+"\" = \"H_OUT_DRAFT\"");
        C(mgr,"IEquationMgr","EvaluateAll");bool rebuilt=Convert.ToBoolean(C(doc,"IModelDoc2","ForceRebuild3",false));Require(rebuilt,"Rebuild failed");
        report["initial_dimensions_m"]=new double[]{Val(dimL),Val(dimPlanL),Val(dimW),Val(dimIn),Val(dimOut)};
        Require(Math.Abs(Val(dimIn)-hin)<1e-7 && Math.Abs(Val(dimOut)-hout)<1e-7,"Slope equation verification failed");
        var probes=new List<object>();
        foreach(double t in new double[]{1.0,2.0}){
          api.GetType("SolidWorks.Interop.sldworks.IEquationMgr").GetProperty("Equation").SetValue(mgr,"\"THETA_DOWN_DRAFT\" = "+t.ToString(CultureInfo.InvariantCulture),new object[]{3});
          C(mgr,"IEquationMgr","EvaluateAll");Require(Convert.ToBoolean(C(doc,"IModelDoc2","ForceRebuild3",false)),"Probe rebuild failed");
          double d=L*Math.Tan(t*Math.PI/180);Require(Math.Abs(Val(dimIn)-(H+d/2))<1e-7&&Math.Abs(Val(dimOut)-(H-d/2))<1e-7,"Angle probe failed");
          probes.Add(new Dictionary<string,object>{{"angle_deg",t},{"height_in_m",Val(dimIn)},{"height_out_m",Val(dimOut)}});
        }
        api.GetType("SolidWorks.Interop.sldworks.IEquationMgr").GetProperty("Equation").SetValue(mgr,"\"THETA_DOWN_DRAFT\" = 1.5",new object[]{3});C(mgr,"IEquationMgr","EvaluateAll");
        // Check that width is driven by its global variable without retaining a changed design.
        api.GetType("SolidWorks.Interop.sldworks.IEquationMgr").GetProperty("Equation").SetValue(mgr,"\"B_BELT\" = 520",new object[]{1});C(mgr,"IEquationMgr","EvaluateAll");C(doc,"IModelDoc2","ForceRebuild3",false);Require(Math.Abs(Val(dimW)-0.52)<1e-7,"Width probe failed");
        api.GetType("SolidWorks.Interop.sldworks.IEquationMgr").GetProperty("Equation").SetValue(mgr,"\"B_BELT\" = 500",new object[]{1});C(mgr,"IEquationMgr","EvaluateAll");
        Require(Convert.ToBoolean(C(doc,"IModelDoc2","ForceRebuild3",false)),"Final rebuild failed");
        Require(Math.Abs(Val(dimW)-W)<1e-7&&Math.Abs(Val(dimIn)-hin)<1e-7,"Restoration failed");
        object ext=G(doc,"IModelDoc2","Extension");object props=G(ext,"IModelDocExtension","CustomPropertyManager","");
        int textType=E("swCustomInfoType_e","swCustomInfoText"),replace=E("swCustomPropertyAddOption_e","swCustomPropertyReplaceValue");
        C(props,"ICustomPropertyManager","Add3","STATUS",textType,"DRAFT - REFERENCE GEOMETRY - NOT FOR MANUFACTURING",replace);
        C(props,"ICustomPropertyManager","Add3","REVISION",textType,"R01",replace);
        C(props,"ICustomPropertyManager","Add3","LIMITATIONS",textType,"No solid bodies, drum axes, supports or purchased parts. L_GAB is an outer reference envelope. Angle 1.5 deg and height at midpoint 800 mm are provisional assumptions.",replace);
        C(doc,"IModelDoc2","ViewZoomtofit2");
        int silent=E("swSaveAsOptions_e","swSaveAsOptions_Silent");object[] saveArgs={output,0,silent,null,null,0,0};
        bool save=Convert.ToBoolean(C(ext,"IModelDocExtension","SaveAs3",saveArgs));Require(save&&Convert.ToInt32(saveArgs[5])==0&&File.Exists(output),"Save failed");saved=true;
        report["save_errors"]=saveArgs[5];report["save_warnings"]=saveArgs[6];report["file_path"]=output;report["rebuild"]=true;report["angle_probes"]=probes;report["width_probe_restored"]=true;
        report["equation_count"]=C(mgr,"IEquationMgr","GetCount");report["manufacturing_approved"]=false;report["solid_bodies_expected"]=0;
        report["native_scope"]="Parametric side and belt plan reference sketches only. Frame modules, supports, drums, tensioning, assemblies and Simulation remain open.";
        if(previous!=null){report["previous_after"]=State(previous);object[] activate={previousTitle,true,0};C(app,"ISldWorks","ActivateDoc2",activate);report["previous_reactivated"]=Convert.ToInt32(activate[2])==0;}
        report["ok"]=true;
      }catch(Exception ex){report["ok"]=false;report["error"]=ex.ToString();if(doc!=null&&!saved&&createdTitle!=null){try{C(app,"ISldWorks","CloseDoc",createdTitle);}catch{}}}
      finally{if(preferenceChanged){try{C(app,"ISldWorks","SetUserPreferenceToggle",inputPreference,oldInputPreference);}catch{}}if(previous!=null&&previousTitle!=null){try{object[] act={previousTitle,true,0};C(app,"ISldWorks","ActivateDoc2",act);}catch{}}if(held)mutex.ReleaseMutex();}
    }
    string json=new JavaScriptSerializer().Serialize(report);File.WriteAllText(reportPath,json,new System.Text.UTF8Encoding(false));Console.WriteLine(json);
    return report.ContainsKey("ok")&&(bool)report["ok"]?0:1;
  }
}
