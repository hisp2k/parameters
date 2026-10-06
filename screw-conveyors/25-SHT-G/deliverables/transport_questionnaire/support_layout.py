"""Body-support counts for the trough conveyor.

One support station contains one 01.01 and one 08.00 body support.
The number of spans is rounded up so their length never exceeds 3000 mm.
"""

from __future__ import annotations

import math

MAX_SUPPORT_SPAN_MM = 3000.0


def body_support_layout(working_length_mm: float) -> dict:
    length = float(working_length_mm)
    if not math.isfinite(length) or length <= 0:
        raise ValueError("Длина рабочей части желоба должна быть положительной")
    spans = math.ceil(length / MAX_SUPPORT_SPAN_MM)
    stations = spans + 1
    return {
        "rule": "maximum_span",
        "maximum_span_mm": MAX_SUPPORT_SPAN_MM,
        "span_count": spans,
        "station_count": stations,
        "support_01_01_count": stations,
        "support_08_00_count": stations,
        "calculated_equal_span_mm": length / spans,
        "geometry_status": "quantity_plan_only_actual_support_positions_require_CAD_mapping",
    }
