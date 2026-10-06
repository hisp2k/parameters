import copy
import json
from pathlib import Path
import unittest
from screw_engine import *


class ScrewTests(unittest.TestCase):
    def test_reference_reconciles_four_independent_cached_totals(self):
        r=calculate(REFERENCE)
        cells=source_data()['sheets']
        for key,sheet,cell in [('net_kg','Mass24_v10','B14'),('blank_kg','Mass24_v10','B15'),
                               ('person_h','Op24_v9','B20'),('machine_h','Op24_v9','C20')]:
            self.assertAlmostEqual(r[key],cells[sheet][cell]['value'],places=8)

    def test_invalid_geometry(self):
        for k,v in [('length',0),('pitch',float('nan')),('gap',float('inf')),('cut_fraction',0),
                    ('cut_fraction',1.01),('shaft_wall',60.5),('flight_inner',300),
                    ('full_flights',2.5),('work_length',6200),('shaft_length',6200),
                    ('flight_thickness',300),('waste',1.1),('diameter',True)]:
            with self.subTest(key=k,value=v),self.assertRaises(ValueError):
                calculate(REFERENCE|{k:v})

    def test_cut_fraction_is_mass_fraction_not_count_fraction(self):
        r=calculate(REFERENCE|{'cut_fraction':1.})
        self.assertAlmostEqual(r['masses'][1]['net_kg'],r['masses'][0]['net_kg']/20)

    def test_norm_scope(self):
        for k,v in [('diameter',320.),('pitch',250.),('flight_thickness',5.),('flight_material','AISI 316L')]:
            r=calculate(REFERENCE|{k:v})
            self.assertFalse(r['labor_complete'])
            self.assertIsNone(r['operations'][9]['person_h'])
        self.assertTrue(calculate(REFERENCE)['labor_complete'])

    def test_geometry_changes_mass_and_hours(self):
        r=calculate(REFERENCE|{'length':12100.,'work_length':12000.,'shaft_length':11994.,'full_flights':40})
        self.assertGreater(r['net_kg'],calculate(REFERENCE)['net_kg']*1.9)
        self.assertGreater(r['person_h'],calculate(REFERENCE)['person_h'])

    def safety(self,**updates):
        return dict(scope='Применим',guards='Да',restart='Да',emergency='Кнопки в голове и хвосте',
            layout='Один конвейер',moving_load='Нет',walkway=750.,height=2000.,
            location='Помещение без постоянных рабочих мест')|updates

    def statuses(self,p,s,attest=True):
        sig=signature({'geometry':p,'safety':s}) if attest else None
        return {r['code']:r['status'] for r in gost_checks(p,s,sig)}

    def test_emergency_ten_metre_boundary(self):
        self.assertEqual(self.statuses(REFERENCE|{'length':10000.},self.safety())['EMERGENCY'],'OK')
        self.assertEqual(self.statuses(REFERENCE|{'length':10001.},self.safety())['EMERGENCY'],'FAIL')
        self.assertEqual(self.statuses(REFERENCE|{'length':10001.},self.safety(),False)['EMERGENCY'],'FAIL')
        self.assertEqual(self.statuses(REFERENCE|{'length':10001.},self.safety(emergency='Остановка с любого места трассы'))['EMERGENCY'],'OK')

    def test_gost_walkways_and_height_boundaries(self):
        for layout,minimum in [('Один конвейер',750.),('Между параллельными',1000.),('Между полностью ограждёнными',700.)]:
            self.assertEqual(self.statuses(REFERENCE,self.safety(layout=layout,walkway=minimum))['WALKWAY'],'OK')
            self.assertEqual(self.statuses(REFERENCE,self.safety(layout=layout,walkway=minimum-1))['WALKWAY'],'FAIL')
        self.assertEqual(self.statuses(REFERENCE,self.safety(moving_load='Да'))['WALKWAY'],'FAIL')
        self.assertEqual(self.statuses(REFERENCE,self.safety(height=1999.))['HEADROOM'],'FAIL')
        self.assertEqual(self.statuses(REFERENCE,self.safety(height=0.))['HEADROOM'],'MISSING')

    def test_confirmation_invalidated_on_geometry_or_location_change(self):
        s=self.safety()
        sig=signature({'geometry':REFERENCE,'safety':s})
        for p,t in [(REFERENCE|{'diameter':320.},s),(REFERENCE,s|{'walkway':800.})]:
            rows={r['code']:r['status'] for r in gost_checks(p,t,sig)}
            self.assertEqual(rows['GUARD'],'MISSING')

    def test_out_of_scope_never_passes(self):
        self.assertEqual([r['code'] for r in gost_checks(REFERENCE,self.safety(scope='Не проверено'))],['GOST_SCOPE'])

    def test_missing_prices_and_bom_never_final(self):
        r=calculate(REFERENCE)
        data=source_data()
        c=partial_cost(r,{},data['buy'],{})
        self.assertIsNone(c['full_cost'])
        self.assertIsNone(c['selling_price'])
        self.assertEqual(c['known_direct'],0.)
        self.assertTrue(c['issues'])

    def test_cost_is_person_plus_machine_without_double_markup(self):
        r=calculate(REFERENCE)
        mat={m['name']:dict(price=100.,source='Счёт') for m in r['masses']}
        rates={op['resource']:dict(person_rate=1000.,machine_rate=2000.,source='Ручная ставка') for op in r['operations']}
        c=partial_cost(r,mat,[],rates,overhead=10.)
        self.assertAlmostEqual(c['known_with_overhead'],(r['blank_kg']*100+r['person_h']*1000+r['machine_h']*2000)*1.1)
        self.assertIsNone(c['full_cost'])
        with self.assertRaises(ValueError):
            partial_cost(r,mat,[],rates,margin=100.)

    def test_snapshot_roundtrip_and_nonfinite_rejected(self):
        raw=snapshot_bytes(REFERENCE,self.safety(),{},source_data()['buy'],{},dict(overhead=0.,margin=0.,vat=0.))
        obj=load_snapshot(raw)
        self.assertEqual(obj['inputs'],REFERENCE)
        self.assertEqual(calculate(obj['inputs'])['net_kg'],calculate(REFERENCE)['net_kg'])
        obj['inputs']['pitch']=float('nan')
        with self.assertRaises(ValueError):load_snapshot(json.dumps(obj).encode())


class ScrewUITests(unittest.TestCase):
    def test_screw_page_baseline_invalid_input_and_reset(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).parent/'transporter_app_local.py'),default_timeout=50).run()
        app.radio(key='equipment_workspace').set_value('Шнековый транспортер').run()
        self.assertFalse(app.exception)
        self.assertIn('294.087 кг',[m.value for m in app.metric])
        app.number_input(key='sc_p_diameter').set_value(320.).run()
        self.assertFalse(app.exception)
        self.assertTrue(any('неполная' in w.value for w in app.warning))
        app.number_input(key='sc_p_pitch').set_value(0.).run()
        self.assertFalse(app.exception)
        self.assertTrue(any('остановлен' in e.value for e in app.error))
        app.button(key='sc_reset').click().run()
        self.assertFalse(app.exception)
        self.assertIn('294.087 кг',[m.value for m in app.metric])
        app.checkbox(key='sc_auto').check().run()
        app.number_input(key='sc_p_length').set_value(12100.).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input(key='sc_p_full_flights').value,40)
        app.radio(key='equipment_workspace').set_value('Ленточные и роликовые').run()
        self.assertFalse(app.exception)
        app.radio(key='equipment_workspace').set_value('Шнековый транспортер').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input(key='sc_p_length').value,12100.)


if __name__=='__main__':unittest.main(verbosity=2)
