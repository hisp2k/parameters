"""Required properties and profile compatibility for the input gate."""

from __future__ import annotations

from dataclasses import dataclass

from .models import MaterialClass


@dataclass(frozen=True)
class PropertySpec:
    name: str
    dimension: str
    positive: bool = False
    lower_bound: str | None = None
    upper_bound: str | None = None


MATERIAL_SPECS: dict[MaterialClass, tuple[PropertySpec, ...]] = {
    MaterialClass.SLUDGE_DEWATERED: (
        PropertySpec("wet_density", "density", positive=True),
        PropertySpec("dry_solids_mass_fraction", "fraction", lower_bound="0", upper_bound="1"),
        PropertySpec("max_inclusion_size", "length", lower_bound="0"),
        PropertySpec("temperature", "temperature_c"),
    ),
    MaterialClass.BULK_FREE_FLOWING: (
        PropertySpec("bulk_density", "density", positive=True),
        PropertySpec("max_inclusion_size", "length", lower_bound="0"),
        PropertySpec("temperature", "temperature_c"),
    ),
    MaterialClass.BULK_COHESIVE: (
        PropertySpec("bulk_density", "density", positive=True),
        PropertySpec("moisture_mass_fraction", "fraction", lower_bound="0", upper_bound="1"),
        PropertySpec("max_inclusion_size", "length", lower_bound="0"),
        PropertySpec("temperature", "temperature_c"),
    ),
    MaterialClass.SLURRY_OR_FREE_LIQUID: (
        PropertySpec("mixture_density", "density", positive=True),
        PropertySpec("solids_mass_fraction", "fraction", lower_bound="0", upper_bound="1"),
        PropertySpec("temperature", "temperature_c"),
    ),
}


# The bulk profile is deliberately incompatible with sludge and liquid.
ALLOWED_MATERIALS: dict[str, frozenset[MaterialClass]] = {
    "SCREW_TUBE_H_BULK_V1": frozenset(
        {MaterialClass.BULK_FREE_FLOWING, MaterialClass.BULK_COHESIVE}
    ),
    "SCREW_SLUDGE_CONCEPT_V0": frozenset({MaterialClass.SLUDGE_DEWATERED}),
}
