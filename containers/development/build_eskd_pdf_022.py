from pathlib import Path
from math import sqrt
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent
OUT.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('Arial',r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialB',r'C:\Windows\Fonts\arialbd.ttf'))
pdf=OUT/'Комплект_чертежей_КМ022_ЕСКД.pdf'
c=canvas.Canvas(str(pdf),pagesize=landscape(A3))
c.setTitle('КМ.022 Комплект чертежей контейнера 0,22 м3')

W,H=420,297
TOP,BOT,HEIGHT,THK=600.0,590.0,620.0,1.5
SLANT=sqrt(HEIGHT**2+5**2)
VOL=(HEIGHT-THK)*(597**2+597*587+587**2)/3/1e9

def line(x1,y1,x2,y2,width=.25):
    c.setLineWidth(width*mm);c.line(x1*mm,y1*mm,x2*mm,y2*mm)

def rect(x,y,w,h,width=.5):
    c.setLineWidth(width*mm);c.rect(x*mm,y*mm,w*mm,h*mm,fill=0)

def poly(points,width=.7,closed=True):
    c.setLineWidth(width*mm)
    p=c.beginPath();p.moveTo(points[0][0]*mm,points[0][1]*mm)
    for x,y in points[1:]:p.lineTo(x*mm,y*mm)
    if closed:p.close()
    c.drawPath(p)

def txt(x,y,s,size=8,bold=False):
    c.setFont('ArialB' if bold else 'Arial',size)
    c.drawString(x*mm,y*mm,s)

def txt_center(x,y,s,size=8,bold=False):
    c.setFont('ArialB' if bold else 'Arial',size)
    c.drawCentredString(x*mm,y*mm,s)

def arrow(x,y,dx,dy):
    # Filled 2.7 mm arrowhead in the direction of the dimension line.
    px,py=-dy,dx
    p=c.beginPath();p.moveTo(x*mm,y*mm)
    p.lineTo((x+2.7*dx+.55*px)*mm,(y+2.7*dy+.55*py)*mm)
    p.lineTo((x+2.7*dx-.55*px)*mm,(y+2.7*dy-.55*py)*mm)
    p.close();c.setLineWidth(.2*mm);c.drawPath(p,stroke=1,fill=1)

def hdim(x1,x2,y_obj,y_dim,label):
    line(x1,y_obj,x1,y_dim+3);line(x2,y_obj,x2,y_dim+3)
    line(x1,y_dim,x2,y_dim)
    arrow(x1,y_dim,1,0);arrow(x2,y_dim,-1,0)
    c.setFillColorRGB(1,1,1)
    wid=max(9,len(label)*2.1)
    c.rect((x1+x2-wid)/2*mm,(y_dim-1.4)*mm,wid*mm,3.6*mm,stroke=0,fill=1)
    c.setFillColorRGB(0,0,0);txt_center((x1+x2)/2,y_dim-.2,label,7,True)

def vdim(y1,y2,x_obj,x_dim,label):
    line(x_obj,y1,x_dim-3,y1);line(x_obj,y2,x_dim-3,y2)
    line(x_dim,y1,x_dim,y2)
    arrow(x_dim,y1,0,1);arrow(x_dim,y2,0,-1)
    c.saveState();c.translate(x_dim*mm,((y1+y2)/2)*mm);c.rotate(90)
    c.setFillColorRGB(1,1,1);c.rect(-10*mm,-1.4*mm,20*mm,3.8*mm,stroke=0,fill=1)
    c.setFillColorRGB(0,0,0);c.setFont('ArialB',7);c.drawCentredString(0,0,label)
    c.restoreState()

def title_block(name,code,sheet,total,scale,material=''):
    # Form 1, 185 x 55 mm, lower right of the A3 frame.
    x,y=230,5
    rect(x,y,185,55,.7)
    line(295,5,295,60,.35)
    for yy in (15,25,35,45,55):line(230,yy,295,yy,.25)
    for xx in (237,247,270,285):line(xx,5,xx,60,.25)
    for yy in (15,30,45):line(295,yy,415,yy,.35)
    for xx in (325,355,385,400):line(xx,15,xx,30,.25)
    line(295,23,415,23,.25)
    txt(230.7,56.5,'Изм',6);txt(238,56.5,'Лист',6)
    txt(248,56.5,'№ докум.',6);txt(271,56.5,'Подп.',6)
    txt(286,56.5,'Дата',6)
    for yy,label in [(48,'Разраб.'),(38,'Пров.'),(28,'Т.контр.'),(18,'Н.контр.'),(8,'Утв.')]:
        txt(230.7,yy,label,6)
    txt(298,52,name,9,True)
    if material:txt(298,47,material,7)
    txt(298,36,code,9,True)
    for xx,label in [(297,'Лит.'),(327,'Масса'),(357,'Масштаб'),(387,'Лист'),(402,'Листов')]:
        txt(xx,25,label,6)
    txt_center(310,17,'—',7);txt_center(340,17,'—',7)
    txt_center(370,17,scale,8,True)
    txt_center(392.5,17,str(sheet),8,True)
    txt_center(407.5,17,str(total),8,True)
    txt(298,8,'КМ.022   •   30.09.2026',7)

def sheet(name,code,num,total=7,scale='1:4',material=''):
    rect(20,5,395,287,.7)
    txt(25,281,name,11,True)
    title_block(name,code,num,total,scale,material)

def trap_view(x,y,up,lo,sl,scale=4):
    a=up/scale;b=lo/scale;hh=sl/scale
    d=(a-b)/2
    poly([(x+d,y),(x+d+b,y),(x+a,y+hh),(x,y+hh)])
    return x,x+a,y,y+hh,x+d,x+d+b

# 1 — assembly drawing
sheet('Контейнер мусорный КМ.022. Сборочный чертеж','КМ.022.00.00 СБ',1)
x0,xt,y0,yt,xb1,xb2=trap_view(45,110,600,590,620,4)
for xx in (x0+20,xt-20):
    c.setLineWidth(.6*mm);c.circle(xx*mm,90*mm,(125/8)*mm)
    rect(xx-12.5,107,25,3,.3)
hdim(x0,xt,yt,274,'600')
hdim(xb1,xb2,y0,68,'590')
vdim(y0,yt,x0,31,'620')
vdim(90-125/8,y0,x0,23,'142,5')

tx,ty,sz=230,113,150
rect(tx,ty,sz,sz,.7)
rect(tx+1.25,ty+1.25,147.5,147.5,.25)
for xx in (tx+20,tx+130):
    for yy in (ty+20,ty+130):
        c.setDash(2*mm,1*mm)
        rect(xx-12.5,yy-12.5,25,25,.35)
        c.setDash()
hdim(tx,tx+sz,ty+sz,277,'600')
vdim(ty,ty+sz,tx,218,'600')
txt(235,103,'2 колеса неповоротных, 2 поворотных; Ø125.',7)
txt(235,95,'Номинальная емкость 0,22 м³; расчетная 0,2168 м³.',7)
txt(235,87,'Высота 620 — без учета колес.',7,True)
txt(235,79,'Колеса и вилки показаны условно.',7)
txt(235,71,'Пластины снизу показаны условно.',7)
c.showPage()

# 2 — body
sheet('Корпус сварной','КМ.022.00.01',2,scale='1:4',material='09Г2С, лист 1,5')
x0,xt,y0,yt,xb1,xb2=trap_view(55,95,600,590,620,4)
poly([(xb1+.4,y0+.4),(xb2-.4,y0+.4),(xt-.4,yt-.4),(x0+.4,yt-.4)],.25,False)
hdim(x0,xt,yt,269,'600')
hdim(xb1,xb2,y0,81,'590')
vdim(y0,yt,x0,39,'620')
tx,ty=225,100;rect(tx,ty,150,150,.7)
rect(tx+.75,ty+.75,148.5,148.5,.25)
hdim(tx,tx+150,ty+150,269,'600')
txt(225,88,'Толщина стенок и днища: 1,5 мм.',7,True)
txt(225,81,'Днище и углы проварить сплошным швом.',7)
txt(225,74,'Полезный геометрический объем ≈ 0,2168 м³.',7)
c.showPage()

# 3 and 4 — tapered wall blanks
for no,up,lo,code,name in [(3,600,590,'КМ.022.00.02','Стенка передняя/задняя'),
                            (4,597,587,'КМ.022.00.03','Стенка левая/правая')]:
    sheet(name,code,no,scale='1:4',material='09Г2С, лист 1,5')
    x0,xt,y0,yt,xb1,xb2=trap_view(120,95,up,lo,SLANT,4)
    txt(120,261,'Развертка, 2 шт.',8,True)
    hdim(x0,xt,yt,273,str(up))
    hdim(xb1,xb2,y0,81,str(lo))
    vdim(y0,yt,x0,102,f'{SLANT:.2f}'.replace('.',','))
    txt(293,231,'Материал: 09Г2С',8)
    txt(293,220,'Толщина: 1,5 мм',8)
    txt(293,209,'Количество: 2 шт.',8)
    txt(293,190,'Размер по высоте дан',7)
    txt(293,181,'в плоскости заготовки.',7)
    txt(293,160,'Резка по DXF.',7)
    txt(293,151,'Угловые стыки подогнать',7)
    txt(293,142,'перед сваркой.',7)
    c.showPage()

# 5 — bottom
sheet('Днище','КМ.022.00.04',5,scale='1:4',material='09Г2С, лист 1,5')
rect(125,99,147.5,147.5,.7)
txt(125,254,'Вид сверху, 1 шт.',8,True)
hdim(125,272.5,246.5,260,'590')
vdim(99,246.5,125,111,'590')
txt(296,225,'Лист 09Г2С, 1,5 мм.',8)
txt(296,214,'Кромки зачистить.',8)
txt(296,203,'Приварить по контуру.',8)
c.showPage()

# 6 — wheel mounting plate
sheet('Пластина крепления колес','КМ.022.00.05',6,scale='1:1',material='09Г2С, лист 4')
px,py=130,123;rect(px,py,100,100,.7)
for dx in (15,85):
    for dy in (15,85):c.setLineWidth(.4*mm);c.circle((px+dx)*mm,(py+dy)*mm,5.5*mm)
txt(px,232,'Вид сверху, 4 шт.',8,True)
hdim(px,px+100,py+100,241,'100')
vdim(py,py+100,px,116,'100')
hdim(px+15,px+85,py+15,py-13,'70')
vdim(py+15,py+85,px+15,px+115,'70')
txt(272,205,'4 отв. Ø11',9,True)
txt(272,193,'Шаг отверстий 70×70 мм.',8)
txt(272,181,'Центры пластин в сборке:',8)
txt(272,172,'±220 мм от осей корпуса.',8)
txt(272,150,'Перед изготовлением проверить',7)
txt(272,141,'присоединение выбранных колес.',7)
c.showPage()

# 7 — specification and technical requirements
sheet('Спецификация и технические требования','КМ.022.00.00 СП',7,scale='—')
cols=[25,42,193,296,330,390]
for xx in cols:line(xx,92,xx,263,.25)
for yy in [263,250,230,210,190,170,150,130,110,92]:line(25,yy,390,yy,.25)
for xx,s in [(27,'Поз.'),(45,'Наименование'),(195,'Обозначение / материал'),(298,'Кол.'),(333,'Примечание')]:
    txt(xx,254,s,7,True)
rows=[
    ('1','Стенка передняя/задняя','КМ.022.00.02','2','09Г2С 1,5'),
    ('2','Стенка левая/правая','КМ.022.00.03','2','09Г2С 1,5'),
    ('3','Днище','КМ.022.00.04','1','09Г2С 1,5'),
    ('4','Пластина колесная','КМ.022.00.05','4','09Г2С 4'),
    ('5','Колесо неповоротное Ø125','покупное','2','модель усл.'),
    ('6','Колесо поворотное Ø125','покупное','2','модель усл.'),
]
for i,row in enumerate(rows):
    yy=236-i*20
    for xx,val in zip([27,45,195,300,333],row):txt(xx,yy,val,7)
txt(25,83,'1. Емкость 0,22 м³ — номинальная; расчетный внутренний объем 0,2168 м³.',7)
txt(25,76,'2. Колеса Ø125 и отверстия пластин уточнить по каталогу выбранного поставщика.',7)
txt(25,69,'3. DXF в мм: CUT — рез, INFO/SHEET — справочные. Компенсация реза не задана.',7)
c.showPage();c.save()
print(pdf,VOL)
