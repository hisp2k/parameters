from pathlib import Path
from math import sqrt
import sys
import ezdxf

OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent
OUT.mkdir(parents=True,exist_ok=True)
H=620.0; TOP=600.0; BOTTOM=590.0; THK=1.5
SLANT=sqrt(H*H+((TOP-BOTTOM)/2)**2)

def trap(upper,lower,x=0,y=0):
    d=(upper-lower)/2
    return [(x,y),(x+lower,y),(x+lower+d,y+SLANT),(x-d,y+SLANT)]

def square(size,x=0,y=0):
    return [(x,y),(x+size,y),(x+size,y+size),(x,y+size)]

def write(name,contours,circles=(),label='',sheet=None):
    d=ezdxf.new('R2010')
    d.header['$INSUNITS']=4
    d.layers.new('CUT',dxfattribs={'color':1})
    d.layers.new('INFO',dxfattribs={'color':7})
    d.layers.new('SHEET',dxfattribs={'color':8})
    m=d.modelspace()
    for poly in contours:
        m.add_lwpolyline(poly,close=True,dxfattribs={'layer':'CUT'})
    for x,y,r in circles:
        m.add_circle((x,y),r,dxfattribs={'layer':'CUT'})
    if sheet:
        m.add_lwpolyline(square(sheet[0]),close=True,dxfattribs={'layer':'SHEET'}) if sheet[0]==sheet[1] else m.add_lwpolyline([(0,0),(sheet[0],0),(sheet[0],sheet[1]),(0,sheet[1])],close=True,dxfattribs={'layer':'SHEET'})
    if label:
        m.add_text(label,dxfattribs={'layer':'INFO','height':16,'insert':(25,920 if sheet else SLANT+35)})
    p=OUT/name; d.saveas(p); print(p.name)

write('01_front_back_t1p5.dxf',[trap(600,590)],label='FRONT BACK x2 09G2S 1.5mm')
write('02_left_right_t1p5.dxf',[trap(597,587)],label='LEFT RIGHT x2 09G2S 1.5mm')
write('03_bottom_t1p5.dxf',[square(590)],label='BOTTOM x1 09G2S 1.5mm')
holes=[(x,y,5.5) for x in (15,85) for y in (15,85)]
write('04_wheel_mount_t4.dxf',[square(100)],holes,label='MOUNT x4 09G2S 4mm 4xD11')

# Manufacturing nests: CUT contains only part contours; SHEET is a guide.
for i,(up,lo) in enumerate([(600,590),(597,587)],1):
    write(f'nest_{i}_walls_1500x1000.dxf',
          [trap(up,lo,35,35),trap(up,lo,735,35)],
          label=f'SHEET {i} 1500x1000 09G2S t1.5',sheet=(1500,1000))
write('nest_3_bottom_1500x1000.dxf',[square(590,35,35)],
      label='SHEET 3 1500x1000 09G2S t1.5',sheet=(1500,1000))
pcs=[square(100,35+j*140,35) for j in range(4)]
hh=[(35+j*140+x,35+y,5.5) for j in range(4) for x in (15,85) for y in (15,85)]
write('nest_4_mounts_1500x1000.dxf',pcs,hh,
      label='SHEET 4 1500x1000 09G2S t4',sheet=(1500,1000))
