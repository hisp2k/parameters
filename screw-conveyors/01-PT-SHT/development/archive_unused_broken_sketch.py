exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(doc.GetTitle,False,2,e)
f=doc.FirstFeature
while f and f.Name!='Эскиз1':f=f.GetNextFeature
assert f and f.GetErrorCode==51 and not f.GetChildren
sketch=f.GetSpecificFeature2
rows=[]
for s in sketch.GetSketchSegments:
 try:
  a=s.GetStartPoint2;b=s.GetEndPoint2;rows.append({'name':s.GetName,'type':s.GetType,'construction':bool(s.ConstructionGeometry),'start':[a.X,a.Y,a.Z],'end':[b.X,b.Y,b.Z]})
 except Exception:pass
archive={'feature':'Эскиз1','reason':'Неиспользуемый вспомогательный эскиз с тремя потерянными внешними связями; дочерние элементы отсутствуют. Исходная сборка сохранена в резервной копии.','segments':rows,'model_to_sketch':list(sketch.ModelToSketchTransform.ArrayData),'backup':str(base/'snapshots/20261004-all-interferences-before'/path.relative_to(base))}
(base/'archived_auxiliary_sketch_20261004.json').write_text(json.dumps(archive,ensure_ascii=False,indent=2),encoding='utf-8')
doc.ClearSelection2(True)
assert f.Select2(False,0) and doc.Extension.DeleteSelection2(0)
doc.ForceRebuild3(False);assert len(doc.GetComponents(False))==205
print('save',doc.Save3(1,e,q),e.value,q.value,flush=True)
