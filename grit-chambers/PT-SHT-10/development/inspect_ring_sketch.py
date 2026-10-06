import win32com.client as w
s=w.Dispatch('SldWorks.Application');d=s.ActiveDoc
print('doc',d.GetTitle,'box',d.GetPartBox(True))
f=d.FirstFeature
while f:
 print('feat',f.Name,f.GetTypeName2)
 if f.GetTypeName2=='ProfileFeature':
  sk=f.GetSpecificFeature2
  print('sketch',sk)
  for seg in sk.GetSketchSegments or []:
   print(' seg',seg.GetType,seg.GetCurve.CircleParams if hasattr(seg.GetCurve,'CircleParams') else None)
 f=f.GetNextFeature
