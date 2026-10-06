"""JSON boundary for the input stage. Unknowns stay explicit."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .models import (
    CalculationRequest,
    DataStatus,
    FeedMode,
    MaterialClass,
    MaterialComponent,
    MaterialProfile,
    Property,
    QuantityRange,
)


def _property(raw: dict[str, Any] | None) -> Property:
    if raw is None:
        return Property(DataStatus.NOT_PROVIDED)
    status = DataStatus(raw["status"])
    quantity = None
    if raw.get("quantity") is not None:
        q = raw["quantity"]
        quantity = QuantityRange(
            Decimal(str(q["minimum"])),
            Decimal(str(q["nominal"])),
            Decimal(str(q["maximum"])),
            q["unit"],
        )
    return Property(
        status=status,
        quantity=quantity,
        source=raw.get("source"),
        observed_at=raw.get("observed_at"),
        method=raw.get("method"),
        confidence=raw.get("confidence"),
    )


def request_from_dict(raw: dict[str, Any]) -> CalculationRequest:
    material = raw["material"]
    return CalculationRequest(
        request_id=raw["request_id"],
        product_profile_id=raw["product_profile_id"],
        material=MaterialProfile(
            material_id=material["material_id"],
            version=material["version"],
            material_class=MaterialClass(material["material_class"]),
            physical_model_id=material.get("physical_model_id"),
            properties={k: _property(v) for k, v in material.get("properties", {}).items()},
            evidence_refs=material.get("evidence_refs", {}),
            components=tuple(
                MaterialComponent(
                    component_id=c["component_id"],
                    name=c["name"],
                    properties={k: _property(v) for k, v in c.get("properties", {}).items()},
                    reported_values=c.get("reported_values", {}),
                    evidence_refs=c.get("evidence_refs", {}),
                )
                for c in material.get("components", [])
            ),
        ),
        feed_mode=FeedMode(raw.get("feed_mode", "UNKNOWN")),
        target_flow=_property(raw.get("target_flow")),
        length=_property(raw.get("length")),
        angle=_property(raw.get("angle")),
        operating_hours_per_day=_property(raw.get("operating_hours_per_day")) if raw.get("operating_hours_per_day") else None,
        starts_per_hour=_property(raw.get("starts_per_hour")) if raw.get("starts_per_hour") else None,
    )
