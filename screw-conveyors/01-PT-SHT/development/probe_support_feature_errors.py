exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
import sys;sys.path.insert(0,str(base));import bridge
s=sw.GetOpenDocumentByName(str(bridge.FILES['support']))
for c in s.GetComponents(False):
 d=c.GetModelDoc2;print('C',c.Name2,c.GetPathName,flush=True)
 f=d.FirstFeature
 while f:
  if f.GetErrorCode:print('PART ERROR',f.Name,f.GetTypeName2,f.GetErrorCode,flush=True)
  f=f.GetNextFeature
f=s.FirstFeature
while f:
 if f.GetTypeName2 in ['ReferencePattern','MirrorCompFeat']:
  print('FEATURE',f.Name,f.GetTypeName2,f.GetErrorCode,flush=True);a=f.GetDefinition
  if a:
   for name in ['MirrorPlane','OppositeHandComponents','MirroredComponentFilenames','ComponentsToInstanceAlignToComponentOrigin','ComponentsToInstanceAlignToSelection','MirrorComponentsFolderLocation']:
    try:print(name,getattr(a,name),flush=True)
    except Exception as ex:print(name,str(ex)[:100],flush=True)
 f=f.GetNextFeature
