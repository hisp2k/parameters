"""Explicit conversions to the SI units used by the input layer."""

from __future__ import annotations

from decimal import Decimal


class UnitError(ValueError):
    pass


# Dimension, multiplier to internal SI unit. Internal rates are per second.
_UNITS: dict[str, tuple[str, Decimal]] = {
    "kg/s": ("mass_flow", Decimal("1")),
    "kg/h": ("mass_flow", Decimal("1") / Decimal("3600")),
    "t/h": ("mass_flow", Decimal("1000") / Decimal("3600")),
    "lb/h": ("mass_flow", Decimal("0.45359237") / Decimal("3600")),
    "m3/s": ("volume_flow", Decimal("1")),
    "m3/h": ("volume_flow", Decimal("1") / Decimal("3600")),
    "ft3/h": ("volume_flow", Decimal("0.028316846592") / Decimal("3600")),
    "kg/m3": ("density", Decimal("1")),
    "lb/ft3": ("density", Decimal("0.45359237") / Decimal("0.028316846592")),
    "m": ("length", Decimal("1")),
    "mm": ("length", Decimal("0.001")),
    "ft": ("length", Decimal("0.3048")),
    "in": ("length", Decimal("0.0254")),
    "deg": ("angle", Decimal("1")),
    "C": ("temperature_c", Decimal("1")),
    "fraction": ("fraction", Decimal("1")),
    "%": ("fraction", Decimal("0.01")),
}


def dimension(unit: str) -> str:
    try:
        return _UNITS[unit][0]
    except KeyError as exc:
        raise UnitError(f"Unsupported unit: {unit}") from exc


def to_si(value: Decimal, unit: str, expected_dimension: str) -> Decimal:
    actual_dimension = dimension(unit)
    if actual_dimension != expected_dimension:
        raise UnitError(
            f"Unit {unit} has dimension {actual_dimension}; expected {expected_dimension}"
        )
    return value * _UNITS[unit][1]


def from_si(value: Decimal, unit: str, expected_dimension: str) -> Decimal:
    actual_dimension = dimension(unit)
    if actual_dimension != expected_dimension:
        raise UnitError(
            f"Unit {unit} has dimension {actual_dimension}; expected {expected_dimension}"
        )
    return value / _UNITS[unit][1]
