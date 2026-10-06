from pathlib import Path
from collections import Counter
import sys
import pythoncom
import win32com.client as win32
import subprocess
import ezdxf
from ezdxf import bbox
from PIL import Image

root=Path(sys.argv[1]).resolve()
pdf=root/'Комплект_чертежей_КМ022_ЕСКД.pdf'
info=subprocess.run(['pdfinfo',str(pdf)],capture_output=True,text=True,check=True).stdout
assert 'Pages:           7' in info,info
print('PDF 7 pages')
subprocess.run(['pdftoppm','-f','1','-l','1','-scale-to','1600','-png','-singlefile',str(pdf),str(root.parent.parent/'work'/'pdf_022'/'final_page1')],check=True)

for name,qty in [('01_front_back_t1p5.dxf',1),('02_left_right_t1p5.dxf',1),('03_bottom_t1p5.dxf',1),('04_wheel_mount_t4.dxf',5)]:
    d=ezdxf.readfile(root/name)
    auditor=d.audit()
    assert not auditor.errors,(name,auditor.errors)
    assert d.header['$INSUNITS']==4
    m=d.modelspace()
    types=Counter(e.dxftype() for e in m if e.dxf.layer=='CUT')
    if 'mount' in name: assert types['CIRCLE']==4,types
    else: assert types['LWPOLYLINE']==1,types
    bb=bbox.extents((e for e in m if e.dxf.layer=='CUT'),fast=True)
    print('DXF',name,types,'bounds',tuple(round(v,3) for v in list(bb.extmin)[:2]),tuple(round(v,3) for v in list(bb.extmax)[:2]))

sw=win32.Dispatch('SldWorks.Application')
def open_doc(path,typ):
    e=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    w=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    d=sw.OpenDoc6(str(path),typ,1,'',e,w)
    assert d,(path,e.value,w.value)
    d.ForceRebuild3(False)
    print('SOLIDWORKS',path.name,'warnings',w.value,'errors',e.value)
    return d

asm=open_doc(root/'bin_022m3.SLDASM',2)
components=asm.GetComponents(False)
assert len(components)==9,len(components)
print('ASSEMBLY',len(components),'components')
for p in (root/'bin_022_assembly.SLDDRW',root/'bin_022_body.SLDDRW',root/'bin_022_mount_plate.SLDDRW'):
    open_doc(p,3)

err=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
sw.ActivateDoc2(asm.GetTitle,False,err)
asm.ShowNamedView2('*Isometric',7)
asm.ViewZoomtofit2()
large=root.parent.parent/'work'/'model_preview_large.png'
asm.SaveAs3(str(large),0,1)
assert large.exists() and large.stat().st_size>100000
Image.MAX_IMAGE_PIXELS=None
im=Image.open(large)
im.thumbnail((1600,1200))
im.save(root/'model_preview.png')
print('PREVIEW',im.size)
