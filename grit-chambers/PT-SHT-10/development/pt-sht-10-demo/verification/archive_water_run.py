from pathlib import Path
import json,shutil,sys
root=Path('work/pt-sht-10-demo/Модель/2');d=json.loads((root/'2.info.json').read_text(encoding='utf-8'))
assert d['finished'],'Solver still running'
dest=Path('work/water_runs')/(sys.argv[1] if len(sys.argv)>1 else 'mesh1');dest.mkdir(parents=True,exist_ok=True)
for fn in ['2.info.json','2.info','2.xmlconfig','2.cpt.stdout','2.stdout','EFDsolver.log','2.fld','2.cpt','2.fbd','2.gdb','2.geom','project_results.xml','calculation_warnings.txt']:
 if (root/fn).exists():shutil.copy2(root/fn,dest/fn)
gs={x['goal']['name']:x['goal'] for x in d['goals']}
q=[gs[n+'_Q']['value'] for n in ['Inlet','MainOutlet','BottomOutlet']]
rho=gs['Inlet_MassFlow']['value']/q[0]
head=(gs['Inlet_TotalP']['value']-gs['MainOutlet_TotalP']['value'])/(rho*9.81)+.7195-.458
summary={'finished':d['finished'],'mesh':d['mesh'],'iteration':d['telemetry']['iteration'],'rho_kg_m3':rho,'Q_m3_h':[x*3600 for x in q],'imbalance_percent':100*abs(sum(q))/abs(q[0]),'inlet_to_main_total_head_drop_m':head,'goals':gs}
(dest/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='goals'},ensure_ascii=False),flush=True)
print('CONVERGENCE',[(n,g['progress'],g['criteria'],g['delta']) for n,g in gs.items() if g['use_in_convergence']],flush=True)
