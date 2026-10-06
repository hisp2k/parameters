"""Independent intake calculation using a published KWS example.

Run directly. It deliberately does not import screw_calculator.
It verifies unit conversions only; no machine sizing is inferred.
Source: https://www.kwsmfg.com/resources/problem-solvers/shaftless-screw-conveyor-system-for-conveying-biosolids/
"""

from decimal import Decimal
import json


def calculate() -> dict[str, str]:
    volume_ft3_h = Decimal("150")
    density_lb_ft3 = Decimal("60")
    dry_fraction_min = Decimal("0.15")
    dry_fraction_max = Decimal("0.21")

    ft3_to_m3 = Decimal("0.028316846592")
    lb_to_kg = Decimal("0.45359237")

    volume_m3_h = volume_ft3_h * ft3_to_m3
    wet_mass_lb_h = volume_ft3_h * density_lb_ft3
    wet_mass_kg_h = wet_mass_lb_h * lb_to_kg
    wet_density_kg_m3 = density_lb_ft3 * lb_to_kg / ft3_to_m3
    dry_mass_min_kg_h = wet_mass_kg_h * dry_fraction_min
    dry_mass_max_kg_h = wet_mass_kg_h * dry_fraction_max

    return {
        "reference": "KWS published dewatered biosolids case; shaftless equipment, not a tube-conveyor validation",
        "input_volume_ft3_h": str(volume_ft3_h),
        "input_wet_density_lb_ft3": str(density_lb_ft3),
        "input_dry_solids_mass_fraction_min": str(dry_fraction_min),
        "input_dry_solids_mass_fraction_max": str(dry_fraction_max),
        "volume_m3_h": str(volume_m3_h),
        "wet_density_kg_m3": str(wet_density_kg_m3),
        "wet_mass_kg_h": str(wet_mass_kg_h),
        "dry_mass_min_kg_h": str(dry_mass_min_kg_h),
        "dry_mass_max_kg_h": str(dry_mass_max_kg_h),
        "design_status": "NOT_CALCULATED",
    }


if __name__ == "__main__":
    print(json.dumps(calculate(), ensure_ascii=False, indent=2))
