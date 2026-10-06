exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
trial=sw.GetOpenDocumentByName(str(Path('work/screw_collision_trial/Шнековый вал — контроль.SLDASM').resolve()))
d=next(c.GetModelDoc2 for c in trial.GetComponents(True) if 'Винт шнека' in c.Name2)
f=d.FirstFeature
while f:
 if f.GetTypeName2 in ['Helix','LPattern','LoftedBend','RefPlane','3DProfileFeature','ProfileFeature']:
  print('FEATURE',f.Name,f.GetTypeName2,flush=True)
  if f.GetTypeName2=='Helix': print('pitch',f.GetDefinition.Pitch,'height',f.GetDefinition.Height,'revolutions',f.GetDefinition.Revolution,flush=True)
  display=f.GetFirstDisplayDimension
  while display:
   dim=display.GetDimension2(0);print(dim.FullName,dim.SystemValue,flush=True);display=f.GetNextDisplayDimension(display)
 f=f.GetNextFeature
