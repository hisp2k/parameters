"""Preflight checks. READY_FOR_ENGINEERING_MODEL is never a design approval."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .models import CalculationRequest, DataStatus, FeedMode, Property
from .profiles import ALLOWED_MATERIALS, MATERIAL_SPECS, PropertySpec
from .units import UnitError


@dataclass(frozen=True)
class Issue:
    code: str
    field: str
    message: str
    status: str  # BLOCK or UNKNOWN


@dataclass(frozen=True)
class PreflightResult:
    status: str  # BLOCK, UNKNOWN, or READY_FOR_ENGINEERING_MODEL
    issues: tuple[Issue, ...]


def _check_property(
    field_name: str, prop: Property | None, spec: PropertySpec, issues: list[Issue]
) -> tuple[Decimal, Decimal, Decimal] | None:
    if prop is None or prop.status != DataStatus.CONFIRMED or prop.quantity is None:
        issues.append(Issue("PROPERTY_REQUIRED", field_name, "Confirmed value and source required", "UNKNOWN"))
        return None
    try:
        values = prop.quantity.si(spec.dimension)
    except UnitError as exc:
        issues.append(Issue("INVALID_UNIT", field_name, str(exc), "BLOCK"))
        return None
    if spec.positive and values[0] <= 0:
        issues.append(Issue("INVALID_RANGE", field_name, "Minimum must be greater than zero", "BLOCK"))
    if spec.lower_bound is not None and values[0] < Decimal(spec.lower_bound):
        issues.append(Issue("INVALID_RANGE", field_name, f"Minimum is below {spec.lower_bound}", "BLOCK"))
    if spec.upper_bound is not None and values[2] > Decimal(spec.upper_bound):
        issues.append(Issue("INVALID_RANGE", field_name, f"Maximum exceeds {spec.upper_bound}", "BLOCK"))
    return values


def preflight(request: CalculationRequest) -> PreflightResult:
    issues: list[Issue] = []
    permitted = ALLOWED_MATERIALS.get(request.product_profile_id)
    if permitted is None:
        issues.append(Issue("PROFILE_NOT_FOUND", "product_profile_id", "Unknown product profile", "BLOCK"))
    elif request.material.material_class not in permitted:
        issues.append(Issue("MATERIAL_MODEL_MISMATCH", "material.material_class", "Material and product profile are incompatible", "BLOCK"))

    if request.feed_mode == FeedMode.UNKNOWN:
        issues.append(Issue("FEED_MODE_REQUIRED", "feed_mode", "Feed mode must be established", "UNKNOWN"))
    elif request.feed_mode == FeedMode.FLOOD and request.product_profile_id == "SCREW_TUBE_H_BULK_V1":
        issues.append(Issue("FLOOD_FEED_UNSUPPORTED", "feed_mode", "Use a separately validated feeder model", "BLOCK"))

    if not request.material.physical_model_id:
        issues.append(Issue("PHYSICAL_MODEL_REQUIRED", "material.physical_model_id", "Physical model ID is required", "UNKNOWN"))

    target = request.target_flow.quantity
    if request.target_flow.status != DataStatus.CONFIRMED or target is None:
        issues.append(Issue("TARGET_FLOW_REQUIRED", "target_flow", "Confirmed target flow required", "UNKNOWN"))
    else:
        try:
            target_dimension = "mass_flow" if target.unit in {"kg/s", "kg/h", "t/h", "lb/h"} else "volume_flow"
            rates = target.si(target_dimension)
            if rates[0] <= 0:
                issues.append(Issue("INVALID_RANGE", "target_flow", "Flow must be positive", "BLOCK"))
            density_key = "wet_density" if request.material.material_class.value == "SLUDGE_DEWATERED" else "bulk_density"
            if target_dimension == "mass_flow" and density_key not in request.material.properties:
                issues.append(Issue("DENSITY_REQUIRED", f"material.{density_key}", "Density range required for volume conversion", "UNKNOWN"))
        except UnitError as exc:
            issues.append(Issue("INVALID_UNIT", "target_flow", str(exc), "BLOCK"))

    _check_property("length", request.length, PropertySpec("length", "length", positive=True), issues)
    angle_values = _check_property("angle", request.angle, PropertySpec("angle", "angle"), issues)
    if angle_values and request.product_profile_id == "SCREW_TUBE_H_BULK_V1" and any(x != 0 for x in angle_values):
        issues.append(Issue("ANGLE_OUT_OF_PROFILE", "angle", "Bulk MVP is horizontal only", "BLOCK"))

    for spec in MATERIAL_SPECS[request.material.material_class]:
        _check_property(f"material.{spec.name}", request.material.properties.get(spec.name), spec, issues)

    # These conditions need a separate material test or engineering decision.
    if request.material.material_class.value == "SLUDGE_DEWATERED":
        for name in ("adhesion_assessment", "drainage_assessment", "fibrous_inclusions_assessment"):
            if not request.material.evidence_refs.get(name):
                issues.append(Issue("ENGINEERING_EVIDENCE_REQUIRED", f"material.{name}", "Assessment reference required before design release", "UNKNOWN"))

    for component in request.material.components:
        if component.component_id == "SAND":
            _check_property(
                "material.components.SAND.mass_fraction_of_wet_mixture",
                component.properties.get("mass_fraction_of_wet_mixture"),
                PropertySpec("mass_fraction_of_wet_mixture", "fraction", lower_bound="0", upper_bound="1"),
                issues,
            )
            _check_property(
                "material.components.SAND.max_particle_size",
                component.properties.get("max_particle_size"),
                PropertySpec("max_particle_size", "length", positive=True),
                issues,
            )
            _check_property(
                "material.components.SAND.water_content_dry_basis",
                component.properties.get("water_content_dry_basis"),
                PropertySpec("water_content_dry_basis", "fraction", lower_bound="0"),
                issues,
            )
            if not component.evidence_refs.get("moisture_basis"):
                issues.append(Issue("MOISTURE_BASIS_REQUIRED", "material.components.SAND.moisture", "Clarify whether reported moisture is water per dry sand mass or wet mixture mass", "UNKNOWN"))
            if not component.evidence_refs.get("mixing_homogeneity"):
                issues.append(Issue("MIXING_STATE_REQUIRED", "material.components.SAND.mixing_homogeneity", "Establish whether sand is uniformly mixed or settles", "UNKNOWN"))
            if not request.material.evidence_refs.get("mixture_density_measurement"):
                issues.append(Issue("MIXTURE_DENSITY_REQUIRED", "material.wet_density", "Wet density must be measured for the sand-sludge mixture", "UNKNOWN"))

    status = "BLOCK" if any(x.status == "BLOCK" for x in issues) else "UNKNOWN" if issues else "READY_FOR_ENGINEERING_MODEL"
    return PreflightResult(status, tuple(issues))
