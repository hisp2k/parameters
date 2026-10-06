# -*- coding: utf-8 -*-
"""
Единая модель параметра приложения (раздел 19 задания):
значение, единица, источник, статус, автор, дата.

Любое числовое или текстовое значение, которое течёт между модулями
(опросный лист -> инженерное ядро -> CAD -> документы -> экономика),
должно быть обёрнуто в Parameter, а не быть "голым" float/str. Это даёт
единый способ ответить на вопрос "откуда это число и можно ли ему верить"
в любом месте системы — в том числе в листе согласования и в блокировках
выпуска (release_gate.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class ParamStatus(str, Enum):
    """Статус достоверности значения параметра."""

    USER_INPUT = "введено_пользователем"
    CALCULATED = "рассчитано"
    CALCULATED_PRELIMINARY = "рассчитано_предварительно"  # черновая методика, не подтверждена
    CAD_READBACK = "считано_из_cad"
    CATALOG = "из_каталога"
    ASSUMED_DEFAULT = "принято_по_умолчанию"  # видимое допущение, требует подтверждения
    NOT_VERIFIED = "не_проверено"
    MISSING = "отсутствует"


@dataclass
class Parameter:
    """Один параметр с полной историей происхождения."""

    name: str
    value: Any
    unit: str = ""
    source: str = ""
    status: ParamStatus = ParamStatus.NOT_VERIFIED
    author: str = "system"
    date: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    note: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "status": self.status.value if isinstance(self.status, ParamStatus) else self.status,
            "author": self.author,
            "date": self.date,
            "note": self.note,
        }

    @staticmethod
    def from_dict(d: dict) -> "Parameter":
        status = d.get("status", ParamStatus.NOT_VERIFIED.value)
        try:
            status = ParamStatus(status)
        except ValueError:
            status = ParamStatus.NOT_VERIFIED
        return Parameter(
            name=d["name"],
            value=d.get("value"),
            unit=d.get("unit", ""),
            source=d.get("source", ""),
            status=status,
            author=d.get("author", "system"),
            date=d.get("date", datetime.now(timezone.utc).isoformat()),
            note=d.get("note"),
        )

    def is_confirmed(self) -> bool:
        """Можно ли опираться на это значение при формировании УТВЕРЖДЁННОГО комплекта."""
        return self.status in (
            ParamStatus.USER_INPUT,
            ParamStatus.CALCULATED,
            ParamStatus.CAD_READBACK,
            ParamStatus.CATALOG,
        )


class ParameterSet(dict):
    """Именованный набор параметров с удобными методами добавления/выгрузки."""

    def put(self, name: str, value: Any, unit: str = "", source: str = "",
            status: ParamStatus = ParamStatus.NOT_VERIFIED, author: str = "system",
            note: Optional[str] = None) -> Parameter:
        p = Parameter(name=name, value=value, unit=unit, source=source,
                      status=status, author=author, note=note)
        self[name] = p
        return p

    def value_of(self, name: str, default: Any = None) -> Any:
        p = self.get(name)
        return p.value if p is not None else default

    def to_dict(self) -> dict:
        return {k: v.to_dict() for k, v in self.items()}

    @staticmethod
    def from_dict(d: dict) -> "ParameterSet":
        ps = ParameterSet()
        for k, v in d.items():
            ps[k] = Parameter.from_dict(v)
        return ps

    def unconfirmed(self) -> list[str]:
        return [name for name, p in self.items() if not p.is_confirmed()]
