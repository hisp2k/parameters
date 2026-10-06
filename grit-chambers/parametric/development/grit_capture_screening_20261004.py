"""Analytical screening only; this does not calculate grit-chamber capture."""

import csv
import math
from pathlib import Path

RHO_WATER = 998.2  # kg/m3, assumed clean water at 20 C
MU_WATER = 0.001002  # Pa s
RHO_PARTICLE = 2650.0  # kg/m3, assumed spherical mineral particle
GRAVITY = 9.81  # m/s2
FLOW = 0.006  # m3/s
DEPTH = 0.55  # m, nominal
DIAMETERS_MM = (0.10, 0.15, 0.20, 0.30, 0.50)
CONFIGURATIONS = (
    ("BASE_700x900", 0.70, 0.90, 255),
    ("NARROW_600x1050", 0.60, 1.05, 210),
    ("SHORT_WIDE_800x800", 0.80, 0.80, 285),
)


def terminal_speed(diameter_m):
    """Solve buoyant weight = Schiller-Naumann drag for Re < 1000."""
    rhs = (4.0 / 3.0) * (RHO_PARTICLE / RHO_WATER - 1.0) * GRAVITY * diameter_m

    def residual(speed):
        reynolds = RHO_WATER * speed * diameter_m / MU_WATER
        drag = 24.0 / reynolds * (1.0 + 0.15 * reynolds**0.687)
        return drag * speed**2 - rhs

    low, high = 1e-12, 1.0
    for _ in range(100):
        mid = (low + high) / 2.0
        if residual(mid) < 0.0:
            low = mid
        else:
            high = mid
    speed = (low + high) / 2.0
    reynolds = RHO_WATER * speed * diameter_m / MU_WATER
    if reynolds >= 1000:
        raise ValueError("Drag correlation outside the assumed Reynolds range")
    return speed, reynolds


def main():
    rows = []
    for name, width, length, hole_count in CONFIGURATIONS:
        area = width * length
        overflow_rate = FLOW / area
        nominal_time = area * DEPTH / FLOW
        screen_open_area = hole_count * math.pi * (0.022**2) / 4.0
        screen_side_gap_area = 2.0 * 0.03 * DEPTH
        screen_velocity = FLOW / screen_open_area
        impact_gap_velocity = FLOW / (0.22 * width)
        outlet_underflow_velocity = FLOW / (0.32 * width)
        for diameter_mm in DIAMETERS_MM:
            speed, reynolds = terminal_speed(diameter_mm / 1000.0)
            capture_number = speed / overflow_rate
            ideal_capture = min(1.0, capture_number)
            mixed_capture = capture_number / (1.0 + capture_number)
            area_for_70 = 0.70 * FLOW / speed
            mixed_area_for_70 = (0.70 / 0.30) * FLOW / speed
            rows.append(
                {
                    "configuration": name,
                    "diameter_mm": diameter_mm,
                    "particle_reynolds": reynolds,
                    "terminal_speed_m_s": speed,
                    "nominal_settling_area_m2": area,
                    "surface_loading_m_s": overflow_rate,
                    "nominal_residence_s": nominal_time,
                    "full_depth_settling_s": DEPTH / speed,
                    "ideal_capture_percent": 100.0 * ideal_capture,
                    "fully_mixed_capture_percent": 100.0 * mixed_capture,
                    "maximum_direct_bypass_fraction_for_70_in_mixed_model": max(
                        0.0, 1.0 - 0.70 / mixed_capture
                    ),
                    "effective_area_for_70_percent_m2": area_for_70,
                    "effective_area_fraction_for_70_percent": area_for_70 / area,
                    "mixed_model_area_for_70_percent_m2": mixed_area_for_70,
                    "mixed_model_area_fraction_for_70_percent": mixed_area_for_70 / area,
                    "screen_open_area_m2": screen_open_area,
                    "screen_side_gap_geometric_area_m2": screen_side_gap_area,
                    "screen_side_gap_share_of_holes_plus_side_gaps": screen_side_gap_area
                    / (screen_open_area + screen_side_gap_area),
                    "screen_mean_speed_m_s": screen_velocity,
                    "impact_gap_mean_speed_m_s": impact_gap_velocity,
                    "outlet_underflow_mean_speed_m_s": outlet_underflow_velocity,
                    "actual_capture_percent": "UNKNOWN",
                }
            )

    out = Path(r"C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\03_Результаты")
    out.mkdir(parents=True, exist_ok=True)
    path = out / "GRIT_CAPTURE_SCREENING_20261004.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        if row["diameter_mm"] == 0.20:
            print(
                row["configuration"],
                "v_settle=", round(row["terminal_speed_m_s"], 5),
                "Re=", round(row["particle_reynolds"], 3),
                "ideal_eta=", round(row["ideal_capture_percent"], 1),
                "mixed_eta=", round(row["fully_mixed_capture_percent"], 1),
                "mixed_bypass_limit=", round(row["maximum_direct_bypass_fraction_for_70_in_mixed_model"], 3),
                "A70=", round(row["effective_area_for_70_percent_m2"], 3),
                "A70_fraction=", round(row["effective_area_fraction_for_70_percent"], 3),
                "mixed_A70_fraction=", round(row["mixed_model_area_fraction_for_70_percent"], 3),
                "screen_v=", round(row["screen_mean_speed_m_s"], 3),
                "impact_v=", round(row["impact_gap_mean_speed_m_s"], 3),
                "outlet_under_v=", round(row["outlet_underflow_mean_speed_m_s"], 3),
            )
    print(path)


if __name__ == "__main__":
    main()
