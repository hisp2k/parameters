from pathlib import Path
from math import sqrt
import sys
import ezdxf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent
OUT.mkdir(exist_ok=True)
pdfmetrics.registerFont(TTFont('Arial',r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold',r'C:\Windows\Fonts\arialbd.ttf'))

H=1000.0; TOP=900.0; BASE=850.0; T=2.0
SLANT=sqrt(H*H+((TOP-BASE)/2)**2)
VOL=(H-T)*(896**2+896*846+846**2)/3/1e9

def dxf(name, polylines, text=None):
    doc=ezdxf.new('R2010')
    doc.header['$INSUNITS']=4
    doc.layers.new('CUT',dxfattribs={'color':1})
    doc.layers.new('INFO',dxfattribs={'color':7})
    m=doc.modelspace()
    for points in polylines:
        m.add_lwpolyline(points,close=True,dxfattribs={'layer':'CUT'})
    for item in text or []:
        label, x,y=item
        m.add_text(label,dxfattribs={'height':18,'insert':(x,y),'layer':'INFO'})
    path=OUT/name
    doc.saveas(path)
    return path

def trap(top,bottom,x=0,y=0):
    d=(top-bottom)/2
    return [(x,y),(x+bottom,y),(x+bottom+d,y+SLANT),(x-d,y+SLANT)]

def square(size,x=0,y=0):
    return [(x,y),(x+size,y),(x+size,y+size),(x,y+size)]

def plate(x=0,y=0):
    return square(120,x,y)

def circle(cx,cy,r,n=64):
    from math import cos,sin,pi
    return [(cx+r*cos(2*pi*i/n),cy+r*sin(2*pi*i/n)) for i in range(n)]

dxf('cut_front_back_2mm.dxf',[trap(900,850)], [('FRONT/BACK x2 09G2S t=2',0,SLANT+35)])
dxf('cut_left_right_2mm.dxf',[trap(896,846)], [('LEFT/RIGHT x2 09G2S t=2',0,SLANT+35)])
dxf('cut_bottom_2mm.dxf',[square(850)], [('BOTTOM x1 09G2S t=2',0,880)])
plate_contours=[plate()]
for xx in (20,100):
    for yy in (30,90):
        plate_contours.append(circle(xx,yy,5.5))
dxf('cut_mount_plate_4mm.dxf',plate_contours,[('PLATE x4 09G2S t=4 4xD11',0,150)])

# Two 2500 x 1250 mm sheets for the walls, one for the bottom. 4 mm
# mounting plates use separate stock and therefore a separate layout.
for idx,pairs in enumerate([[(900,850),(900,850)],[(896,846),(896,846)]],1):
    contours=[trap(a,b,50+i*1150,50) for i,(a,b) in enumerate(pairs)]
    dxf(f'nest_walls_sheet_{idx}_2500x1250.dxf',contours,
        [(f'SHEET {idx} 2500x1250 / t2 / 09G2S',50,1180)])
dxf('nest_bottom_sheet_2500x1250.dxf',[square(850,50,50)],
    [('SHEET 3 2500x1250 / t2 / 09G2S',50,1180)])
mounts=[]
for j in range(4):
    x=50+j*160; y=50
    mounts.append(plate(x,y))
    for xx in (x+20,x+100):
        for yy in (y+30,y+90):
            mounts.append(circle(xx,yy,5.5))
dxf('nest_mounts_sheet_2500x1250.dxf',mounts,
    [('SHEET 4 2500x1250 / t4 / 09G2S',50,1180)])

P=OUT/'Чертежи_контейнер_075.pdf'
c=canvas.Canvas(str(P),pagesize=landscape(A3))
W,PH=landscape(A3)

def txt(x,y,s,size=11,bold=False):
    c.setFont('Arial-Bold' if bold else 'Arial',size)
    c.drawString(x,y,s)

def header(n,title):
    c.setLineWidth(1)
    c.rect(20,20,W-40,PH-40)
    c.line(20,PH-75,W-20,PH-75)
    txt(35,PH-49,title,18,True)
    txt(W-220,PH-49,f'Лист {n}/3    30.09.2026',10)
    c.line(20,77,W-20,77)
    txt(35,51,'КТБО-075 | 09Г2С | мм | Предварительный проект',11,True)
    txt(W-200,51,'Формат A3',10)

def path(points,close=False):
    p=c.beginPath(); p.moveTo(*points[0])
    for q in points[1:]: p.lineTo(*q)
    if close:p.close()
    c.drawPath(p)

def dim_h(x1,x2,y0,yd,label):
    c.setLineWidth(.6)
    c.line(x1,y0,x1,yd+4);c.line(x2,y0,x2,yd+4)
    c.line(x1,yd,x2,yd)
    for x,di in [(x1,1),(x2,-1)]:
        path([(x,yd),(x+di*7,yd+3),(x+di*7,yd-3)],True)
    c.setFillColorRGB(1,1,1);c.rect((x1+x2)/2-25,yd-6,50,12,fill=1,stroke=0)
    c.setFillColorRGB(0,0,0);txt((x1+x2)/2-19,yd-3,label,10,True)

def dim_v(y1,y2,x0,xd,label):
    c.setLineWidth(.6)
    c.line(x0,y1,xd-4,y1);c.line(x0,y2,xd-4,y2)
    c.line(xd,y1,xd,y2)
    for y,di in [(y1,1),(y2,-1)]:
        path([(xd,y),(xd-3,y+di*7),(xd+3,y+di*7)],True)
    c.saveState();c.translate(xd-6,(y1+y2)/2);c.rotate(90)
    c.setFillColorRGB(1,1,1);c.rect(-20,-3,40,13,fill=1,stroke=0)
    c.setFillColorRGB(0,0,0);txt(-14,0,label,10,True);c.restoreState()

header(1,'Контейнер для сбора мусора 0,75 м³ — сборочный чертеж')
s=.38; x=105; y=240
xb=x+(900-850)/2*s; xt=x+900*s
path([(xb,y),(xb+850*s,y),(xt,y+1000*s),(x,y+1000*s)],True)
for xc in [x+100*s,x+800*s]:
    c.circle(xc,y-100*s,80*s)
    c.rect(xc-22,y-8,44,8)
txt(x+118,y+1000*s+30,'Вид спереди',12,True)
dim_h(x,xt,y+1000*s,y+1000*s+18,'900')
dim_h(xb,xb+850*s,y,y-95,'850')
dim_v(y,y+1000*s,x,x-32,'1000')
dim_v(y-180*s,y,x,x-63,'180')

tx=600; ty=430; q=300
c.rect(tx,ty,q,q)
c.rect(tx+(900-850)/2/900*q,ty+(900-850)/2/900*q,850/900*q,850/900*q)
for xc in [tx+100/900*q,tx+800/900*q]:
    for yc in [ty+100/900*q,ty+800/900*q]:
        c.rect(xc-11,yc-11,22,22)
txt(tx,ty+q+24,'Вид сверху',12,True)
dim_h(tx,tx+q,ty+q,ty+q+16,'900')
dim_v(ty,ty+q,tx,tx-22,'900')
txt(600,385,'○ — колесо Ø160; □ — монтажная пластина 120×120',11)
txt(600,360,'Левая пара колес — неповоротные, правая — поворотные.',11)
txt(600,335,'Высота 1000 мм указана без колес.',11,True)
txt(600,310,'Общая расчетная высота модели: 1180 мм.',11)
txt(600,285,f'Полезный геометрический объем ≈ {VOL:.3f} м³.',11,True)
txt(600,260,'Колеса и кронштейны показаны упрощенно.',11)
c.showPage()

header(2,'Корпус и монтаж колес — размеры и спецификация')
txt(45,PH-110,'Корпус сварной, открытый; материал листовых деталей — 09Г2С.',13,True)
txt(45,PH-136,'Верх по наружному контуру 900×900; низ 850×850; высота стенки 1000.',12)
txt(45,PH-162,'Лист стенок и днища 2 мм. Уклон каждой стенки: 25 мм на высоту 1000 мм.',12)
txt(45,PH-188,f'Наклонная высота боковой заготовки: {SLANT:.3f} мм.',12)
txt(45,PH-214,'Днище приварить сплошным герметичным швом; углы проварить по всей высоте.',12)
txt(45,PH-240,'4 монтажные пластины 120×120×4 мм, отверстия 4×Ø11, межосевые 80×60 мм.',12)
txt(45,PH-266,'Центры пластин: ±350 мм от осей X и Z. Пластины приварить к днищу снизу.',12)
txt(45,PH-292,'Колеса: 2 неповоротных + 2 поворотных, номинальный диаметр 160 мм.',12)
txt(45,PH-318,'Привязку отверстий и допустимую нагрузку согласовать с выбранной моделью колес.',12)

rows=[('1','Передняя/задняя стенка','09Г2С, 2 мм','2'),
      ('2','Левая/правая стенка','09Г2С, 2 мм','2'),
      ('3','Днище','09Г2С, 2 мм','1'),
      ('4','Монтажная пластина','09Г2С, 4 мм','4'),
      ('5','Колесо неповоротное Ø160','покупное','2'),
      ('6','Колесо поворотное Ø160','покупное','2')]
xcols=[45,100,600,890,1060]
for i,(num,name,mat,qty) in enumerate([('№','Наименование','Материал / примечание','Кол.'),*rows]):
    yy=PH-385-i*33
    if i==0:
        c.setFillColorRGB(.9,.93,.96);c.rect(45,yy-9,1020,33,fill=1,stroke=0);c.setFillColorRGB(0,0,0)
    c.line(45,yy-10,1065,yy-10)
    for xx in xcols: c.line(xx,PH-361,xx,PH-385-6*33-10)
    txt(57,yy,num,10,i==0);txt(112,yy,name,10,i==0);txt(612,yy,mat,10,i==0);txt(902,yy,qty,10,i==0)
txt(45,110,'Поверхности очистить, загрунтовать и окрасить после сварки. Острые кромки притупить.',11)
c.showPage()

header(3,'Листовые детали и раскрой')
txt(45,PH-111,'Контуры DXF заданы в миллиметрах по номиналу детали; компенсация реза не внесена.',12,True)
txt(45,PH-138,'Стенка 1 — верх 900, низ 850, наклонная высота 1000,312 мм; 2 шт.',12)
txt(45,PH-165,'Стенка 2 — верх 896, низ 846, наклонная высота 1000,312 мм; 2 шт.',12)
txt(45,PH-192,'Днище — 850×850×2 мм; 1 шт. Пластина — 120×120×4 мм, 4×Ø11; 4 шт.',12)
txt(45,PH-219,'Стенки 2 устанавливаются между стенками 1. Стыки подгоняются перед сваркой.',12)
txt(45,PH-246,'Раскладка: листы 1–3 — 2500×1250×2 мм; лист 4 — 2500×1250×4 мм.',12)
txt(45,PH-273,'Детали на листах разнесены с технологическим зазором; лист 4 используется частично.',12)
sx=90; sy=235; sc=.21
path([(sx,sy),(sx+850*sc,sy),(sx+875*sc,sy+SLANT*sc),(sx-25*sc,sy+SLANT*sc)],True)
txt(67,sy+SLANT*sc+20,'Стенка 1, 2 шт.',11,True)
dim_h(sx-25*sc,sx+875*sc,sy+SLANT*sc,sy+SLANT*sc+15,'900')
dim_h(sx,sx+850*sc,sy,sy-18,'850')
sx2=430
path([(sx2,sy),(sx2+846*sc,sy),(sx2+871*sc,sy+SLANT*sc),(sx2-25*sc,sy+SLANT*sc)],True)
txt(sx2-20,sy+SLANT*sc+20,'Стенка 2, 2 шт.',11,True)
dim_h(sx2-25*sc,sx2+871*sc,sy+SLANT*sc,sy+SLANT*sc+15,'896')
dim_h(sx2,sx2+846*sc,sy,sy-18,'846')
sx3=760; sy3=250
c.rect(sx3,sy3,850*sc,850*sc)
txt(sx3,sy3+850*sc+20,'Днище, 1 шт.',11,True)
dim_h(sx3,sx3+850*sc,sy3,sy3-18,'850')
c.showPage();c.save()
print('PDF',P)
print('VOLUME_M3',VOL)
