import json
import sys
from pathlib import Path
sys.path.insert(0, r'C:\Users\adm\Documents\Codex\2026-09-28\new-chat\outputs\transport_questionnaire')
from app import Questionnaire
from validation import validate

raw = {
    'general': {'working_length_mm':'3000','inclination_deg':'10','throughput_m3_h':'10','batch_volume_m3':'1'},
    'screw': {'diameter_mode':'manual','diameter_mm':'200','pitch_mode':'gost','pitch_mm':'200'},
    'inlet_count':'2','inlets_simultaneous':'yes',
    'inlets': [
        {'position_mm':'500','shape':'rectangular','length_mm':'200','width_mm':'200','flow_m3_h':'6'},
        {'position_mm':'1200','shape':'round','diameter_mm':'150','flow_m3_h':'4'},
    ],
    'outlet_count':'1','outlets_simultaneous':'',
    'outlets':[{'position_mm':'2750','shape':'round','diameter_mm':'150','direction':'down'}],
    'material': {'name':'Тестовый материал','source':'manual','bulk_density_kg_m3':'1000',
                 'max_lump_mm':'10','max_moisture_pct':'5','abrasion':'low','flowability':'free',
                 'temperature_c':'25','corrosion':'no'},
    'installation': {'height_source':'manual','axis_height_mm':'1000','supports_free':'yes',
                     'environment':'inside'},
    'operation': {'duty':'continuous','hours_per_day':'8','starts_per_hour':'2',
                  'loaded_start':'yes','reverse':'no','blockage':'no','hopper':'no',
                  'design_life_h':'8500'},
}
normalized, errors, warnings = validate(raw)
assert not errors, errors
assert normalized['inlets'][1]['flow_m3_h'] == 4
assert normalized['screw']['pitch_mm'] == 200
print('VALID:',len(errors),'errors',len(warnings),'warnings')

bad = json.loads(json.dumps(raw))
bad['screw']['diameter_mm']='50'
bad['inlets'][0]['position_mm']='20'
bad['inlets'][1]['flow_m3_h']='5'
_, errors, _ = validate(bad)
assert any('нестандартного диаметра' in e for e in errors), errors
assert any('выходит за рабочую длину' in e for e in errors), errors
assert any('Сумма расходов' in e for e in errors), errors
print('INVALID:',len(errors),'expected errors')

q=Questionnaire()
q.withdraw()
q.apply(raw)
assert len(q.rows_inlet)==2
assert len(q.rows_outlet)==1
recollected=q.collect()
assert recollected['inlets'][1]['shape']=='round'
assert recollected['inlets'][0]['flow_m3_h']=='6'
q.vars['inlet_count'].set('7')
assert len(q.rows_inlet)==7
assert q.rows_inlet[0].vars['position_mm'].get()=='500'
q.rows_inlet[6].vars['position_mm'].set('2500')
q.vars['inlet_count'].set('2')
q.vars['inlet_count'].set('7')
assert q.rows_inlet[6].vars['position_mm'].get()=='2500'
q.vars['outlet_count'].set('2')
assert len(q.rows_outlet)==2
q.apply(raw)
q.vars['inlet_count'].set('7')
assert q.rows_inlet[6].vars['position_mm'].get()==''
q.apply(raw)
from tkinter import filedialog, messagebox
saved_path=Path(r'C:\Users\adm\Documents\Codex\2026-09-28\new-chat\work\saved_transport_input.json')
filedialog.asksaveasfilename=lambda **kwargs: str(saved_path)
messagebox.showinfo=lambda *args, **kwargs: None
messagebox.showwarning=lambda *args, **kwargs: None
messagebox.showerror=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('Save should not show errors'))
q.save_validated()
saved=json.loads(saved_path.read_text(encoding='utf-8'))
assert saved['status']=='validated_questionnaire'
assert saved['inputs']['general']['working_length_mm']==3000
assert len(saved['inputs']['inlets'])==2
q.apply(saved['inputs'])
assert q.collect()['inlets'][1]['position_mm']=='1200.0'
q.destroy()
print('UI: rows, save and reload OK')
