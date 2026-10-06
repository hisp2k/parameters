"""Тех-Аэро: локальная веб-версия калькулятора, ревизия 5."""
import copy
from dataclasses import asdict
from datetime import date
import io
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from questionnaire_schema_v3 import FIELD_MAP, questionnaire_rows
from questionnaire_parser_v3 import ExtractedField, ExtractionResult, extract_local, extract_with_openai, _normalize_value
from questionnaire_engine_v3 import calculate_from_extraction, engineering_blockers
from cost_engine_v4 import (CostMaster, CostSettings, load_cost_master_xlsx, calculate_cost, PriceEvidence, LaborRate, validate_master,
                            infer_category, item_key, merge_online_prices, _f)
from web_support import (demo_extraction, fingerprint, load_project, project_bytes, export_xlsx,
                         BOM_LABELS, LABOR_LABELS, SOURCES, cost_structure)

BASE = Path(__file__).resolve().parent
st.set_page_config(page_title="Тех-Аэро · Калькулятор транспортеров", page_icon="⚙", layout="wide")
st.markdown('''<style>
.block-container{padding-top:2rem;max-width:1500px}
[data-testid="stSidebar"]{background:#eef3f6}
h1,h2,h3{color:#123747;letter-spacing:-.025em}
[data-testid="stMetric"]{border-top:3px solid #008e91;padding:14px 8px;background:#f1f7f8}
[data-testid="stMetricLabel"] p{font-size:14px}
.stButton>button[kind="primary"]{background:#006e75;border-color:#006e75}
</style>''', unsafe_allow_html=True)
st.caption("ТЕХ-АЭРО  /  ИНЖЕНЕРИЯ И СЕБЕСТОИМОСТЬ  /  ЛОКАЛЬНАЯ ВЕРСИЯ 6")
st.title("Калькулятор транспортеров")

workspace = st.radio("Раздел калькулятора", ["Ленточные и роликовые", "Шнековый транспортер"], horizontal=True, key="equipment_workspace")
if workspace == "Шнековый транспортер":
    from screw_ui import render_screw_app
    render_screw_app()
    st.stop()


def money(value):
    return f"{value:,.0f} ₽".replace(",", " ")


def set_source(extraction, saved=None):
    for key in list(st.session_state):
        if key.startswith(("input_", "prices_", "extras_", "online_", "cfg_", "rate_", "norms_")):
            del st.session_state[key]
    st.session_state.source = extraction
    st.session_state.saved = saved or {}
    st.session_state.kind = extraction.product_type or "Ленточный конвейер"
    for k, v in (saved or {}).get("settings", {}).items():
        st.session_state["cfg_" + k] = v
    if saved:
        st.session_state["cfg_rate"] = saved.get("rate", 0.0)
        st.session_state["cfg_complexity"] = saved.get("complexity", 1.0)


if "source" not in st.session_state:
    set_source(ExtractionResult({}, "Ленточный конвейер", []))

c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
c1.button("Новый расчёт", on_click=lambda: set_source(ExtractionResult({}, "Ленточный конвейер", [])), width="stretch")
c2.button("Пример: ленточный", on_click=lambda: set_source(demo_extraction("Ленточный конвейер")), width="stretch")
c3.button("Пример: рольганг", on_click=lambda: set_source(demo_extraction("Рольганг")), width="stretch")
c4.caption("Введите данные или начните с учебного примера. Расчёт обновляется при изменении полей.")

with st.expander("Загрузить опросный лист или сохранённый проект"):
    file = st.file_uploader("Документ", type=["xlsx", "xlsm", "csv", "pdf", "docx", "txt", "md", "json", "png", "jpg", "jpeg", "webp"])
    ai = st.checkbox("Использовать ИИ для распознавания документа", value=False)
    key = st.text_input("Ключ API для распознавания", type="password") if ai else ""
    model = st.text_input("Модель API для распознавания", value=os.environ.get("OPENAI_MODEL", "")) if ai else ""
    if ai:
        st.caption("По кнопке «Прочитать документ» файл отправляется в выбранный сервис API. Для обычного XLSX ключ не нужен.")
    if st.button("Прочитать документ", disabled=file is None):
        try:
            if file.name.lower().endswith(".json"):
                ex, saved = load_project(file.getvalue())
                set_source(ex, saved)
            else:
                if ai and not model.strip():
                    raise ValueError("Укажите модель API")
                with st.spinner("Чтение документа…"):
                    ex = extract_with_openai(file.getvalue(), file.name, key or None, model) if ai else extract_local(file.getvalue(), file.name)
                if not ex.fields:
                    raise ValueError("Поля не найдены. Заполните их вручную или используйте шаблон")
                set_source(ex)
            st.rerun()
        except Exception as exc:
            # A failed document must never leave an unrelated old estimate visible.
            set_source(ExtractionResult({}, None, [f"Документ не прочитан: {exc}"]))
            st.rerun()
    st.download_button("Скачать шаблон XLSX", (BASE / "questionnaire_template_transporters_v3.xlsx").read_bytes(), "Опросный_лист.xlsx")

