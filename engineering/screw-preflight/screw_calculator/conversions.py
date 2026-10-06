"""Exact unit and interval conversions, without a conveying model."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .models import DataStatus, Property
from .units import dimension, from_si


@dataclass(frozen=True)
class FlowScenarios:
    minimum_m3_h: Decimal
    nominal_m3_h: Decimal
    maximum_m3_h: Decimal
    trace: tuple[str, ...]


def volume_flow_scenarios(target_flow: Property, density: Property | None = None) -> FlowScenarios:
    """Convert target flow to volume, pairing extremes conservatively.

    This is an input transformation, not screw conveyor capacity.
    """
    if target_flow.status != DataStatus.CONFIRMED or target_flow.quantity is None:
        raise ValueError("Confirmed target flow is required")
    flow = target_flow.quantity
    flow_dimension = dimension(flow.unit)
    if flow_dimension == "volume_flow":
        lower, nominal, upper = flow.si("volume_flow")
        return FlowScenarios(
            *(from_si(x, "m3/h", "volume_flow") for x in (lower, nominal, upper)),
            ("Direct volumetric target conversion",),
        )
    if flow_dimension != "mass_flow":
        raise ValueError("Target flow must be mass flow or volume flow")
    if density is None or density.status != DataStatus.CONFIRMED or density.quantity is None:
        raise ValueError("Confirmed density range is required for mass flow")
    mass_min, mass_nom, mass_max = flow.si("mass_flow")
    density_min, density_nom, density_max = density.quantity.si("density")
    if mass_min <= 0 or density_min <= 0:
        raise ValueError("Mass flow and density must be positive")
    return FlowScenarios(
        from_si(mass_min / density_max, "m3/h", "volume_flow"),
        from_si(mass_nom / density_nom, "m3/h", "volume_flow"),
        from_si(mass_max / density_min, "m3/h", "volume_flow"),
        ("Qv,min = m_min / rho_max", "Qv,nom = m_nom / rho_nom", "Qv,max = m_max / rho_min"),
    )
