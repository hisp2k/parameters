exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
c=next(c for c in doc.GetComponents(True) if 'Шнековый вал' in c.Name2);eq=c.GetModelDoc2.GetEquationMgr
for i in range(eq.GetCount):print(i,eq.Equation(i),flush=True)
