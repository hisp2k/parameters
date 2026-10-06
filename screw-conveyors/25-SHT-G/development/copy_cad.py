import glob, os, shutil
base=r'C:\Users\adm\Desktop\25.SHT.G.00.00.00.00'
src=os.path.dirname(glob.glob(os.path.join(base,'**','*Транспортер.SLDASM'),recursive=True)[0])
dst=r'C:\Users\adm\Documents\Codex\2026-09-28\new-chat\outputs\25.SHT.G_parameterized'
for root,dirs,files in os.walk(src):
    rel=os.path.relpath(root,src)
    for fn in files:
        if fn.upper().endswith(('.SLDASM','.SLDPRT')):
            to=os.path.join(dst,rel,fn)
            os.makedirs(os.path.dirname(to),exist_ok=True)
            if not os.path.exists(to): shutil.copy2(os.path.join(root,fn),to)
print(src)
print(dst)
