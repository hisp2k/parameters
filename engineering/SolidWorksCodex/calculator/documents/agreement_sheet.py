# -*- coding: utf-8 -*-
"""
Лист согласования (раздел 13 задания).

Экранный просмотр (HTML) и PDF формируются из ОДНОГО набора данных —
AgreementSheetData, собираемого из Project. Ни HTML-, ни PDF-рендерер не
хранят собственной копии данных и не могут разойтись между собой по цифрам,
потому что оба читают одни и те же поля одного объекта.

ИСПРАВЛЕНИЯ (раздел 1 задания):

- "Не снимай отметку «Предварительный» только из-за статуса «Передан на
  проверку» и cad_sync.done=True." Раньше `is_preliminary` становился False,
  как только `project.status != PROJECT_STATUS_DRAFT` И `cad_sync.done` —
  то есть простой переход в статус "передан_на_проверку" при включённом (но
  не обязательно актуальном) `cad_sync.done` уже снимал отметку. Теперь
  документ остаётся предварительным, пока проект не достиг
  `PROJECT_STATUS_RELEASED` — то есть пока не пройден весь release_gate.
- "Экранируй пользовательский текст при формировании HTML и PDF." Раньше
  текстовые поля (наименование материала, заказчик, обозначение и т.п.)
  подставлялись в HTML/PDF без экранирования — значение материала вида
  `<script>...</script>` или `<b>` сломало бы разметку и в HTML, и в PDF
  (Paragraph reportlab тоже воспринимает `<`/`>` как разметку). Теперь весь
  пользовательский текст проходит через `html.escape()` (HTML) или
  `xml.sax.saxutils.escape()` (PDF, с сохранением только тех тегов, которые
  добавляет сам код, а не значение).
- "Обеспечь генерацию PDF на Windows и Linux: убери жёсткую зависимость от
  Linux-пути к шрифтам." Шрифт больше не берётся из
  `/usr/share/fonts/truetype/dejavu/` — используется файл, вложенный прямо в
  репозиторий (`calculator/assets/fonts/`), одинаковый путь на любой ОС.
"""

from __future__ import annotations

import html as html_escape_module
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

from calculator.core.project import Project, PROJECT_STATUS_RELEASED
from calculator.documents.schematic import SchematicData, render_html_svg, render_pdf_drawing

ASSETS_FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def _e(text) -> str:
    """Экранирование для HTML — раздел 1.Д."""
    return html_escape_module.escape(str(text), quote=True)


def _ep(text) -> str:
    """Экранирование для PDF (reportlab Paragraph понимает мини-XML-разметку)."""
    return _xml_escape(str(text))


@dataclass
class AgreementSheetData:
    project_name: str
    customer: str
    manufacturer: str
    designation: str
    date: str
    revision: str
    status_label: str
    is_preliminary: bool

    product_material: str
    productivity_required_text: str
    productivity_achievable_text: str
    requirement_met: bool

    overall_dimensions_text: str
    connection_dimensions_text: str
    incline_deg_text: str
    load_point_text: str
    unload_point_text: str
    flow_direction_text: str

    screw_params_text: str
    drive_params_text: str

    construction_material: str
    mass_text: str
    mass_source: str

    view_note: str
    schematic_svg: str | None       # None только если геометрию вообще нельзя посчитать
    schematic_data: SchematicData | None

    options_text: str
    scope_of_supply_text: str
    limitations: list[str] = field(default_factory=list)
    stale_documents_note: str | None = None

    review_fields: list[str] = field(
        default_factory=lambda: [
            "Разработал", "Проверил", "Согласовано с заказчиком", "Утвердил",
        ]
    )


