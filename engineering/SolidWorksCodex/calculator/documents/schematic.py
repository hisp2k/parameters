# -*- coding: utf-8 -*-
"""
Предварительная размерная схема (раздел 2 и 13 задания).

"Предварительную геометрию показывай сразу после изменения параметров,
явно отличая её от проверенной CAD-модели" (раздел 2) и "Не оставляй
ссылку «см. схему», если схема отсутствует" (раздел 13) — раньше лист
согласования вообще не рисовал никакой геометрии, только текстовое поле
"нет подключения к CAD-ревизии". Этот модуль строит простую боковую схему
(труба под углом наклона, диаметр, длина, точки загрузки/выгрузки) из ОДНИХ
и тех же чисел (SchematicData) для HTML (инлайн SVG) и PDF (примитивы
reportlab.graphics) — то есть рендереры разные, а данные для картинки одни.

Это ПРЕДВАРИТЕЛЬНАЯ схема (не чертёж и не CAD-вид): пропорции упрощены для
читаемости, реальные диаметр/длина подписаны числами рядом.
"""

from __future__ import annotations

import html
import math
from dataclasses import dataclass


@dataclass
class SchematicData:
    working_length_mm: float
    incline_deg: float
    diameter_mm: float
    designation: str = ""
    is_preliminary: bool = True


def _layout(data: SchematicData, canvas_w: float = 560.0, canvas_h: float = 220.0):
    """Общая геометрия для обоих рендереров — упрощённый масштаб, не 1:1."""
    margin = 50.0
    usable_w = canvas_w - 2 * margin
    usable_h = canvas_h - 2 * margin

    angle_rad = math.radians(max(-20.0, min(20.0, data.incline_deg or 0.0)))
    # Масштаб по горизонтальной проекции длины, высота — по синусу угла.
    x0, y0 = margin, canvas_h - margin
    x1 = x0 + usable_w
    y1 = y0 - usable_w * math.tan(angle_rad)
    y1 = max(margin, min(canvas_h - margin, y1))

    # "Толщина" трубы на экране — не соответствует реальному масштабу диаметра
    # (иначе при большой разнице длина/диаметр труба выродится в линию или
    # займёт весь холст) — это явно предварительная схема, не чертёж.
    tube_half_h = min(22.0, max(10.0, usable_h * 0.12))
    return {
        "canvas_w": canvas_w, "canvas_h": canvas_h,
        "x0": x0, "y0": y0, "x1": x1, "y1": y1,
        "tube_half_h": tube_half_h,
        "angle_deg": math.degrees(angle_rad),
    }


def render_html_svg(data: SchematicData) -> str:
    g = _layout(data)
    x0, y0, x1, y1, th = g["x0"], g["y0"], g["x1"], g["y1"], g["tube_half_h"]
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length, dx / length  # нормаль к оси трубы

    def pt(px, py):
        return f"{px:.1f},{py:.1f}"

    tube_poly = " ".join([
        pt(x0 + nx * th, y0 + ny * th), pt(x1 + nx * th, y1 + ny * th),
        pt(x1 - nx * th, y1 - ny * th), pt(x0 - nx * th, y0 - ny * th),
    ])
    designation = html.escape(data.designation or "")
    preliminary_note = "ПРЕДВАРИТЕЛЬНО — не CAD-вид" if data.is_preliminary else "по CAD-модели"

    return f"""<svg viewBox="0 0 {g['canvas_w']:.0f} {g['canvas_h']:.0f}" xmlns="http://www.w3.org/2000/svg"
     style="background:#fafafa;border:1px solid #ccc;max-width:100%;">
  <polygon points="{tube_poly}" fill="#dde6f0" stroke="#33587a" stroke-width="2"/>
  <circle cx="{x0:.1f}" cy="{y0:.1f}" r="5" fill="#2a7a2a"/>
  <circle cx="{x1:.1f}" cy="{y1:.1f}" r="5" fill="#a02a2a"/>
  <text x="{x0:.1f}" y="{y0 + th + 18:.1f}" font-size="11" fill="#2a7a2a">загрузка</text>
  <text x="{x1 - 40:.1f}" y="{y1 - th - 8:.1f}" font-size="11" fill="#a02a2a">выгрузка</text>
  <text x="{(x0 + x1) / 2 - 60:.1f}" y="{max(y0, y1) + th + 34:.1f}" font-size="12" fill="#222">
    L(раб.)={data.working_length_mm:.0f} мм, угол={g['angle_deg']:.1f}°, D={data.diameter_mm:.0f} мм
  </text>
  <text x="8" y="16" font-size="11" fill="#a05a00" font-style="italic">{preliminary_note}: {designation}</text>
</svg>"""


def render_pdf_drawing(data: SchematicData):
    """Тот же макет через reportlab.graphics — используется в build_pdf()."""
    from reportlab.graphics.shapes import Drawing, Polygon, Circle, String

    g = _layout(data)
    x0, y0, x1, y1, th = g["x0"], g["y0"], g["x1"], g["y1"], g["tube_half_h"]
    # reportlab.graphics использует систему координат с Y вверх — переворачиваем.
    h = g["canvas_h"]
    y0r, y1r = h - y0, h - y1
    dx, dy = x1 - x0, y1r - y0r
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length, dx / length

    d = Drawing(g["canvas_w"], g["canvas_h"])
    d.add(Polygon(
        points=[
            x0 + nx * th, y0r + ny * th, x1 + nx * th, y1r + ny * th,
            x1 - nx * th, y1r - ny * th, x0 - nx * th, y0r - ny * th,
        ],
        fillColor="#dde6f0", strokeColor="#33587a", strokeWidth=1.2,
    ))
    d.add(Circle(x0, y0r, 4, fillColor="#2a7a2a", strokeColor=None))
    d.add(Circle(x1, y1r, 4, fillColor="#a02a2a", strokeColor=None))
    # fontName="DejaVu" ОБЯЗАТЕЛЕН: reportlab.graphics.shapes.String по
    # умолчанию использует Helvetica, который не содержит кириллицу — без
    # явного указания шрифта здесь текст выходил нечитаемыми прямоугольниками
    # (тот же класс бага, что и в reportlab.platypus, но String не наследует
    # шрифт из registerFontFamily() автоматически, нужно указывать на каждом
    # элементе отдельно).
    d.add(String(x0, y0r + th + 12, "загрузка", fontSize=8, fontName="DejaVu", fillColor="#2a7a2a"))
    d.add(String(x1 - 30, y1r - th - 12, "выгрузка", fontSize=8, fontName="DejaVu", fillColor="#a02a2a"))
    d.add(String(
        20, 10,
        f"L(раб.)={data.working_length_mm:.0f} мм, угол={g['angle_deg']:.1f}°, D={data.diameter_mm:.0f} мм",
        fontSize=8, fontName="DejaVu", fillColor="#222222",
    ))
    d.add(String(4, g["canvas_h"] - 12, "ПРЕДВАРИТЕЛЬНО — не CAD-вид", fontSize=8, fontName="DejaVu", fillColor="#a05a00"))
    return d