with st.sidebar:
    st.header("Параметры стоимости")
    master_file = st.file_uploader("Справочник цен и ставок XLSX", type=["xlsx"], key="master_upload")
    try:
        master_data = master_file.getvalue() if master_file else (BASE / "cost_master_transporters_v4.xlsx").read_bytes()
        master = load_cost_master_xlsx(master_data)
    except Exception as exc:
        st.error(f"Справочник не прочитан: {exc}")
        st.stop()
    master_id = fingerprint(master_data.hex())
    if st.session_state.get("master_id") != master_id:
        previous_master_id = st.session_state.get("master_id")
        st.session_state.master_id = master_id
        for k in list(st.session_state):
            if k.startswith(("rate_", "norms_")):
                del st.session_state[k]
        if previous_master_id is not None:
            st.session_state.saved = {}
            for k, v in asdict(master.settings).items():
                st.session_state['cfg_' + k] = float(v)
    saved_master = st.session_state.saved.get('master')
    if saved_master:
        try:
            master = CostMaster(CostSettings(**saved_master['settings']),
                               {k: LaborRate(**v) for k, v in saved_master['labor_rates'].items()},
                               [PriceEvidence(**v) for v in saved_master['prices']], saved_master['norms'])
            validate_master(master)
        except (ValueError, TypeError, KeyError) as exc:
            st.error(f'Сохранённый справочник повреждён: {exc}')
            st.stop()
    st.caption("Закупочные цены вводятся без НДС. Ставки по умолчанию не назначаются.")
    rate = st.number_input("Временная ставка, ₽/нормо-ч", min_value=0.0, value=0.0, step=50.0, key="cfg_rate")
    if rate:
        st.caption("Ручное допущение для этого расчёта; корпоративные ставки имеют приоритет.")
    config = {"target_margin_pct": "Рентабельность в цене, %", "vat_pct": "НДС при продаже, %"}
    for k, label in config.items():
        setattr(master.settings, k, st.number_input(label, min_value=0.0, max_value=99.0 if k == "target_margin_pct" else 100.0,
                value=float(getattr(master.settings, k)), step=1.0, key="cfg_" + k))
    st.caption("Цена без НДС = себестоимость / (1 − рентабельность). Значение НДС взято из справочника и редактируется.")
    complexity = st.number_input("Коэффициент трудоёмкости", min_value=0.1, max_value=10.0, value=1.0, step=0.1, key="cfg_complexity")
    with st.expander("Накладные и резервы"):
        names = {"procurement_overhead_pct": "Закупочные накладные, % материалов", "production_overhead_pct": "Производственные накладные, % труда",
                 "contingency_pct": "Резерв расчёта, %", "packaging_pct": "Упаковка, %", "warranty_risk_pct": "Гарантия, %",
                 "commissioning_reserve_pct": "Резерв ПНР, %", "frame_steel_waste_pct": "Отход металла, %", "belt_length_reserve_pct": "Запас длины ленты, %"}
        for k, label in names.items():
            setattr(master.settings, k, st.number_input(label, 0.0, 100.0, float(getattr(master.settings, k)), 0.5, key="cfg_" + k))
        st.caption("Резервы начисляются на материалы, труд и накладные. Резерв ПНР — дополнительные затраты сверх операции испытания.")
    st.download_button("Скачать мастер-справочник", master_data, "cost_master_transporters_v4.xlsx")

extraction = st.session_state.source
kind = st.selectbox("Тип оборудования", ["Ленточный конвейер", "Рольганг"], key="kind")
if kind == "Ленточный конвейер":
    st.caption("Инженерная модель ленточного конвейера для сыпучего груза. Ширина и скорость подбираются по производительности.")
for warning in extraction.warnings:
    st.warning(warning)

input_tab, cost_tab, report_tab = st.tabs(["1 · Исходные данные", "2 · Комплектующие и стоимость", "3 · Проверки и выгрузка"])
fields = {"product_type": ExtractedField("product_type", kind, "Выбор пользователя", "", 1.0, "manual")}
invalid = []
metas = [m for m in questionnaire_rows("belt" if kind == "Ленточный конвейер" else "roller") if m.field_id != "product_type" and m.section != "Экономика"]