def build_agreement_sheet_data(project: Project, manufacturer: str = "Тех-Аэро") -> AgreementSheetData:
    # Раздел 1.Д: остаётся предварительным до фактического выпуска, а не до
    # промежуточного статуса "передан_на_проверку" + один булев флаг CAD.
    is_preliminary = project.status != PROJECT_STATUS_RELEASED
    status_label = "ПРЕДВАРИТЕЛЬНЫЙ — не для производства" if is_preliminary else project.status

    q = project.questionnaire
    er = project.engineering_result
    tr = project.tube_engineering_result
    schematic_svg = None
    schematic_data = None

    if q is not None:
        length, angle = q.geometry.resolved_length_angle()
        productivity_required_text = (
            f"{q.productivity.value} {q.productivity.unit.value}"
            if q.productivity.value is not None and q.productivity.unit is not None
            else "не задана заказчиком"
        )
        product_material = q.material.material_name
        overall_text = (
            f"{q.geometry.overall_length_mm:.0f} мм (габарит)"
            if q.geometry.overall_length_mm is not None
            else f"{length:.0f} мм (рабочая длина; общий габарит ещё не определён)" if length else "не определены"
        )
        incline_text = f"{angle:.1f}°" if angle is not None else "не определён"
        load_text = str(q.geometry.load_point_xyz_mm) if q.geometry.load_point_xyz_mm else "см. схему компоновки ниже"
        unload_text = str(q.geometry.unload_point_xyz_mm) if q.geometry.unload_point_xyz_mm else "см. схему компоновки ниже"
        construction_material = q.profile.construction_material

        # Схема строится только когда есть подтверждённый числовой диаметр
        # корпуса (желобчатый расчёт). Для SHAFTED_TUBE диаметр корпуса
        # заблокирован (см. core/tube_engineering.py) — схему не строим,
        # а не подставляем DN присоединительного патрубка как диаметр корпуса.
        if length and er is not None:
            sd = SchematicData(
                working_length_mm=length, incline_deg=angle or 0.0,
                diameter_mm=er.diameter_mm, designation=project.designation,
                is_preliminary=not project.cad_sync.done,
            )
            schematic_data = sd
            schematic_svg = render_html_svg(sd)
    else:
        productivity_required_text = product_material = overall_text = incline_text = "не заданы"
        load_text = unload_text = construction_material = "не заданы"

    if er is not None:
        productivity_achievable_text = f"{er.productivity_achievable_t_per_h:.2f} т/ч"
        requirement_met = er.requirement_met
        screw_params_text = (
            f"диаметр {er.diameter_mm:.0f} мм, шаг {er.step_mm:.0f} мм, "
            f"частота вращения {er.rotation_speed_rpm:.1f} об/мин из допустимых до "
            f"{er.max_allowed_rotation_speed_rpm:.1f} об/мин "
            f"(ψ={er.fill_factor_psi}, C={er.incline_factor_c}) — предварительный расчёт, не проверено"
        )
        if er.motor_selection_ok:
            drive_params_text = (
                f"мощность на валу {er.shaft_power_kw:.2f} кВт, "
                f"предварительно подобранный мотор {er.motor_power_kw} кВт — привод не согласован (раздел 11)"
            )
        else:
            drive_params_text = (
                f"мощность на валу {er.shaft_power_kw:.2f} кВт — подходящий мотор из стандартного "
                "ряда черновика НЕ подобран, требуется каталог поставщика"
            )
        limitations = list(er.warnings)
    elif tr is not None:
        # SHAFTED_TUBE (Issue #3) — инженерное ядро честно заблокировано:
        # показываем геометрию/конфликт и полный список блокеров вместо
        # форматирования несуществующих числовых значений.
        productivity_achievable_text = (
            f"не вычислено (требуется {tr.productivity_required_t_per_h} т/ч)"
            if tr.productivity_required_t_per_h is not None
            else "не вычислено — производительность не переведена в т/ч"
        )
        requirement_met = False
        dn_text = (
            f"DN{tr.connection_diameter_mm:.0f} (только патрубок)"
            if tr.connection_diameter_mm is not None else "не задан"
        )
        screw_params_text = (
            f"ЗАБЛОКИРОВАНО (валовый трубчатый шнек): диаметр корпуса не определён, "
            f"присоединительный диаметр {dn_text} — см. ограничения ниже"
        )
        drive_params_text = "не вычислено — нет мощности/оборотов (инженерное ядро заблокировано)"
        limitations = list(tr.warnings) + list(tr.blockers)
        if tr.geometry_conflict is not None and tr.geometry_conflict.conflict:
            gc = tr.geometry_conflict
            incline_text = (
                f"{incline_text} — ПРОТИВОРЕЧИЕ: по высотам пола набор {gc.height_gain_from_floor_heights_mm} мм, "
                f"по углу/длине набор {gc.height_gain_from_angle_mm} мм (допуск {gc.tolerance_mm:.0f} мм)"
            )
    else:
        productivity_achievable_text = "расчёт не выполнен"
        requirement_met = False
        screw_params_text = drive_params_text = "расчёт не выполнен"
        limitations = []

    if project.is_calc_stale():
        limitations.append(
            "Расчёт УСТАРЕЛ: входные данные изменились после последнего расчёта (раздел 1.Б) — требуется пересчёт."
        )
    if not project.drive_selection.done:
        limitations.append(project.drive_selection.note)
    if not project.kd_bom.done:
        limitations.append(project.kd_bom.note)
    if not project.technology.done:
        limitations.append(project.technology.note)

    stale_docs = project.stale_issued_documents()
    stale_note = (
        f"{len(stale_docs)} ранее выгруженных документ(ов) относятся к устаревшей ревизии и "
        "не отражают текущее состояние проекта (раздел 1.Б)."
        if stale_docs else None
    )

    if q is not None and er is not None:
        view_note = (
            "ПРЕДВАРИТЕЛЬНО: схема ниже построена по расчёту, БЕЗ подтверждения CAD-моделью "
            "(нет синхронизации с SolidWorks, раздел 12)."
            if not project.cad_sync.done else
            "Виды по актуальной CAD-ревизии (см. параметр cad_sync)."
        )
    else:
        view_note = "Схема недоступна: не выполнен расчёт геометрии/компоновки."

    return AgreementSheetData(
        project_name=project.project_name,
        customer=project.customer,
        manufacturer=manufacturer,
        designation=project.designation,
        date=project.updated_at[:10],
        revision=project.revision,
        status_label=status_label,
        is_preliminary=is_preliminary,
        product_material=product_material,
        productivity_required_text=productivity_required_text,
        productivity_achievable_text=productivity_achievable_text,
        requirement_met=requirement_met,
        overall_dimensions_text=overall_text,
        connection_dimensions_text="не определены — нет утверждённой BOM-версии сборки",
        incline_deg_text=incline_text,
        load_point_text=load_text,
        unload_point_text=unload_text,
        flow_direction_text="от точки загрузки к точке выгрузки (см. геометрию)",
        screw_params_text=screw_params_text,
        drive_params_text=drive_params_text,
        construction_material=construction_material,
        mass_text="не рассчитана — нет данных из CAD",
        mass_source="CAD не синхронизирован" if not project.cad_sync.done else "из CAD",
        view_note=view_note,
        schematic_svg=schematic_svg,
        schematic_data=schematic_data,
        options_text="типовые опции по профилю эксплуатации (см. опросный лист проекта)",
        scope_of_supply_text="не определена окончательно — требует подтверждения инженером",
        limitations=limitations,
        stale_documents_note=stale_note,
    )


