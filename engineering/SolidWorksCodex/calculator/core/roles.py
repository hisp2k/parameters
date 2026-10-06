# -*- coding: utf-8 -*-
"""
Три роли (раздел 5 задания). Только эти три — расчётные модули и сервисы
ролями не являются.

Права здесь — минимальный, проверяемый список действий, а не полноценная
система авторизации (для неё нужны реальные пользователи/логин, которых
пока нет). Цель на этом этапе: чтобы КАЖДОЕ чувствительное действие в коде
проходило через can(), а не проверялось "на глаз" в разных местах.

ИСПРАВЛЕНИЕ (раздел 2 задания — "Не предоставляй инженерные полномочия
автоматически только потому, что пользователь руководитель"): раньше
инженерные действия (`review_strength_and_drive`, `rebuild_cad_project_copy`
и т.п.) были разрешены множеству {ENGINEER, HEAD} — то есть человек с ролью
"руководитель" молча получал права инженера просто потому, что руководитель
"выше". Теперь `_PERMISSIONS` содержит РОВНО ту роль, которой действие
принадлежит по разделу 5, без автоматического наследования. Человек, который
на предприятии совмещает роли (например, ведущий инженер = руководитель),
должен явно объявить, в качестве какой роли он действует — для этого
используется `can_as()`/`RoleContext`, которые требуют явного
`acting_as` и логируют совмещение, а не выводят его из одной лишь личности
пользователя.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    MANAGER = "менеджер"
    ENGINEER = "инженер"
    HEAD = "руководитель"


# Действие -> РОВНО ОДНА роль, которой оно принадлежит по разделу 5. Никакого
# неявного наследования "старшей" ролью — см. can_as() для совмещения ролей.
_PERMISSIONS: dict[str, set[Role]] = {
    "input_requirements": {Role.MANAGER, Role.ENGINEER, Role.HEAD},
    "preliminary_selection": {Role.MANAGER, Role.ENGINEER, Role.HEAD},
    "create_preliminary_agreement_sheet": {Role.MANAGER, Role.ENGINEER, Role.HEAD},
    "submit_for_review": {Role.MANAGER, Role.ENGINEER, Role.HEAD},

    "confirm_inputs_assumptions": {Role.ENGINEER},
    "review_strength_and_drive": {Role.ENGINEER},
    "rebuild_cad_project_copy": {Role.ENGINEER},
    "review_kd_bom": {Role.ENGINEER},
    "develop_technology": {Role.ENGINEER},
    "maintain_reference_registries": {Role.ENGINEER},
    "prepare_release_package": {Role.ENGINEER},

    "manage_access": {Role.HEAD},
    "approve_rates_prices_economics": {Role.HEAD},
    "approve_nonstandard_decision": {Role.HEAD},
    "approve_methodology_change": {Role.HEAD},  # только после инженерной проверки — см. can()
    "authorize_production_release": {Role.HEAD},  # только по проверенному комплекту — см. release_gate.py
}


def can(role: Role, action: str) -> bool:
    """
    Управленческое утверждение НЕ заменяет техническую проверку (раздел 5).
    Поэтому can() отвечает только "имеет ли ЭТА КОНКРЕТНАЯ роль право нажать
    кнопку" — без учёта того, какие ещё роли назначены тому же человеку.
    """
    allowed = _PERMISSIONS.get(action)
    if allowed is None:
        raise ValueError(f"Неизвестное действие для проверки прав: {action!r}")
    return role in allowed


def require(role: Role, action: str) -> None:
    if not can(role, action):
        raise PermissionError(f"Роль {role.value!r} не может выполнить действие {action!r}")


@dataclass
class RoleContext:
    """
    Явное совмещение ролей одним человеком (раздел 2: "совмещение ролей
    должно быть явным"). person_name — кто именно; assigned_roles — какие
    роли этому человеку назначены на проекте; acting_as — КАК ИМЕННО он
    действует в этом конкретном действии. Ни одно действие не проверяется
    по всему набору assigned_roles сразу — только по acting_as, и это
    выбор, который интерфейс обязан спросить явно (а не подставить
    "старшую" роль по умолчанию).
    """

    person_name: str
    assigned_roles: set[Role]
    acting_as: Role

    def __post_init__(self) -> None:
        if self.acting_as not in self.assigned_roles:
            raise PermissionError(
                f"{self.person_name!r} не назначен(а) ролью {self.acting_as.value!r} "
                f"на этом проекте (назначены: {[r.value for r in self.assigned_roles]}) — "
                "нельзя действовать от роли, которая явно не назначена."
            )

    def can(self, action: str) -> bool:
        return can(self.acting_as, action)

    def require(self, action: str) -> None:
        if not self.can(action):
            raise PermissionError(
                f"{self.person_name!r}, действуя как {self.acting_as.value!r}, "
                f"не может выполнить действие {action!r}."
            )

    def label(self) -> str:
        """Как это должно отображаться в документах/логах: имя + роль, в которой действовал."""
        combo = ""
        if len(self.assigned_roles) > 1:
            others = sorted(r.value for r in self.assigned_roles if r != self.acting_as)
            combo = f" (совмещает также: {', '.join(others)})"
        return f"{self.person_name} — {self.acting_as.value}{combo}"