def field_widget(meta):
    prev = extraction.fields.get(meta.field_id)
    initial = prev.value if prev else meta.default
    label = meta.title + (f", {meta.unit}" if meta.unit else "")
    widget_key = "input_" + kind + "_" + meta.field_id
    if meta.dtype in {"enum", "bool"}:
        options = meta.allowed if meta.dtype == "enum" else [False, True]
        value = st.selectbox(label, options, index=options.index(initial) if initial in options else None,
                            key=widget_key, placeholder="Выберите значение", format_func=(lambda x: "Да" if x else "Нет") if meta.dtype == "bool" else str)
    else:
        raw = st.text_input(label, value="" if initial is None else str(initial), key=widget_key)
        value = _normalize_value(meta, raw, meta.unit, "")
        if raw.strip() and value is None:
            invalid.append(meta.title + ": некорректное значение")
    if value is not None and value != "":
        if prev and value == prev.value:
            fields[meta.field_id] = prev
        elif not prev and value == meta.default:
            fields[meta.field_id] = ExtractedField(meta.field_id, value, "Типовое допущение", "Значение прототипа, не корпоративная норма", 1.0, "default")
        else:
            fields[meta.field_id] = ExtractedField(meta.field_id, value, "Ручной ввод", "Проверено пользователем", 1.0, "manual")


with input_tab:
    st.subheader("Параметры заказа")
    important = [m for m in metas if m.required_for or m.field_id in {"project_name", "customer", "cargo_name", "cargo_length_mm", "cargo_width_mm", "cylinder_diameter_mm", "cylinder_axial_length_mm"}]
    cols = st.columns(2)
    for i, meta in enumerate(important):
        with cols[i % 2]:
            field_widget(meta)
    with st.expander("Конструкция и условия эксплуатации · типовые допущения", expanded=False):
        cols = st.columns(2)
        for i, meta in enumerate(m for m in metas if m not in important):
            with cols[i % 2]:
                field_widget(meta)
    st.caption("Изменения применяются автоматически. Допущения и происхождение данных доступны во вкладке «Проверки и выгрузка».")

verified = ExtractionResult(fields, kind, extraction.warnings, extraction.raw_text, extraction.extractor)
package = calculate_from_extraction(verified)
if invalid or package.status != "calculated":
    with input_tab:
        st.info("Для расчёта заполните или исправьте:")
        for msg in invalid + package.missing_required:
            st.write("• " + msg)
    with cost_tab:
        st.info("Стоимость появится после заполнения обязательных исходных данных.")
    st.stop()

# The reserve changes both procurement quantity and belt installation labor.
if kind == "Ленточный конвейер":
    package.bom[0]["Кол-во"] = round(2 * package.engineering["input"]["length_m"] * (1 + master.settings.belt_length_reserve_pct / 100), 2)
