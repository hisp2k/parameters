"""Immutable, provenance-aware input objects. No engineering coefficients live here."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Mapping

from .units import dimension, to_si


class DataStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    NOT_MEASURED = "NOT_MEASURED"
    NOT_PROVIDED = "NOT_PROVIDED"
    REQUIRES_CALCULATION = "REQUIRES_CALCULATION"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MaterialClass(str, Enum):
    BULK_FREE_FLOWING = "BULK_FREE_FLOWING"
    BULK_COHESIVE = "BULK_COHESIVE"
    SLUDGE_DEWATERED = "SLUDGE_DEWATERED"
    SLURRY_OR_FREE_LIQUID = "SLURRY_OR_FREE_LIQUID"


class FeedMode(str, Enum):
    CONTROLLED = "CONTROLLED"
    FLOOD = "FLOOD"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class QuantityRange:
    """Range in the supplied unit, with nominal between lower and upper."""

    minimum: Decimal
    nominal: Decimal
    maximum: Decimal
    unit: str

    def __post_init__(self) -> None:
        dimension(self.unit)
        if not all(x.is_finite() for x in (self.minimum, self.nominal, self.maximum)):
            raise ValueError("Quantity values must be finite")
        if not self.minimum <= self.nominal <= self.maximum:
            raise ValueError("Expected minimum <= nominal <= maximum")

    def si(self, expected_dimension: str) -> tuple[Decimal, Decimal, Decimal]:
        return tuple(
            to_si(value, self.unit, expected_dimension)
            for value in (self.minimum, self.nominal, self.maximum)
        )


@dataclass(frozen=True)
class Property:
    status: DataStatus
    quantity: QuantityRange | None = None
    source: str | None = None
    observed_at: str | None = None
    method: str | None = None
    confidence: str | None = None

    def __post_init__(self) -> None:
        if self.status == DataStatus.CONFIRMED:
            if self.quantity is None or not self.source:
                raise ValueError("Confirmed property requires quantity and source")
        elif self.quantity is not None:
            raise ValueError("Unconfirmed property must not carry a numeric quantity")


@dataclass(frozen=True)
class MaterialComponent:
    component_id: str
    name: str
    properties: Mapping[str, Property] = field(default_factory=dict)
    reported_values: Mapping[str, str] = field(default_factory=dict)
    evidence_refs: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class MaterialProfile:
    material_id: str
    version: str
    material_class: MaterialClass
    physical_model_id: str | None
    properties: Mapping[str, Property] = field(default_factory=dict)
    evidence_refs: Mapping[str, str] = field(default_factory=dict)
    components: tuple[MaterialComponent, ...] = ()


@dataclass(frozen=True)
class CalculationRequest:
    request_id: str
    product_profile_id: str
    material: MaterialProfile
    feed_mode: FeedMode
    target_flow: Property
    length: Property
    angle: Property
    operating_hours_per_day: Property | None = None
    starts_per_hour: Property | None = None
