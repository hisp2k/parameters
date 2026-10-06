"""Questionnaire, CAD link, and preliminary shaft FEA (Python/Tkinter).

Run with: python app.py
"""

from __future__ import annotations

import json
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from validation import GOST_PITCHES_MM, validate
from cad_bridge import apply_to_model, default_model_dir, prepare
from strength import prepare_strength, run_strength as run_strength_study
from purchased import baseline_items, validate_items, write_specification
from material_catalog import cards, get_card
from support_layout import body_support_layout


class ScrollFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, background="#f7f8fa")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.body = ttk.Frame(self.canvas, padding=16)
        self.window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.window, width=e.width))
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


def field(parent, row, label, variable, *, width=22):
    ttk.Label(parent, text=label, wraplength=450, justify="left").grid(
        row=row, column=0, sticky="w", padx=(0, 12), pady=5)
    entry = ttk.Entry(parent, textvariable=variable, width=width)
    entry.grid(row=row, column=1, sticky="w", pady=5)
    return entry


def choices(parent, row, label, variable, items):
    ttk.Label(parent, text=label, wraplength=450, justify="left").grid(
        row=row, column=0, sticky="w", padx=(0, 12), pady=5)
    holder = ttk.Frame(parent)
    holder.grid(row=row, column=1, sticky="w", pady=5)
    widgets = []
    for title, code in items:
        button = ttk.Radiobutton(holder, text=title, value=code, variable=variable)
        button.pack(side="left", padx=(0, 12))
        widgets.append(button)
    return widgets


class OpeningRow(ttk.LabelFrame):
    def __init__(self, parent, index: int, kind: str):
        super().__init__(parent, text=f"{'Загрузка' if kind == 'inlet' else 'Выгрузка'} {index}", padding=10)
        self.kind = kind
        self.vars = {key: tk.StringVar() for key in
                     ("position_mm", "shape", "diameter_mm", "length_mm", "width_mm",
                      "flow_m3_h", "direction", "side")}
        self.columnconfigure(1, weight=1)
        field(self, 0, "Центр от начала рабочей части, мм", self.vars["position_mm"])
        choices(self, 1, "Форма", self.vars["shape"],
                [("Круглая", "round"), ("Прямоугольная", "rectangular")])
        self.diameter = field(self, 2, "Диаметр, мм", self.vars["diameter_mm"])
        self.axial = field(self, 3, "Длина вдоль желоба, мм", self.vars["length_mm"])
        self.width = field(self, 4, "Ширина, мм", self.vars["width_mm"])
        row = 5
        if kind == "outlet":
            choices(self, row, "Направление", self.vars["direction"],
                    [("Вниз", "down"), ("Вбок", "side")])
            self.side_buttons = choices(self, row + 1, "Если вбок", self.vars["side"],
                                        [("Влево", "left"), ("Вправо", "right")])
            row += 2
            self.vars["direction"].trace_add("write", lambda *_: self.update_fields())
        else:
            self.side_buttons = []
        self.flow = field(self, row, "Расход через эту точку, м³/ч", self.vars["flow_m3_h"])
        self.vars["shape"].trace_add("write", lambda *_: self.update_fields())
        self.update_fields()

    def update_fields(self):
        shape = self.vars["shape"].get()
        self.diameter.configure(state="normal" if shape == "round" else "disabled")
        state = "normal" if shape == "rectangular" else "disabled"
        self.axial.configure(state=state)
        self.width.configure(state=state)
        for button in self.side_buttons:
            button.configure(state="normal" if self.vars["direction"].get() == "side" else "disabled")

    def set_flow_enabled(self, enabled: bool):
        self.flow.configure(state="normal" if enabled else "disabled")

    def collect(self):
        return {key: var.get().strip() for key, var in self.vars.items()}

    def apply(self, data):
        for key, var in self.vars.items():
            value = data.get(key)
            var.set("" if value is None else str(value))
        self.update_fields()


