from pathlib import Path
p=Path('work/fix_brace_clearance_20261005.py');s=p.read_text(encoding='utf-8')
s=s.replace('inherited=abs(volume(native)-new_volume)<.001', "f=native.FirstFeature;mirrored=False\n  while f:\n   mirrored=mirrored or f.GetTypeName2=='MirrorStock';f=f.GetNextFeature\n  actual_volume=volume(native)\n  print('Live part',component.Name2,'volume',actual_volume,'original/trial',old_volume,new_volume,'mirror',mirrored,flush=True)\n  inherited=mirrored and abs(actual_volume-new_volume)<new_volume*.001")
s=s.replace('assert len(native.GetBodies2(0,True))==1 and abs(volume(native)-new_volume)<.001', 'assert len(native.GetBodies2(0,True))==1 and abs(volume(native)-new_volume)<(new_volume*.001 if inherited else .001)')
s=s.replace("'after_volume_mm3':new_volume", "'trial_volume_mm3':new_volume,'after_volume_mm3':volume(native)")
p.write_text(s,encoding='utf-8')
