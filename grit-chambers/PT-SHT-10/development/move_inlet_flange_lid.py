import win32com.client as w,pythoncom
s=w.Dispatch('SldWorks.Application');a=s.ActiveDoc
c=next(c for c in a.GetComponents(False) or [] if c.Name2=='CFD_inlet_flange_lid-2')
t=c.Transform2;data=list(t.ArrayData)
print('before',list(c.GetBox(False,False)),data,flush=True)
data[9]=0.2515;data[10]=0.7195;data[11]=0.329
mat=s.GetMathUtility
t=mat.CreateTransform(tuple(data));c.Transform2=t
print('after',list(c.GetBox(False,False)),flush=True)
print('rebuild CAD',a.ForceRebuild3(False),flush=True)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);v=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
print('save',a.Save3(1,e,v),e.value,v.value,flush=True)
