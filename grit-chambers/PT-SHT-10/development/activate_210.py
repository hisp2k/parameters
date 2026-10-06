import win32com.client as w,pythoncom
s=w.Dispatch('SldWorks.Application')
for d in s.GetDocuments or []:print(d.GetTitle,d.GetPathName)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
x=s.ActivateDoc2('PT-SHT-10-210L.SLDASM',True,e)
print('ACT',bool(x),e.value,s.ActiveDoc.GetTitle)
