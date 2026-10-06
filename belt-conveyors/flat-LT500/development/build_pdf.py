from pathlib import Path
from html import escape
from docx import Document
from docx.oxml.ns import qn
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,PageBreak,Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader
import subprocess, json, shutil
base=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2')
source=base/'outputs/Ленточный_транспортер/01_Техническое_задание/ЛТ500_Паспорт_концепции_R00.docx'
pdf=source.with_suffix('.pdf')
pdfmetrics.registerFont(TTFont('Arial',r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialBold',r'C:\Windows\Fonts\arialbd.ttf'))
styles={
 'Normal':ParagraphStyle('Normal',fontName='Arial',fontSize=10.2,leading=13.2,spaceAfter=7),
 'Title':ParagraphStyle('Title',fontName='ArialBold',fontSize=20,leading=24,spaceAfter=13),
 'Heading1':ParagraphStyle('H1',fontName='ArialBold',fontSize=14,leading=17,spaceBefore=8,spaceAfter=9,keepWithNext=True),
 'Heading2':ParagraphStyle('H2',fontName='ArialBold',fontSize=12,leading=15,spaceAfter=7,keepWithNext=True),
 'Cell':ParagraphStyle('Cell',fontName='Arial',fontSize=9.0,leading=11.2),
 'Head':ParagraphStyle('Head',fontName='ArialBold',fontSize=9.0,leading=11.2),
}
def clean(text):
 for c in ['\u2011','\u2013','\u2014']: text=text.replace(c,'-')
 return escape(text).replace('\n','<br/>')
doc=Document(source); story=[]
for node in doc.element.body:
 if node.tag==qn('w:p'):
  if any(el.get(qn('w:type'))=='page' for el in node.iter(qn('w:br'))): story.append(PageBreak()); continue
  text=''.join(el.text or '' for el in node.iter(qn('w:t')))
  if not text: continue
  st=node.find('./'+qn('w:pPr')+'/'+qn('w:pStyle')); name=st.get(qn('w:val')) if st is not None else 'Normal'
  story.append(Paragraph(clean(text),styles.get(name,styles['Normal'])))
 elif node.tag==qn('w:tbl'):
  rows=[]; widths=[]
  for i,row in enumerate(node.findall(qn('w:tr'))):
   cells=[]
   for cell in row.findall(qn('w:tc')):
    text='\n'.join(''.join(el.text or '' for el in p.iter(qn('w:t'))) for p in cell.findall(qn('w:p')))
    cells.append(Paragraph(clean(text),styles['Head' if i==0 else 'Cell']))
    if i==0:
     w=cell.find('./'+qn('w:tcPr')+'/'+qn('w:tcW')); widths.append(float(w.get(qn('w:w')))*0.05 if w is not None else 50)
   rows.append(cells)
  factor=(172*mm)/sum(widths); widths=[w*factor for w in widths]
  t=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
  t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#D9D9D9')),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E4EAF0')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F5F7F9')]),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
  story.extend([t,Spacer(1,8)])
def decoration(canvas,doc):
 canvas.saveState(); canvas.setFont('Arial',8); canvas.setFillColor(colors.HexColor('#475563'))
 canvas.drawString(20*mm,284*mm,'ЛТ500   Предварительная концепция   R00   04 октября 2026')
 canvas.drawString(20*mm,10*mm,'НЕ ДЛЯ ИЗГОТОВЛЕНИЯ'); canvas.drawRightString(192*mm,10*mm,str(doc.page)); canvas.restoreState()
out=SimpleDocTemplate(str(pdf),pagesize=(210*mm,297*mm),rightMargin=18*mm,leftMargin=20*mm,topMargin=20*mm,bottomMargin=17*mm,title='Ленточный транспортёр для отбросов с решёток ЛТ500 R00',author='Проект ЛТ500')
out.build(story,onFirstPage=decoration,onLaterPages=decoration)
qa=base/'work/pdf_qa'; qa.mkdir(exist_ok=True)
renderer=r'C:\Users\adm\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe'
subprocess.run([renderer,'-r','110','-png',str(pdf),str(qa/'page')],check=True,capture_output=True)
reader=PdfReader(pdf)
(base/'work/pdf_text_qa.json').write_text(json.dumps({'pages':len(reader.pages),'text_lengths':[len(p.extract_text()) for p in reader.pages]},ensure_ascii=False),encoding='utf8')
shutil.move(str(source),str(base/'work/ЛТ500_Паспорт_концепции_R00_непроверенный.docx'))
print(json.dumps({'pdf_pages':len(reader.pages),'rendered_images':len(list(qa.glob('page-*.png')))},ensure_ascii=False))
