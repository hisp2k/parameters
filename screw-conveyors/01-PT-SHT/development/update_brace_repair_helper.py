from pathlib import Path
p=Path('work/fix_brace_clearance_20261005.py');s=p.read_text(encoding='utf-8')
s=s.replace('from brace_clearance_20261005 import create_clearance', 'from brace_bypass_20261005 import create_bypass\nfrom brace_clearance_20261005 import create_clearance')
s=s.replace('cut=create_clearance(sw,trial,center,direction)', 'bypass=create_bypass(sw,trial,center,direction)\n  cut=create_clearance(sw,trial,center,direction)')
s=s.replace("assert .9*old_volume<new_volume<old_volume,'Unexpected amount of material removed'", "assert old_volume<new_volume<2*old_volume,'Unexpected bypass volume'")
s=s.replace('planned.append((component,native,center,direction,cut,old_volume,new_volume,list(t)))','planned.append((component,native,center,direction,cut,bypass,old_volume,new_volume,list(t)))')
s=s.replace('for component,native,center,direction,cut,old_volume,new_volume,t in planned:\n  activate(native);live_parts.append(native)\n  live_cut=create_clearance(sw,native,center,direction)', '''for component,native,center,direction,cut,bypass,old_volume,new_volume,t in planned:
  activate(native);native.ForceRebuild3(False)
  inherited=abs(volume(native)-new_volume)<.001
  if inherited:
   live_cut={'inherited_from_mirrored_source':True};live_bypass={'inherited_from_mirrored_source':True,'strength_verified':False}
  else:
   assert abs(volume(native)-old_volume)<.001
   live_parts.append(native)
   live_bypass=create_bypass(sw,native,center,direction)
   live_cut=create_clearance(sw,native,center,direction)''')
s=s.replace("'cut':live_cut,'removed_mm3':old_volume-new_volume", "'cut':live_cut,'bypass':live_bypass,'inherited':inherited,'volume_change_mm3':new_volume-old_volume")
s=s.replace("for name in ['Проход корпуса — выборка для 55 градусов','Проход корпуса — профиль','Проход корпуса — поперечная плоскость','Ось корпуса 55 градусов — базовые точки']:", "for name in ['Проход корпуса — выборка для 55 градусов','Проход корпуса — профиль','Проход корпуса — поперечная плоскость','Ось корпуса 55 градусов — базовые точки']+[n+s for n in ['Полость обхода — нижний переход','Полость обхода — наружная ветвь','Полость обхода — верхний переход','Обход корпуса — нижний переход','Обход корпуса — наружная ветвь','Обход корпуса — верхний переход'] for s in ['', ' — профиль']]:")
p.write_text(s,encoding='utf-8')