geometry_id = fingerprint(package.bom)
saved = st.session_state.saved
with cost_tab:
    st.subheader("Состав оборудования")
    st.caption("Это основные узлы из инженерной модели. Добавьте по проекту опоры, крепёж, ограждения, электрику и другие недостающие позиции.")
    with st.expander("Дополнительные материалы и комплектующие"):
        extra = st.data_editor(pd.DataFrame(saved.get("extra_rows") or [], columns=["Позиция", "Кол-во", "Ед.", "Параметр"]),
                              num_rows="dynamic", hide_index=True, key="extras_" + geometry_id,
                              column_config={"Кол-во": st.column_config.NumberColumn(min_value=0.0)})
        extra_rows = extra.fillna("").to_dict("records")
    valid_extra = []
    for row in extra_rows:
        if any(v != "" for v in row.values()):
            try:
                if not row["Позиция"] or not row["Ед."] or _f(row["Кол-во"]) <= 0:
                    raise ValueError("Укажите позицию, положительное количество и единицу измерения")
                valid_extra.append(row)
            except (ValueError, TypeError) as exc:
                st.error(f"Дополнительная позиция: {exc}")
                st.stop()
    package.bom.extend(valid_extra)
    identities = [item_key(row) for row in package.bom]
    if len(set(identities)) != len(identities):
        st.error("В составе повторяются одинаковые позиции с одинаковыми параметрами и единицами. Объедините их в одну строку с общим количеством.")
        st.stop()
    bom_id = fingerprint(package.bom)
    online_rows = st.session_state.get("online_" + bom_id, [])
    if online_rows:
        master = merge_online_prices(master, online_rows)
    initial_cost = calculate_cost(kind, package.engineering, package.bom, master, rate, complexity)
    edited_rows = []
    saved_prices = {r["Ключ"]: r for r in saved.get("price_rows", []) if r.get("Ручная", True)}
    for item, priced in zip(package.bom, initial_cost.priced_bom):
        identity = item_key(item)
        row = {"Ключ": identity, "Позиция": item["Позиция"], "Количество": item["Кол-во"], "Ед.": item["Ед."], "Параметр": item["Параметр"],
               "Цена без НДС, ₽": float(priced["unit_price_rub"]), "Источник": priced["source_name"] or SOURCES[priced["source_type"]], "Дата": priced.get("price_date", "")}
        if identity in saved_prices:
            for k in ["Цена без НДС, ₽", "Источник", "Дата"]:
                row[k] = saved_prices[identity].get(k, row[k])
        edited_rows.append(row)
    price_edits = st.data_editor(pd.DataFrame(edited_rows), hide_index=True, width="stretch",
        key="prices_" + bom_id + master_id + fingerprint(online_rows),
        disabled=["Ключ", "Позиция", "Количество", "Ед.", "Параметр"],
        column_config={"Ключ": None, "Цена без НДС, ₽": st.column_config.NumberColumn(min_value=0.0, format="%.2f")})
    price_rows = price_edits.fillna("").to_dict("records")
    for item, original, changed in zip(package.bom, initial_cost.priced_bom, price_rows):
        price = _f(changed["Цена без НДС, ₽"])
        if price != original["unit_price_rub"] or changed["Источник"] != (original["source_name"] or SOURCES[original["source_type"]]) or changed["Дата"] != original.get("price_date", "") or item_key(item) in saved_prices:
            # Explicit row edit overrides only this exact item and remains a manual assumption.
            master.prices = [p for p in master.prices if not (p.item_key == item_key(item))]
            manual = PriceEvidence(infer_category(item["Позиция"]), f"{item['Позиция']} {item['Параметр']}", item["Ед."], price,
                "manual", changed["Источник"] or "Ручной ввод", price_date=changed["Дата"] or date.today().isoformat(), item_key=item_key(item))
            # Isolate the edited item from category matching, including an explicit zero.
            item["Ручная цена"] = asdict(manual)
        changed['Ручная'] = 'Ручная цена' in item

    with st.expander("Ставки по операциям и нормы"):
        st.caption("Изменения действуют в текущем расчёте. Нормы прототипа требуют калибровки по хронометражу.")
        rate_rows = [{"Операция": x["operation"], "Ставка, ₽/ч": x["rate_rub_h"]} for x in initial_cost.labor]
        rate_edit = st.data_editor(pd.DataFrame(rate_rows), hide_index=True, disabled=["Операция"], key="rate_" + kind + str(rate) + master_id,
                                  column_config={"Ставка, ₽/ч": st.column_config.NumberColumn(min_value=0.0)})
        for row, old in zip(rate_edit.to_dict("records"), rate_rows):
            if row != old:
                master.labor_rates[row["Операция"]] = LaborRate(row["Операция"], _f(row["Ставка, ₽/ч"]), "Ручная ставка операции")
        if master.norms:
            norms = st.data_editor(pd.DataFrame([{"Норма": k, "Значение": v} for k, v in master.norms.items()]), hide_index=True,
                                   disabled=["Норма"], key="norms_" + master_id, column_config={"Значение": st.column_config.NumberColumn(min_value=0.0)})
            master.norms = {r["Норма"]: _f(r["Значение"]) for r in norms.to_dict("records")}

    with st.expander("Поиск недостающих рыночных цен · необязательно"):
        st.caption("Поиск отправляет только перечень позиций в API и выполняется по кнопке. Онлайн-цены сохраняют источник и дату, требуют проверки закупщиком.")
        market_key = st.text_input("Ключ API для поиска цен", type="password")
        market_model = st.text_input("Модель API для поиска цен", value=os.environ.get("OPENAI_MODEL", ""))
        if st.button("Найти отсутствующие цены"):
            try:
                if not market_model.strip():
                    raise ValueError("Укажите модель API")
                from online_price_agent_v4 import search_prices_for_bom
                missing = [b for b, p in zip(package.bom, initial_cost.priced_bom) if not p["unit_price_rub"] and not b.get("Ручная цена", {}).get("unit_price_rub")]
                if missing:
                    with st.spinner("Поиск цен…"):
                        found = search_prices_for_bom(missing, market_key or None, market_model)
                    st.session_state["online_" + bom_id] = found
                    st.rerun()
                else:
                    st.info("Все позиции уже оценены")
            except Exception as exc:
                st.error(f"Поиск не выполнен: {exc}")
    try:
        cost = calculate_cost(kind, package.engineering, package.bom, master, rate, complexity)
    except (ValueError, TypeError) as exc:
        st.error(f"Проверьте цены и ставки: {exc}")
        st.stop()
    st.subheader("Результат по введённому составу")
    complete = cost.price_coverage_pct == 100 and bool(cost.labor) and all(x["rate_rub_h"] > 0 for x in cost.labor) and not engineering_blockers(package.engineering)
    metrics = st.columns(4)
    metrics[0].metric("Материалы", money(cost.direct_materials_rub))
    metrics[1].metric("Труд", money(cost.direct_labor_rub))
    metrics[2].metric("Сумма с накладными", money(cost.full_cost_rub))
    metrics[3].metric("Цена состава с НДС", money(cost.selling_price_inc_vat_rub) if complete else "Не определена")
    st.progress(cost.price_coverage_pct / 100, text=f"Ценами заполнено {cost.price_coverage_pct:.0f}% позиций")
    if complete:
        st.success("Все строки и ставки заполнены. Проверьте полноту состава перед подготовкой ориентировочного предложения.")
        st.write(f"Цена без НДС: **{money(cost.selling_price_ex_vat_rub)}** · НДС: **{money(cost.vat_rub)}**")
        st.caption(f"Диапазон для введённого состава: {money(cost.price_low_inc_vat_rub)} — {money(cost.price_high_inc_vat_rub)}. Это оценочный резерв, не статистическая гарантия точности.")
    else:
        st.warning("Суммы учитывают только заполненные позиции и ставки. Стоимость всего оборудования ещё не определена.")
    st.dataframe(pd.DataFrame(cost_structure(cost)), hide_index=True, width="stretch")

