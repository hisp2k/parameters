import glob, os, json, pythoncom
import win32com.client as win32

base=r'C:\Users\adm\Desktop\25.SHT.G.00.00.00.00'
patterns=['*02.00.00.01*Шнек*SLDPRT','*01.00.00.02*Желоб*SLDPRT','*01.00.00.03*Желоб*SLDPRT','*02.00.00.02*Вал*SLDPRT','*01.01.00.01*Пластина*SLDPRT']
sw=win32.Dispatch('SldWorks.Application'); sw.Visible=False
for pat in patterns:
    paths=glob.glob(os.path.join(base,'**',pat),recursive=True)
    if not paths: continue
    path=paths[0]
    e=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);w=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    m=sw.OpenDoc6(path,1,1,'',e,w)
    print('\nPART',os.path.basename(path),'status',e.value,w.value,flush=True)
    if not m: continue
    try: print('bbox',m.GetPartBox(True),flush=True)
    except Exception as ex: print('bbox error',ex)
    try: print('mass',m.Extension.CreateMassProperty().Mass,flush=True)
    except Exception as ex: print('mass error',ex)
    try: print('equations',m.GetEquationMgr.GetCount,flush=True)
    except Exception as ex: print('eq error',ex)
    f=m.FirstFeature
    n=0
    while f and n<100:
        print('FEATURE',f.Name, f.GetTypeName2,flush=True)
        try:
            d=f.GetFirstDisplayDimension
            j=0
            while d and j<30:
                try:
                    di=d.GetDimension2(0)
                    print('  DIM',di.FullName,di.SystemValue,flush=True)
                except Exception as ex:print('  DIM ERROR',repr(ex))
                d=f.GetNextDisplayDimension(d);j+=1
        except Exception:pass
        f=f.GetNextFeature;n+=1
