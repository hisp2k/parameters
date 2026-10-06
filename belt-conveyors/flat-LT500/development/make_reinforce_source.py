from pathlib import Path
b=Path(__file__).parent;s=(b/'CreateSeatPrototype.cs').read_text(encoding='utf-8-sig').replace('class SeatPrototype','class ReinforcePrototype')
s=s.replace('2,0,-tc,0,.100','2,0,-tc-.012,0,.100').replace('.542-tc,-.582','.542-tc-.012,-.582')
needle='Wedge(app,doc,pls[0],z,a,tc,"SEAT_"+side);'
addition='''Tube(app,doc,pls[1],1,0,0,z,.120,.080,0,0,.012,.04-tc-.012,"CAP_"+side);
foreach(double sx in new double[]{-.053,.053})Tube(app,doc,pls[0],2,sx,-tc-.012,0,.006,.080,0,0,.080,z-.040,"WEB_"+side+(sx<0?"_MINUS":"_PLUS"));'''
assert needle in s;s=s.replace(needle,needle+'\n'+addition)
s=s.replace('Length==11,"Expected 11 bodies"','Length==17,"Expected 17 bodies"').replace('*(.542-tc)*1e-6','*(.542-tc-.012)*1e-6')
s=s.replace('+4*840.8230016469242*.3e-6;','+4*840.8230016469242*.3e-6+2*120*80*12e-9+4*6*80*80e-9;')
s=s.replace('"R05",replace','"R06",replace').replace('7 support bodies plus 4 reference rail stubs; two 100x60 tapered seats, min10 mm, 1.5deg downhill. Mid seating plane remains y40 mm above foot bottom y-590. No fixings, welds, belt loads or manufacturing approval.','13 support bodies plus 4 reference rail stubs: two 120x80x12 caps and four 6x80x80 side webs added to R05. Seat min10mm, 1.5deg. Rail seating plane y40mm, foot bottom y-590mm. Web weld beads, seat fixings, braces and anchors not modelled. Geometry only, NOT FOR MANUFACTURING.')
(b/'CreateReinforcePrototype.cs').write_text(s,encoding='utf8')
