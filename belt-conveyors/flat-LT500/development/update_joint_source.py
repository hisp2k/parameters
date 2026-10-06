from pathlib import Path
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');p=B/'work/CreateJointPrototype.cs';s=p.read_text(encoding='utf-8-sig').replace('.003,.006,.298,start<0?-.3:.002,nm)', '.003,.006,.294,start<0?-.3:.006,nm)').replace('Nominal gap4mm','Nominal gap12mm')
# Preserve only the just-created, clean R07 prototype from this operation before replacing it.
needle=r'R(output.StartsWith(@"C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2\outputs\")&&!File.Exists(output),"Invalid new destination");'
assert needle in s
s=s.replace(needle,r'''if(File.Exists(output)){R(output.EndsWith("ЛТ500_Крепление_седел_и_стык_R07.SLDPRT"),"Cannot replace other file");object prior=C(app,"ISldWorks","GetOpenDocumentByName",output);if(prior!=null){R(!Convert.ToBoolean(C(prior,"IModelDoc2","GetSaveFlag")),"Own prototype has unsaved edits");C(app,"ISldWorks","CloseDoc",C(prior,"IModelDoc2","GetTitle"));}File.Move(output,@"C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2\work\joint_gap4_superseded.SLDPRT");}'''+needle)
needle='static List<object> Interferences(object doc){object[] bs=(object[])C(doc,"IPartDoc","GetBodies2",0,false);'
assert needle in s
s=s.replace(needle,r'''static List<object> Interferences(object doc){return Interferences(doc,null,0d);}static List<object> Interferences(object doc,object app,double dx){object[] bs=(object[])C(doc,"IPartDoc","GetBodies2",0,false);if(dx!=0){object mu=C(app,"ISldWorks","GetMathUtility");object tr=C(mu,"IMathUtility","CreateTransform",new object[]{new double[]{1,0,0,0,1,0,0,0,1,dx,-dx*Math.Tan(1.5*Math.PI/180),0,1,0,0,0}});for(int k=0;k<bs.Length;k++){string name=Convert.ToString(G(bs[k],"IBody2","Name"));object copy=C(bs[k],"IBody2","Copy");S(copy,"IBody2","Name",name);if(name.Contains("MODULE_OUT")||name.StartsWith("RAIL_HOLE_")&&name.EndsWith("_OUT"))R(Convert.ToBoolean(C(copy,"IBody2","ApplyTransform",tr)),"Stroke transform failed");bs[k]=copy;}}''')
needle='report["reopened_intersections"]=Interferences(doc);'
assert needle in s
s=s.replace(needle,needle+'report["stroke_minus6_intersections"]=Interferences(doc,app,-.006);report["stroke_plus6_intersections"]=Interferences(doc,app,.006);')
p.write_text(s,encoding='utf-8-sig')
print('R07 gap12 and temporary-body stroke checks prepared')