with input_tab:
    st.subheader("Предварительный инженерный подбор")
    cols = st.columns(4)
    if kind == "Ленточный конвейер":
        b = package.engineering["belt"]
        for c, label, val in zip(cols, ["Ширина ленты", "Скорость", "Двигатель", "Профиль балки"],
                                 [f"{b['selected_width_mm']} мм", f"{b['speed_mps']:.2f} м/с", f"{b['selected_motor_kw']} кВт", package.engineering["frame"]["section"]]):
            c.metric(label, val or "Не подобран")
    else:
        r = package.engineering["roller"]
        for c, label, val in zip(cols, ["Ролик", "Шаг", "Количество", "Грузов одновременно"],
                                 [f"Ø{r['selected_diameter_mm']} × {r['selected_roller_length_mm']} мм", f"{r['selected_pitch_mm']} мм", r['roller_count'], r['simultaneous_loads']]):
            c.metric(label, val)
    for msg in engineering_blockers(package.engineering):
        st.error(msg)
    st.info("Комплектующие, цены и себестоимость находятся во вкладке «2 · Комплектующие и стоимость».")

with report_tab:
    st.subheader("Что проверить перед предложением")
    for warning in dict.fromkeys(package.warnings + cost.warnings):
        st.write("• " + warning)
    with st.expander("Происхождение данных и допущения"):
        audit = pd.DataFrame(package.audit)
        if not audit.empty:
            audit["Значение"] = audit["Значение"].astype(str)
        st.dataframe(audit, hide_index=True, width="stretch")
    with st.expander("Источники цен и трудоёмкость"):
        st.dataframe(pd.DataFrame(cost.priced_bom).rename(columns=BOM_LABELS), hide_index=True, width="stretch")
        st.dataframe(pd.DataFrame(cost.labor).rename(columns=LABOR_LABELS), hide_index=True, width="stretch")
    with st.expander("Подробные инженерные результаты"):
        st.json(package.engineering)
    st.download_button("Скачать расчёт Excel", export_xlsx(package, cost), "Калькуляция_транспортера.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
    st.download_button("Сохранить проект JSON", project_bytes(verified, master.settings, rate, complexity, price_rows, extra_rows, master), "Проект_транспортера.json", "application/json")
    st.download_button("Скачать полный отчёт JSON", json.dumps({"package": asdict(package), "cost": asdict(cost)}, ensure_ascii=False, indent=2, allow_nan=False).encode(), "Отчёт_транспортера.json", "application/json")
