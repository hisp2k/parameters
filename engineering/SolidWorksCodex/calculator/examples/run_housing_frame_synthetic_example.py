# -*- coding: utf-8 -*-
"""
Отдельно воспроизводимый прогон синтетического примера цепочки
«вал -> подшипники -> корпус -> рама -> основание» после раунда
исправлений по независимой проверке коммита c24d42b (18-19.09.2026).

Запуск (из каталога, СОДЕРЖАЩЕГО calculator/, т.е. на уровень выше):

    python3 -m calculator.examples.run_housing_frame_synthetic_example

или (из каталога calculator/):

    PYTHONPATH=.. python3 examples/run_housing_frame_synthetic_example.py

Это ИССЛЕДОВАТЕЛЬСКИЙ синтетический пример (см. StructuralChainResult.
is_research_only=True) — НЕ результат для реального изделия TUBE-SAND-001.
Вывод этого скрипта сохранён рядом (run_housing_frame_synthetic_example.
output.txt) как машинный артефакт для отчёта TUBE_HOUSING_FRAME_STAGE_RU.md.
"""
import dataclasses

from calculator.core.housing_frame_study import (
    calculate_structural_chain,
    synthetic_example_geometry_and_loads,
)


def main() -> None:
    geometry, loads, clearance_inputs, bearing_catalog = synthetic_example_geometry_and_loads()
    result = calculate_structural_chain(geometry, loads, clearance_inputs, bearing_catalog)

    print("=== Вход (синтетический, не TUBE-SAND-001) ===")
    print(geometry)
    print(loads)
    print(clearance_inputs)
    print(bearing_catalog)

    def _max_abs(residual_dict: dict) -> float:
        return max(abs(v) for v in residual_dict.values())

    print()
    print("=== Равновесие (независимые проверки, max|компонента|) ===")
    print(f"equilibrium_residual (внутр. решатель, K*u):      {_max_abs(result.equilibrium_residual):.3e}")
    print(f"independent_free_body_residual (через loads):     {_max_abs(result.independent_free_body_residual):.3e}")
    print(f"raw_external_load_free_body_residual (сырые вх.): {_max_abs(result.raw_external_load_free_body_residual):.3e}")

    print()
    print("=== Реакции основания ===")
    for node_id, reaction in sorted(result.base_reactions.items()):
        print(f"  {node_id}: {reaction}")
    print(f"base_reaction_total_z_n = {result.base_reaction_total_z_n:.3f} Н")

    print()
    print("=== Усилия по стержням (member_forces) ===")
    for member_id, forces in result.member_forces.items():
        print(f"  {member_id}: {forces}")

    print()
    print("=== Вал: изгиб + кручение ===")
    print(f"shaft_von_mises_mpa = {result.shaft_von_mises_mpa:.3f} МПа")
    print(f"shaft_shear_deflection_estimate = {result.shaft_shear_deflection_estimate}")

    print()
    print("=== Подшипники (синтетический каталог) ===")
    for label, bearing in result.bearing_results.items():
        print(f"  {label}: {bearing}")

    print()
    print("=== Зазор вал/корпус ===")
    for section in result.clearance.all_sections:
        print(
            f"  {section.label:>14s}: consumed={section.consumed_by_deflection_mm:.4f} мм"
        )
    governing = result.clearance.governing_section
    print(f"  governing = {governing.label}, consumed={governing.consumed_by_deflection_mm:.4f} мм")
    print(f"  clearance.ok = {result.clearance.clearance.ok}")
    print(f"  fingerprint = {result.computed_fingerprint}")

    print()
    print("=== Проверка отклонения (защита от несовместимой геометрии) ===")
    bad_geometry = dataclasses.replace(
        geometry,
        housing_tube_section=dataclasses.replace(
            geometry.housing_tube_section, inner_diameter_mm=68.0, outer_diameter_mm=80.0
        ),
    )
    try:
        calculate_structural_chain(bad_geometry, loads, clearance_inputs, bearing_catalog)
        print("  ОШИБКА ТЕСТА: несовместимая геометрия НЕ была отклонена!")
    except Exception as exc:  # noqa: BLE001 - демонстрация контролируемого отказа
        print(f"  Отклонено, как и ожидалось: {type(exc).__name__}: {exc}")

    print()
    print("=== Таблица приёмки (acceptance_table), фрагмент ===")
    for row in result.acceptance_table:
        print(f"  [{row.status}] {row.node} / {row.mode}: {row.result} ({row.criterion})")

    print()
    print("=== Нерешённые вопросы (unresolved_items) ===")
    for item in result.unresolved_items:
        print(f"  - {item}")


if __name__ == "__main__":
    main()
