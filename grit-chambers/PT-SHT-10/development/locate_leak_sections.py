exec(open('work/test_weld_repairs.py',encoding='utf-8').read().split("if '--save-repairs'")[0])
for lo,hi in [(0.,.01),(.01,.032),(.032,.036),(.036,.10),(.1,.30),(.30,.38),(.38,.386),(.386,.43),(.43,.50),(.50,.68),(.68,.76),(.76,.83),(.83,.834),(.834,.842)]:
 cut=cuboid(-.5,lo,-.5,.5,hi,.5)
 regions=op(bodies[0],cut,15901)
 print('SECTION',lo,hi,'REGIONS',len(regions),[(round(x.GetMassProperties(1.)[3],9),[round(v,5) for v in x.GetBodyBox()]) for x in regions],flush=True)