def render_html(data: AgreementSheetData) -> str:
    limitations_html = "".join(f"<li>{_e(l)}</li>" for l in data.limitations) or "<li>нет</li>"
    banner = (
        '<div style="background:#fff3cd;border:1px solid #e0a800;padding:8px 12px;'
        'font-weight:bold;margin-bottom:12px;">ПРЕДВАРИТЕЛЬНЫЙ ЛИСТ — НЕ ДЛЯ ПРОИЗВОДСТВА</div>'
        if data.is_preliminary else ""
    )
    stale_banner = (
        f'<div style="background:#f8d7da;border:1px solid #c00;padding:8px 12px;'
        f'font-weight:bold;margin-bottom:12px;">{_e(data.stale_documents_note)}</div>'
        if data.stale_documents_note else ""
    )
    review_html = "".join(
        f'<tr><td style="border:1px solid #999;padding:4px 8px;">{_e(f)}</td>'
        f'<td style="border:1px solid #999;padding:4px 8px;width:160px;"></td></tr>'
        for f in data.review_fields
    )
    requirement_badge = (
        '<span style="color:#0a7a0a;font-weight:bold;">ВЫПОЛНЕНО</span>' if data.requirement_met
        else '<span style="color:#a00;font-weight:bold;">НЕ ВЫПОЛНЕНО</span>'
    )
    schematic_html = (
        f'<h3>Предварительная схема</h3>{data.schematic_svg}'
        if data.schematic_svg else ""
    )
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>Лист согласования — {_e(data.designation)}</title></head>
<body style="font-family:Arial,sans-serif;font-size:13px;max-width:900px;margin:20px auto;">
{banner}{stale_banner}
<h2>Лист согласования</h2>
<table style="border-collapse:collapse;width:100%;">
<tr><td style="padding:2px 8px;"><b>Проект</b></td><td>{_e(data.project_name)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Заказчик</b></td><td>{_e(data.customer)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Изготовитель</b></td><td>{_e(data.manufacturer)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Обозначение</b></td><td>{_e(data.designation)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Дата</b></td><td>{_e(data.date)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Ревизия</b></td><td>{_e(data.revision)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Статус</b></td><td><b>{_e(data.status_label)}</b></td></tr>
</table>
<hr>
<table style="border-collapse:collapse;width:100%;">
<tr><td style="padding:2px 8px;width:260px;"><b>Материал продукта</b></td><td>{_e(data.product_material)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Производительность требуемая</b></td><td>{_e(data.productivity_required_text)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Производительность достижимая</b></td><td>{_e(data.productivity_achievable_text)} — {requirement_badge}</td></tr>
<tr><td style="padding:2px 8px;"><b>Габариты</b></td><td>{_e(data.overall_dimensions_text)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Присоединительные размеры</b></td><td>{_e(data.connection_dimensions_text)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Угол наклона</b></td><td>{_e(data.incline_deg_text)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Точка загрузки</b></td><td>{_e(data.load_point_text)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Точка выгрузки</b></td><td>{_e(data.unload_point_text)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Направление движения</b></td><td>{_e(data.flow_direction_text)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Параметры шнека</b></td><td>{_e(data.screw_params_text)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Параметры привода</b></td><td>{_e(data.drive_params_text)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Материал конструкции</b></td><td>{_e(data.construction_material)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Масса</b></td><td>{_e(data.mass_text)} ({_e(data.mass_source)})</td></tr>
<tr><td style="padding:2px 8px;"><b>Изометрия / вид сбоку</b></td><td>{_e(data.view_note)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Опции</b></td><td>{_e(data.options_text)}</td></tr>
<tr><td style="padding:2px 8px;"><b>Граница поставки</b></td><td>{_e(data.scope_of_supply_text)}</td></tr>
</table>
{schematic_html}
<h3>Ограничения</h3>
<ul>{limitations_html}</ul>
<h3>Согласование</h3>
<table style="border-collapse:collapse;">{review_html}</table>
</body></html>"""


def _register_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    if "DejaVu" in pdfmetrics.getRegisteredFontNames():
        return
    regular = ASSETS_FONT_DIR / "DejaVuSans.ttf"
    bold = ASSETS_FONT_DIR / "DejaVuSans-Bold.ttf"
    if not regular.exists() or not bold.exists():
        raise FileNotFoundError(
            f"Не найден шрифт для PDF по пути {ASSETS_FONT_DIR} — ожидались файлы "
            "DejaVuSans.ttf и DejaVuSans-Bold.ttf, вложенные в репозиторий "
            "(calculator/assets/fonts/), не системный путь ОС."
        )
    pdfmetrics.registerFont(TTFont("DejaVu", str(regular)))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(bold)))
    pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold",
                                   italic="DejaVu", boldItalic="DejaVu-Bold")


def build_pdf(data: AgreementSheetData, out_path) -> Path:
    """PDF — фиксированный документ, из того же набора данных, что и render_html()."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    # Кириллица + кроссплатформенность (раздел 1.Д): шрифт берётся из
    # calculator/assets/fonts/, а не из системного пути ОС — раньше жёсткая
    # ссылка на /usr/share/fonts/truetype/dejavu/ работала только в Linux.
    _register_fonts()

    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["Normal"], fontName="DejaVu", fontSize=9, leading=12)
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="DejaVu-Bold", fontSize=14)
    h3 = ParagraphStyle("h3", parent=styles["Heading3"], fontName="DejaVu-Bold", fontSize=11)

    story = []
    if data.stale_documents_note:
        story.append(Paragraph(f"<font color='#a00'><b>{_ep(data.stale_documents_note)}</b></font>", body))
        story.append(Spacer(1, 6))
    if data.is_preliminary:
        story.append(Paragraph(
            "<font color='red'><b>ПРЕДВАРИТЕЛЬНЫЙ ЛИСТ — НЕ ДЛЯ ПРОИЗВОДСТВА</b></font>", body
        ))
        story.append(Spacer(1, 6))
    story.append(Paragraph("Лист согласования", h1))

    requirement_text = "ВЫПОЛНЕНО" if data.requirement_met else "НЕ ВЫПОЛНЕНО"
    rows = [
        ("Проект", data.project_name), ("Заказчик", data.customer),
        ("Изготовитель", data.manufacturer), ("Обозначение", data.designation),
        ("Дата", data.date), ("Ревизия", data.revision), ("Статус", data.status_label),
        ("Материал продукта", data.product_material),
        ("Производительность требуемая", data.productivity_required_text),
        ("Производительность достижимая", f"{data.productivity_achievable_text} — {requirement_text}"),
        ("Габариты", data.overall_dimensions_text),
        ("Присоединительные размеры", data.connection_dimensions_text),
        ("Угол наклона", data.incline_deg_text), ("Точка загрузки", data.load_point_text),
        ("Точка выгрузки", data.unload_point_text), ("Направление движения", data.flow_direction_text),
        ("Параметры шнека", data.screw_params_text), ("Параметры привода", data.drive_params_text),
        ("Материал конструкции", data.construction_material),
        ("Масса", f"{data.mass_text} ({data.mass_source})"),
        ("Изометрия / вид сбоку", data.view_note), ("Опции", data.options_text),
        ("Граница поставки", data.scope_of_supply_text),
    ]
    table_data = [[Paragraph(f"<b>{_ep(k)}</b>", body), Paragraph(_ep(v), body)] for k, v in rows]
    t = Table(table_data, colWidths=[55 * mm, 110 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t)
    story.append(Spacer(1, 10))

    if data.schematic_data is not None:
        story.append(Paragraph("Предварительная схема", h3))
        story.append(render_pdf_drawing(data.schematic_data))
        story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Ограничения</b>", body))
    for l in (data.limitations or ["нет"]):
        story.append(Paragraph(f"• {_ep(l)}", body))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Согласование</b>", body))
    review_data = [[Paragraph(_ep(f), body), ""] for f in data.review_fields]
    rt = Table(review_data, colWidths=[80 * mm, 60 * mm])
    rt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("FONTNAME", (0, 0), (-1, -1), "DejaVu")]))
    story.append(rt)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out_path), pagesize=A4, title=f"Лист согласования — {data.designation}")
    doc.build(story)
    return out_path