class Questionnaire(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Опросный лист — шнековый транспортёр")
        self.geometry("1040x780")
        self.minsize(850, 620)
        self.configure(background="#e9edf2")
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TRadiobutton", font=("Segoe UI", 10))
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("TButton", padding=7, font=("Segoe UI", 10))
        self.vars = {}
        self.rows_inlet = []
        self.rows_outlet = []
        self._row_cache = {"inlet": [], "outlet": []}
        self._building = False
        self._make_header()
        self.book = ttk.Notebook(self)
        self.book.pack(fill="both", expand=True, padx=14, pady=8)
        self._make_general_tab()
        self._make_inlets_tab()
        self._make_outlets_tab()
        self._make_material_tab()
        self._make_operation_tab()
        self._make_strength_tab()
        self._make_purchased_tab()
        self._make_footer()

    def v(self, key, default=""):
        var = tk.StringVar(value=default)
        self.vars[key] = var
        return var

    def _make_header(self):
        head = ttk.Frame(self, padding=(16, 14, 16, 4))
        head.pack(fill="x")
        ttk.Label(head, text="Параметры шнекового транспортёра",
                  font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(head, text="Введите исходные данные, проверьте их и сохраните в JSON. "
                  "Доступны связь шага шнека с SolidWorks, предварительный расчёт вала и перечень покупных изделий.").pack(anchor="w", pady=(5, 0))

    def _tab(self, title):
        tab = ScrollFrame(self.book)
        self.book.add(tab, text=title)
        tab.body.columnconfigure(0, weight=1)
        return tab.body

    def _make_general_tab(self):
        body = self._tab("1. Основное и шнек")
        main = ttk.LabelFrame(body, text="Основные параметры", padding=12)
        main.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        main.columnconfigure(1, weight=1)
        length_var = self.v("working_length_mm")
        field(main, 0, "Длина рабочей части желоба, мм (500–25 000)", length_var)
        field(main, 1, "Угол наклона, градусы (0–20)", self.v("inclination_deg", "0"))
        field(main, 2, "Суммарная производительность, м³/ч", self.v("throughput_m3_h"))
        field(main, 3, "Общий объём разовой загрузки, м³", self.v("batch_volume_m3"))
        self.support_count_hint = ttk.Label(main, text="", foreground="#465871", wraplength=700)
        self.support_count_hint.grid(row=4, column=0, columnspan=2, sticky="w", pady=(7, 0))
        length_var.trace_add("write", lambda *_: self._update_support_count())
        self._update_support_count()

        screw = ttk.LabelFrame(body, text="Шнек", padding=12)
        screw.grid(row=1, column=0, sticky="ew")
        screw.columnconfigure(1, weight=1)
        diameter_mode = self.v("diameter_mode", "auto")
        pitch_mode = self.v("pitch_mode", "gost")
        choices(screw, 0, "Наружный диаметр (50–600 мм)", diameter_mode,
                [("Подобрать", "auto"), ("Задать", "manual")])
        self.diameter_entry = field(screw, 1, "Диаметр, мм — если задан вручную", self.v("diameter_mm"))
        choices(screw, 2, "Шаг винта", pitch_mode,
                [("Пара по ГОСТ", "gost"), ("Задать, мм", "manual")])
        self.pitch_entry = field(screw, 3, "Шаг, мм — при ручном вводе или выборе пары", self.v("pitch_mm"))
        self.pitch_hint = ttk.Label(screw, text="", foreground="#465871", wraplength=650)
        self.pitch_hint.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))
        for var in (diameter_mode, pitch_mode, self.vars["diameter_mm"]):
            var.trace_add("write", lambda *_: self._update_screw())
        self._update_screw()

    def _update_screw(self):
        if not hasattr(self, "diameter_entry"):
            return
        manual_d = self.vars["diameter_mode"].get() == "manual"
        self.diameter_entry.configure(state="normal" if manual_d else "disabled")
        manual_p = self.vars["pitch_mode"].get() == "manual"
        self.pitch_entry.configure(state="normal" if manual_p or manual_d else "disabled")
        if not manual_d:
            hint = "Диаметр и нормативная пара D/S пока не определены: их выберет расчётный модуль."
        else:
            try:
                d = float(self.vars["diameter_mm"].get().replace(",", "."))
            except ValueError:
                d = None
            pair = GOST_PITCHES_MM.get(d)
            if pair:
                hint = f"Для D={d:g} мм пара ГОСТ: шаг {pair[0]} или {pair[1]} мм. "
                hint += "При выборе «Пара по ГОСТ» укажите один из них."
            else:
                hint = "Для диаметра вне стандартного ряда выберите «Задать, мм» и укажите шаг."
        self.pitch_hint.configure(text=hint)

    def _update_support_count(self):
        try:
            length = float(self.vars["working_length_mm"].get().strip().replace(",", "."))
            if not 500 <= length <= 25000:
                raise ValueError
            plan = body_support_layout(length)
        except ValueError:
            message = "Опоры корпуса: задайте рабочую длину для автоматического подсчёта."
        else:
            count = plan["station_count"]
            message = (f"Опоры корпуса: {count} шт. 01.01 и {count} шт. 08.00; "
                       f"расстояние между соседними опорами не более 3000 мм.")
        self.support_count_hint.configure(text=message)

    def _make_inlets_tab(self):
        body = self._tab("2. Загрузка")
        top = ttk.LabelFrame(body, text="Количество и режим подачи", padding=12)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text="Сначала задайте количество загрузочных горловин (1–7):").grid(
            row=0, column=0, sticky="w", padx=(0, 12))
        count = self.v("inlet_count", "1")
        ttk.Spinbox(top, from_=1, to=7, textvariable=count, width=6).grid(row=0, column=1, sticky="w")
        choices(top, 1, "Если горловин несколько, могут ли они работать одновременно?",
                self.v("inlets_simultaneous"), [("Да", "yes"), ("Нет", "no")])
        self.inlet_holder = ttk.Frame(body)
        self.inlet_holder.grid(row=1, column=0, sticky="ew", pady=10)
        count.trace_add("write", lambda *_: self._rebuild_rows("inlet"))
        self.vars["inlets_simultaneous"].trace_add("write", lambda *_: self._flow_states())
        self._rebuild_rows("inlet")

    def _make_outlets_tab(self):
        body = self._tab("3. Выгрузка")
        top = ttk.LabelFrame(body, text="Количество и режим выгрузки", padding=12)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text="Сначала задайте количество точек выгрузки (1–2):").grid(
            row=0, column=0, sticky="w", padx=(0, 12))
        count = self.v("outlet_count", "1")
        ttk.Spinbox(top, from_=1, to=2, textvariable=count, width=6).grid(row=0, column=1, sticky="w")
        choices(top, 1, "Если точек две, работают ли они одновременно?",
                self.v("outlets_simultaneous"), [("Да", "yes"), ("Нет", "no")])
        ttk.Label(top, text="Лево и право определяются при взгляде по движению материала.",
                  foreground="#465871").grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.outlet_holder = ttk.Frame(body)
        self.outlet_holder.grid(row=1, column=0, sticky="ew", pady=10)
        count.trace_add("write", lambda *_: self._rebuild_rows("outlet"))
        self.vars["outlets_simultaneous"].trace_add("write", lambda *_: self._flow_states())
        self._rebuild_rows("outlet")

    def _rebuild_rows(self, kind):
        if self._building:
            return
        key = "inlet_count" if kind == "inlet" else "outlet_count"
        limit = 7 if kind == "inlet" else 2
        try:
            count = int(self.vars[key].get())
        except ValueError:
            return
        if not 1 <= count <= limit:
            return
        rows = self.rows_inlet if kind == "inlet" else self.rows_outlet
        holder = self.inlet_holder if kind == "inlet" else self.outlet_holder
        old = [row.collect() for row in rows]
        cache = self._row_cache[kind]
        for i, saved in enumerate(old):
            if i < len(cache):
                cache[i] = saved
            else:
                cache.append(saved)
        for row in rows:
            row.destroy()
        new = []
        for i in range(count):
            row = OpeningRow(holder, i + 1, kind)
            row.pack(fill="x", pady=(0, 10))
            if i < len(cache):
                row.apply(cache[i])
            new.append(row)
        if kind == "inlet":
            self.rows_inlet = new
        else:
            self.rows_outlet = new
        self._flow_states()

    def _flow_states(self):
        if not hasattr(self, "rows_outlet"):
            return
        inlet_enabled = len(self.rows_inlet) > 1 and self.vars.get("inlets_simultaneous", tk.StringVar()).get() == "yes"
        outlet_enabled = len(self.rows_outlet) > 1 and self.vars.get("outlets_simultaneous", tk.StringVar()).get() == "yes"
        for row in self.rows_inlet:
            row.set_flow_enabled(inlet_enabled)
        for row in self.rows_outlet:
            row.set_flow_enabled(outlet_enabled)

    def _make_material_tab(self):
        body = self._tab("4. Материал")
        main = ttk.LabelFrame(body, text="Материал и его свойства", padding=12)
        main.grid(row=0, column=0, sticky="ew")
        main.columnconfigure(1, weight=1)
        field(main, 0, "Название материала", self.v("material_name"))
        source = self.v("material_source", "manual")
        choices(main, 1, "Источник проверенных свойств", source,
                [("Заполнить здесь", "manual"), ("Карточка справочника", "catalog")])
        ttk.Label(main, text="Код карточки в справочнике").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=5)
        self.card_entry = ttk.Combobox(main, textvariable=self.v("catalog_code"), values=list(cards()), width=34)
        self.card_entry.grid(row=2, column=1, sticky="w", pady=5)
        self.material_reference_entries = [
            field(main, 3, "Наибольшая насыпная плотность, кг/м³", self.v("bulk_density_kg_m3")),
            field(main, 4, "Наибольший размер куска, мм", self.v("max_lump_mm")),
        ]
        self.material_entries = [
            field(main, 5, "Наибольшая влажность, %", self.v("max_moisture_pct")),
            field(main, 8, "Рабочая температура материала, °C", self.v("temperature_c")),
            field(main, 10, "Если среда коррозионная — описание", self.v("corrosion_note")),
        ]
        self.material_buttons = []
        self.material_buttons += choices(main, 12, "База влажности",
                                         self.v("moisture_basis"),
                                         [("От массы влажной смеси", "wet"),
                                          ("От массы сухого вещества", "dry")])
        self.material_buttons += choices(main, 6, "Абразивность", self.v("abrasion"),
                                         [("Низкая", "low"), ("Средняя", "medium"), ("Высокая", "high")])
        self.material_buttons += choices(main, 7, "Сыпучесть", self.v("flowability"),
                                         [("Свободносыпучий", "free"), ("Налипает / слёживается", "sticky")])
        self.material_buttons += choices(main, 9, "Коррозионное воздействие", self.v("corrosion"),
                                         [("Нет", "no"), ("Есть", "yes")])
        source.trace_add("write", lambda *_: self._update_material())
        self.vars["catalog_code"].trace_add("write", lambda *_: self._update_material())
        self.vars["max_moisture_pct"].trace_add("write", lambda *_: self._update_material())
        self._update_material()
        ttk.Label(body, text="Справочная карточка подставляет верхнюю плотность и крупность. "
                  "Влажность, абразивность, сыпучесть и температуру задайте для расчёта привода. "
                  "Фактические свойства материала следует подтвердить пробой.",
                  wraplength=820, foreground="#465871").grid(row=1, column=0, sticky="w", pady=10)
        self.material_reference = ttk.Label(main, text="", foreground="#465871", wraplength=650)
        self.material_reference.grid(row=11, column=0, columnspan=2, sticky="w", pady=5)
        self._update_material()

    def _update_material(self):
        manual = self.vars["material_source"].get() == "manual"
        self.card_entry.configure(state="disabled" if manual else "readonly")
        for widget in self.material_reference_entries:
            widget.configure(state="normal" if manual else "disabled")
        if not manual:
            try:
                card = get_card(self.vars["catalog_code"].get())
            except ValueError:
                if hasattr(self, "material_reference"):
                    self.material_reference.configure(text="Выберите карточку материала")
            else:
                self.vars["material_name"].set(card["name"])
                self.vars["bulk_density_kg_m3"].set(str(card["bulk_density_max_kg_m3"]))
                self.vars["max_lump_mm"].set(str(card["max_lump_mm"]))
                if hasattr(self, "material_reference"):
                    self.material_reference.configure(
                        text=f"Справочник: {card['density_source_range_lb_ft3']} lb/ft³; "
                             f"верхнее значение {card['bulk_density_max_kg_m3']} кг/м³. {card['source_url']}"
                             + (" Плотность влажной смеси требует отдельного подтверждения."
                                if self.vars["max_moisture_pct"].get().strip() not in ("", "0", "0,0", "0.0")
                                else ""))
        elif hasattr(self, "material_reference"):
            self.material_reference.configure(text="")

    def _make_operation_tab(self):
        body = self._tab("5. Монтаж и режим")
        mounting = ttk.LabelFrame(body, text="Установка", padding=12)
        mounting.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        mounting.columnconfigure(1, weight=1)
        choices(mounting, 0, "Высота оси у начала желоба", self.v("height_source", "manual"),
                [("Задать", "manual"), ("По существующей установке", "existing")])
        self.height_entry = field(mounting, 1, "Высота оси, мм", self.v("axis_height_mm"))
        choices(mounting, 2, "Можно разместить опоры корпуса с шагом не более 3000 мм?",
                self.v("supports_free"), [("Да", "yes"), ("Нет", "no")])
        self.support_entry = field(mounting, 3, "Если нет — разрешённые места опор корпуса",
                                   self.v("support_positions"), width=44)
        choices(mounting, 4, "Размещение", self.v("environment"),
                [("В помещении", "inside"), ("Снаружи", "outside")])
        self.site_entry = field(mounting, 5, "Если снаружи — город / площадка",
                                self.v("site_location"), width=44)
        field(mounting, 6, "Особые требования и условия среды",
              self.v("special_requirements"), width=44)

        operation = ttk.LabelFrame(body, text="Расчётные режимы", padding=12)
        operation.grid(row=1, column=0, sticky="ew")
        operation.columnconfigure(1, weight=1)
        choices(operation, 0, "Режим работы", self.v("duty"),
                [("Непрерывный", "continuous"), ("Периодический", "intermittent")])
        field(operation, 1, "Часов работы в сутки", self.v("hours_per_day"))
        field(operation, 2, "Пусков в час", self.v("starts_per_hour"))
        choices(operation, 3, "Возможен пуск с заполненным желобом?",
                self.v("loaded_start"), [("Да", "yes"), ("Нет", "no")])
        choices(operation, 4, "Нужен реверс?", self.v("reverse"),
                [("Да", "yes"), ("Нет", "no")])
        choices(operation, 5, "Возможна закупорка выгрузки?", self.v("blockage"),
                [("Да", "yes"), ("Нет", "no")])
        self.protection_buttons = choices(operation, 6, "Если да — предусмотрена защита от перегрузки?",
                                          self.v("overload_protection"), [("Да", "yes"), ("Нет", "no")])
        choices(operation, 7, "Подача непосредственно из бункера?", self.v("hopper"),
                [("Да", "yes"), ("Нет", "no")])
        self.head_entry = field(operation, 8, "Если да — высота столба материала, мм",
                                self.v("hopper_head_mm"))
        field(operation, 9, "Требуемый ресурс, ч", self.v("design_life_h"))
        for key in ("height_source", "supports_free", "environment", "blockage", "hopper"):
            self.vars[key].trace_add("write", lambda *_: self._update_operation())
        self._update_operation()

    def _update_operation(self):
        self.height_entry.configure(state="normal" if self.vars["height_source"].get() == "manual" else "disabled")
        self.support_entry.configure(state="normal" if self.vars["supports_free"].get() == "no" else "disabled")
        self.site_entry.configure(state="normal" if self.vars["environment"].get() == "outside" else "disabled")
        self.head_entry.configure(state="normal" if self.vars["hopper"].get() == "yes" else "disabled")
        for button in self.protection_buttons:
            button.configure(state="normal" if self.vars["blockage"].get() == "yes" else "disabled")

    def _make_strength_tab(self):
        body = self._tab("6. Прочность")
        note = ttk.Label(
            body,
            text="Предварительная статическая проверка вала с пазом 25.SHT.G.02.00.00.03 "
                 "в SolidWorks Simulation. Задайте расчётные нагрузки для худшего режима, "
                 "включая пуск и возможную закупорку. Эти нагрузки не выводятся автоматически из расхода.",
            wraplength=820, foreground="#465871")
        note.grid(row=0, column=0, sticky="w", pady=(0, 12))
        main = ttk.LabelFrame(body, text="Нагрузки и материал вала", padding=12)
        main.grid(row=1, column=0, sticky="ew")
        main.columnconfigure(1, weight=1)
        field(main, 0, "Расчётный крутящий момент, Н·м", self.v("torque_nm"))
        field(main, 1, "Расчётная осевая сила, Н (0 допустимо)", self.v("axial_force_n"))
        field(main, 2, "Материал из библиотеки SolidWorks — точное имя",
              self.v("simulation_material", "Plain Carbon Steel"), width=35)
        field(main, 3, "Расчётный предел текучести, МПа (не выше значения библиотеки)", self.v("yield_strength_mpa"))
        field(main, 4, "Требуемый коэффициент запаса ≥ 1", self.v("required_safety_factor"))
        field(main, 5, "Размер элемента сетки, мм (пусто — стандартный)", self.v("mesh_size_mm"))
        ttk.Button(body, text="Рассчитать в SolidWorks Simulation", command=self.run_strength).grid(
            row=2, column=0, sticky="w", pady=12)
        ttk.Label(body,
                  text="Условная схема: один торец вала жёстко закреплён, на другой приложены сила и момент. "
                       "В отчёте будут напряжение Мизеса, перемещение и коэффициент по текучести. "
                       "Вся сборка транспортёра этим расчётом не проверяется.",
                  wraplength=820, foreground="#465871").grid(row=3, column=0, sticky="w")

    def _make_purchased_tab(self):
        body = self._tab("7. Покупные изделия")
        self.purchased_items = baseline_items()
        ttk.Label(body, text="Исходный перечень взят из позиций 41–44 и 63–85 переданной спецификации сборки. "
                  "Выберите применяемые изделия, скорректируйте количество или добавьте новый вариант. "
                  "Выгрузка является проектом раздела спецификации до проверки компоновки и поставщика.",
                  wraplength=850, foreground="#465871").grid(row=0, column=0, sticky="w", pady=(0, 10))
        columns = ("chosen", "category", "designation", "quantity", "source_position")
        table = ttk.Treeview(body, columns=columns, show="headings", height=16, selectmode="browse")
        labels = {"chosen": "Выбор", "category": "Группа", "designation": "Обозначение",
                  "quantity": "Кол.", "source_position": "Поз. исходная"}
        widths = {"chosen": 65, "category": 165, "designation": 455,
                  "quantity": 55, "source_position": 90}
        for key in columns:
            table.heading(key, text=labels[key])
            table.column(key, width=widths[key], stretch=key == "designation")
        table.grid(row=1, column=0, sticky="nsew")
        body.rowconfigure(1, weight=1)
        self.purchased_table = table
        table.bind("<<TreeviewSelect>>", lambda _: self._purchased_load_editor())
        form = ttk.LabelFrame(body, text="Выбранная строка", padding=10)
        form.grid(row=2, column=0, sticky="ew", pady=10)
        self.purchase_vars = {key: tk.StringVar() for key in ("category", "designation", "quantity", "note")}
        self.purchase_selected = tk.BooleanVar(value=True)
        ttk.Checkbutton(form, text="Включить в спецификацию", variable=self.purchase_selected).grid(
            row=0, column=0, columnspan=2, sticky="w")
        field(form, 1, "Группа", self.purchase_vars["category"], width=46)
        field(form, 2, "Обозначение / типоразмер", self.purchase_vars["designation"], width=65)
        field(form, 3, "Количество, шт.", self.purchase_vars["quantity"], width=12)
        field(form, 4, "Примечание (производитель, исполнение)", self.purchase_vars["note"], width=65)
        actions = ttk.Frame(body)
        actions.grid(row=3, column=0, sticky="w")
        ttk.Button(actions, text="Применить к строке", command=self._purchased_apply_editor).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Добавить изделие", command=self._purchased_add).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Удалить свою строку", command=self._purchased_delete).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="Выгрузить раздел спецификации CSV", command=self.export_purchased).pack(side="left")
        self._purchased_refresh()

    def _purchased_refresh(self, selected_id=None):
        table = self.purchased_table
        table.delete(*table.get_children())
        for item in self.purchased_items:
            table.insert("", "end", iid=item["id"], values=(
                "Да" if item["selected"] else "Нет", item["category"], item["designation"],
                item["quantity"], item.get("source_position") or ""))
        if selected_id and table.exists(selected_id):
            table.selection_set(selected_id)
            table.see(selected_id)

    def _purchased_load_editor(self):
        selection = self.purchased_table.selection()
        if not selection:
            return
        item = next(row for row in self.purchased_items if row["id"] == selection[0])
        for key, var in self.purchase_vars.items():
            var.set(str(item.get(key, "")))
        self.purchase_selected.set(item["selected"])

    def _purchased_apply_editor(self):
        selection = self.purchased_table.selection()
        if not selection:
            messagebox.showinfo("Покупные изделия", "Выберите строку перечня", parent=self)
            return
        index = next(i for i, row in enumerate(self.purchased_items) if row["id"] == selection[0])
        candidate = dict(self.purchased_items[index])
        candidate.update({key: var.get().strip() for key, var in self.purchase_vars.items()})
        candidate["selected"] = self.purchase_selected.get()
        try:
            clean = validate_items([candidate])[0]
        except ValueError as exc:
            messagebox.showerror("Покупные изделия", str(exc), parent=self)
            return
        self.purchased_items[index] = clean
        self._purchased_refresh(clean["id"])

    def _purchased_add(self):
        import uuid
        item = {"id": "USER-" + uuid.uuid4().hex[:12], "category": "Прочие изделия",
                "designation": "Новое изделие", "quantity": 1, "selected": True,
                "note": "", "source": "Добавлено пользователем", "source_position": None}
        self.purchased_items.append(item)
        self._purchased_refresh(item["id"])

    def _purchased_delete(self):
        selection = self.purchased_table.selection()
        if selection and selection[0].startswith("USER-"):
            self.purchased_items = [row for row in self.purchased_items if row["id"] != selection[0]]
            self._purchased_refresh()

    def export_purchased(self):
        path = filedialog.asksaveasfilename(parent=self, title="Раздел покупных изделий",
                                            initialfile="спецификация_покупные_изделия.csv",
                                            defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            write_specification(self.purchased_items, path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Покупные изделия", str(exc), parent=self)
            return
        self.status.set(f"Выгружен раздел: {Path(path).name}")
        messagebox.showinfo("Покупные изделия", f"Выгружено: {path}", parent=self)

    def _make_footer(self):
        footer = ttk.Frame(self, padding=(14, 8, 14, 12))
        footer.pack(fill="x")
        ttk.Button(footer, text="Открыть JSON", command=self.load_json).pack(side="left", padx=(0, 8))
        ttk.Button(footer, text="Сохранить черновик", command=self.save_draft).pack(side="left", padx=(0, 8))
        ttk.Button(footer, text="Проверить и сохранить", command=self.save_validated).pack(side="left")
        ttk.Button(footer, text="Связать с моделью", command=self.link_model).pack(side="left", padx=(8, 0))
        ttk.Button(footer, text="Закрыть", command=self.destroy).pack(side="right")
        self.status = tk.StringVar(value="Данные ещё не сохранены")
        ttk.Label(footer, textvariable=self.status, foreground="#465871").pack(side="right", padx=18)

    def collect(self):
        v = lambda key: self.vars[key].get().strip()
        return {
            "general": {key: v(key) for key in
                        ("working_length_mm", "inclination_deg", "throughput_m3_h", "batch_volume_m3")},
            "screw": {key: v(key) for key in
                      ("diameter_mode", "diameter_mm", "pitch_mode", "pitch_mm")},
            "inlet_count": v("inlet_count"),
            "inlets_simultaneous": v("inlets_simultaneous"),
            "inlets": [row.collect() for row in self.rows_inlet],
            "outlet_count": v("outlet_count"),
            "outlets_simultaneous": v("outlets_simultaneous"),
            "outlets": [row.collect() for row in self.rows_outlet],
            "material": {
                "name": v("material_name"), "source": v("material_source"),
                **{key: v(key) for key in
                   ("catalog_code", "bulk_density_kg_m3", "max_lump_mm", "max_moisture_pct",
                    "moisture_basis", "abrasion", "flowability", "temperature_c", "corrosion", "corrosion_note")},
            },
            "installation": {key: v(key) for key in
                             ("height_source", "axis_height_mm", "supports_free", "support_positions",
                              "environment", "site_location", "special_requirements")},
            "operation": {key: v(key) for key in
                          ("duty", "hours_per_day", "starts_per_hour", "loaded_start", "reverse",
                           "blockage", "overload_protection", "hopper", "hopper_head_mm", "design_life_h")},
            "strength": {key: v(key) for key in
                         ("torque_nm", "axial_force_n", "simulation_material", "yield_strength_mpa",
                          "required_safety_factor", "mesh_size_mm")},
            "purchased_items": validate_items(self.purchased_items),
        }

    def apply(self, data):
        self._building = True
        for row in self.rows_inlet + self.rows_outlet:
            row.destroy()
        self.rows_inlet = []
        self.rows_outlet = []
        self._row_cache = {"inlet": [], "outlet": []}
        mapping = {
            **(data.get("general") or {}), **(data.get("screw") or {}),
            **(data.get("material") or {}), **(data.get("installation") or {}),
            **(data.get("operation") or {}), **(data.get("strength") or {}),
        }
        mapping["material_name"] = (data.get("material") or {}).get("name")
        mapping["material_source"] = (data.get("material") or {}).get("source")
        for key, value in mapping.items():
            if key in self.vars:
                self.vars[key].set("" if value is None else str(value))
        inlets = data.get("inlets") or []
        outlets = data.get("outlets") or []
        self.vars["inlet_count"].set(str(data.get("inlet_count") or len(inlets) or 1))
        self.vars["outlet_count"].set(str(data.get("outlet_count") or len(outlets) or 1))
        self.vars["inlets_simultaneous"].set(data.get("inlets_simultaneous") or "")
        self.vars["outlets_simultaneous"].set(data.get("outlets_simultaneous") or "")
        self._building = False
        self._rebuild_rows("inlet")
        self._rebuild_rows("outlet")
        for row, saved in zip(self.rows_inlet, inlets):
            row.apply(saved)
        for row, saved in zip(self.rows_outlet, outlets):
            row.apply(saved)
        self._update_screw()
        self._update_material()
        self._update_operation()
        self._flow_states()
        if "purchased_items" in data:
            self.purchased_items = validate_items(data["purchased_items"])
            self._purchased_refresh()

    def _write(self, payload, initial_name):
        path = filedialog.asksaveasfilename(
            parent=self, title="Сохранить опросный лист", initialfile=initial_name,
            defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Ошибка сохранения", str(exc), parent=self)
            return
        self.status.set(f"Сохранено: {Path(path).name}")
        messagebox.showinfo("Сохранено", path, parent=self)

    def save_draft(self):
        self._write({
            "schema_version": 1,
            "status": "draft",
            "saved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "inputs": self.collect(),
        }, "опросный_лист_черновик.json")

    def save_validated(self):
        normalized, errors, warnings = validate(self.collect())
        if errors:
            messagebox.showerror("Проверьте данные",
                                 "\n".join(errors[:18]) + (f"\n…и ещё {len(errors)-18}" if len(errors) > 18 else ""),
                                 parent=self)
            self.status.set(f"Ошибок: {len(errors)}")
            return
        if warnings:
            messagebox.showwarning("Требует инженерной проверки", "\n".join(warnings), parent=self)
        self._write({
            "schema_version": 1,
            "status": "validated_questionnaire",
            "saved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "inputs": normalized,
            "engineering_warnings": warnings,
            "note": "Опросный лист не является результатом расчёта прочности.",
        }, "данные_транспортера.json")

    def link_model(self):
        root = filedialog.askdirectory(parent=self, title="Выберите папку копии модели SolidWorks",
                                      initialdir=str(default_model_dir()))
        if not root:
            return
        try:
            plan = prepare(self.collect(), root)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Связь с моделью", str(exc), parent=self)
            return
        if plan["blocked"]:
            messagebox.showerror("Параметры пока не поддерживаются",
                                 "\n".join(plan["blocked"]), parent=self)
            return
        info = (f"В деталь шнека D=200 мм будет передан шаг {plan['pitch_mm']:g} мм.\n\n"
                "Длина, наклон, диаметр, загрузки, выгрузки, опоры и привод "
                "не изменятся в геометрии. Все введённые данные будут записаны в отчёт связи.\n\n"
                "Продолжить?")
        if not messagebox.askyesno("Частичная связь с моделью", info, parent=self):
            return
        try:
            result = apply_to_model(plan)
        except (OSError, ValueError, RuntimeError, ImportError) as exc:
            messagebox.showerror("Ошибка SolidWorks", str(exc), parent=self)
            return
        self.status.set(f"Шаг шнека: {result['applied_geometry']['screw_pitch_mm']:g} мм")
        messagebox.showinfo("Связь выполнена",
                            "Шаг шнека проверен и сохранён в SolidWorks.\n"
                            f"Отчёт: {result['report_path']}", parent=self)

    def run_strength(self):
        root = filedialog.askdirectory(parent=self, title="Выберите папку копии модели SolidWorks",
                                      initialdir=str(default_model_dir()))
        if not root:
            return
        try:
            plan = prepare_strength(self.collect(), root)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Проверьте расчётные данные", str(exc), parent=self)
            return
        controls = plan["controls"]
        preview = (f"Вал: {Path(plan['shaft_part']).name}\n"
                   f"Момент: {controls['torque_nm']:g} Н·м; осевая сила: {controls['axial_force_n']:g} Н.\n"
                   f"Материал: {controls['simulation_material']}; предел текучести: "
                   f"{controls['yield_strength_mpa']:g} МПа.\n\n"
                   "Будет выполнен предварительный статический расчёт и передан шаг шнека в копию CAD. Продолжить?")
        if not messagebox.askyesno("Расчёт Simulation", preview, parent=self):
            return
        self.status.set("Выполняется расчёт Simulation…")
        self.update_idletasks()
        try:
            result = run_strength_study(plan)
        except Exception as exc:
            self.status.set("Расчёт не завершён")
            messagebox.showerror("Ошибка расчёта Simulation", str(exc), parent=self)
            return
        sim = result["simulation"]
        self.status.set(f"Вал: σ={sim['max_von_mises_mpa']:.2f} МПа, запас={sim['yield_safety_factor']:.2f}")
        messagebox.showinfo("Предварительный расчёт завершён",
                            f"Макс. напряжение Мизеса: {sim['max_von_mises_mpa']:.3f} МПа\n"
                            f"Макс. перемещение: {sim['max_displacement_mm']:.4f} мм\n"
                            f"Коэффициент по текучести: {sim['yield_safety_factor']:.2f}\n"
                            f"Отчёт: {result['report_path']}", parent=self)

    def load_json(self):
        path = filedialog.askopenfilename(parent=self, title="Открыть опросный лист",
                                          filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            if payload.get("schema_version") != 1 or not isinstance(payload.get("inputs"), dict):
                raise ValueError("Формат файла не поддерживается")
            self.apply(payload["inputs"])
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("Ошибка открытия", str(exc), parent=self)
            return
        self.status.set(f"Открыто: {Path(path).name}")


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        payload = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        raw = payload.get("inputs", payload)
        if "inlet_count" not in raw:
            raw = {**raw, "inlet_count": len(raw.get("inlets", [])),
                   "outlet_count": len(raw.get("outlets", []))}
        _, errors, warnings = validate(raw)
        for error in errors:
            print("ERROR:", error)
        for warning in warnings:
            print("WARNING:", warning)
        print("Проверка пройдена" if not errors else f"Ошибок: {len(errors)}")
        return 0 if not errors else 1
    if len(sys.argv) == 3 and sys.argv[1] == "--open":
        payload = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1 or not isinstance(payload.get("inputs"), dict):
            raise ValueError("Формат файла не поддерживается")
        app = Questionnaire()
        app.apply(payload["inputs"])
        app.status.set(f"Открыто: {Path(sys.argv[2]).name}")
        app.mainloop()
        return 0
    if len(sys.argv) != 1:
        print("Использование: python app.py [--check файл.json | --open файл.json]")
        return 2
    Questionnaire().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
