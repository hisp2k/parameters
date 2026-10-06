from pathlib import Path
from questionnaire_parser_v3 import extract_local
from questionnaire_engine_v3 import calculate_from_extraction
from cost_engine_v4 import CostMaster, PriceEvidence, LaborRate, calculate_cost, load_cost_master_xlsx

BASE = Path(__file__).resolve().parent
sample = (BASE / 'questionnaire_sample_belt_v3.xlsx').read_bytes()
ex = extract_local(sample, 'questionnaire_sample_belt_v3.xlsx')
pkg = calculate_from_extraction(ex, use_defaults=True)
assert pkg.status == 'calculated', pkg.missing_required

m = CostMaster()
m.settings.vat_pct = 22
m.settings.target_margin_pct = 20
m.prices.extend([
    PriceEvidence('steel_kg','Сталь конструкционная','кг',85,'corporate','test'),
    PriceEvidence('belt','Лента конвейерная B=650 мм','м',4800,'supplier_quote','test'),
    PriceEvidence('idler_set','Роликоопора грузовая','компл.',9500,'supplier_quote','test'),
    PriceEvidence('roller','Ролик холостой','шт',3200,'supplier_quote','test'),
    PriceEvidence('drum','Барабан','шт',55000,'formula_estimate','test'),
    PriceEvidence('motor','Электродвигатель','шт',42000,'online_market','test'),
    PriceEvidence('gearbox','Редуктор','шт',75000,'online_market','test'),
])
m.labor_rates['Общая производственная'] = LaborRate('Общая производственная', 1000, 'test')
res = calculate_cost(pkg.product_type, pkg.engineering, pkg.bom, m)
assert res.full_cost_rub > 0
assert res.selling_price_inc_vat_rub > res.full_cost_rub
assert res.price_coverage_pct >= 70
print('OK', pkg.product_type, round(res.full_cost_rub), round(res.selling_price_inc_vat_rub), res.price_coverage_pct)

loaded = load_cost_master_xlsx(BASE / 'cost_master_transporters_v4.xlsx')
assert loaded.settings.vat_pct == 22
assert 'belt_weld_h_m' in loaded.norms
print('MASTER OK', len(loaded.prices), len(loaded.norms), len(loaded.labor_rates))
