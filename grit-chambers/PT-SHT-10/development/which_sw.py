import win32com.client as w
s=w.Dispatch('SldWorks.Application')
print('visible',s.Visible)
try:print('active',s.ActiveDoc.GetPathName)
except Exception as e:print('active error',e)
try:print('hwnd',s.Frame.GetHWnd())
except Exception as e:print('hwnd error',e)
