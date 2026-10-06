exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
cfg='Сборочная — резьба условно';e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
parts={c.GetPathName:c.GetModelDoc2 for c in doc.GetComponents(False) if any(n in c.Name2 for n in ['Гайка М6','Гайка М8','Гайка М10'])}
for path,d in parts.items():
 nominal=next(n for n in [6,8,10] if f'Гайка М{n} ' in path)
 sw.ActivateDoc3(d.GetTitle,False,2,e);assert sw.ActiveDoc.GetPathName==path
 assert cfg not in list(d.GetConfigurationNames),path
 original=d.ConfigurationManager.ActiveConfiguration.Name
 assert d.ConfigurationManager.AddConfiguration2(cfg,f'М{nominal}: условная резьба для проверки сборки. Исходная конфигурация сохранена.','',0,'','Не использовать просвет для назначения размера сверления',True)
 faces=[f for b in d.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsCylinder];bore=min(faces,key=lambda f:f.GetSurface.CylinderParams[6]);axis=list(bore.GetSurface.CylinderParams[3:6]);k=max(range(3),key=lambda i:abs(axis[i]));assert abs(axis[k])>.999
 plane=['Справа','Сверху','Спереди'][k];d.ClearSelection2(True);assert d.FeatureByName(plane).Select2(False,0)
 sk=d.SketchManager;sk.InsertSketch(True);sk.AddToDB=True;sk.CreateCircleByRadius(0.,0.,0.,nominal/2000+.000025);sk.AddToDB=False;sk.InsertSketch(True)
 f=d.FeatureManager.FeatureCut4(False,False,False,1,1,.1,.1,False,False,False,False,0.,0.,False,False,False,False,False,False,True,False,False,False,0,0.,False,True);assert f and not f.GetErrorCode
 f.Name=f'Условная резьба М{nominal} — сборочный просвет'
 assert f.SetSuppression2(0,2,None);assert f.SetSuppression2(1,3,w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_BSTR,[cfg]))
 d.ForceRebuild3(False);assert d.Save3(1,e,q);print('part saved',Path(path).name,flush=True)
parents={doc.GetPathName:doc}
for c in doc.GetComponents(False):
 d=c.GetModelDoc2
 if d and d.GetType==2:parents[d.GetPathName]=d
for path,d in parents.items():
 cs=[c for c in d.GetComponents(True) if c.GetPathName in parts]
 if not cs:continue
 sw.ActivateDoc3(d.GetTitle,False,2,e)
 for c in cs:c.ReferencedConfiguration=cfg
 d.ForceRebuild3(False)
 for old in list(mates(d)):
  if not old.GetErrorCode:continue
  es=[old.GetSpecificFeature2.MateEntity(i) for i in (0,1)];fs=[]
  for i,ent in enumerate(es):
   if ent.Reference is not None:fs.append(old.GetDefinition.EntitiesToMate[i]);continue
   c=ent.ReferenceComponent;t=list(c.Transform2.ArrayData);p=list(ent.EntityParams)
   if old.GetTypeName2=='MateConcentric':
    options=[]
    for b in c.GetModelDoc2.GetBodies2(0,True):
     for face in b.GetFaces():
      if not face.GetSurface.IsCylinder:continue
      v=list(face.GetSurface.CylinderParams);a=[sum(v[j+3]*t[j*3+k] for j in range(3)) for k in range(3)];o=[sum(v[j]*t[j*3+k] for j in range(3))+t[9+k] for k in range(3)]
      if abs(sum(a[k]*p[k+3] for k in range(3)))<.999:continue
      delta=[o[k]-p[k] for k in range(3)];axial=sum(delta[k]*p[k+3] for k in range(3));perp=sum((delta[k]-axial*p[k+3])**2 for k in range(3))**.5
      options.append((perp,face))
    assert options and min(x[0] for x in options)<1e-6,(old.Name,c.Name2)
    fs.append(c.GetCorrespondingEntity(min(options,key=lambda x:x[0])[1]))
   elif old.GetTypeName2=='MateCoincident':
    options=plane_candidates(ent);assert options and options[0][0]<1e-6;fs.append(c.GetCorrespondingEntity(options[0][1]))
   else:raise RuntimeError('Unexpected missing mate '+old.Name)
  kind={'MateConcentric':1,'MateCoincident':0}[old.GetTypeName2];name=old.Name;align=old.GetDefinition.MateAlignment;old.SetSuppression2(0,1,None)
  data=d.CreateMateData(kind);data.MateAlignment=align;data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,fs)
  new=d.CreateMate(data);assert new and not new.GetErrorCode
  d.ClearSelection2(True);assert old.Select2(False,0);assert d.Extension.DeleteSelection2(0);new.Name=name+' — условная резьба'
 d.ForceRebuild3(False);errors=[(m.Name,m.GetErrorCode) for m in mates(d) if m.GetErrorCode];assert not errors,errors;assert d.Save3(1,e,q);print('parent saved',d.GetTitle,len(cs),flush=True)
sw.ActivateDoc3(doc.GetTitle,False,2,e);doc.ForceRebuild3(False);assert not [(m.Name,m.GetErrorCode) for m in mates(doc) if m.GetErrorCode];assert doc.Save3(1,e,q)
print('all nuts configured',flush=True)
