# -*- coding: utf-8 -*-
"""
Минимальный плотный линейный решатель на чистом Python (без numpy/scipy).

ПОЧЕМУ ЧИСТЫЙ PYTHON. `calculator/requirements.txt` объявляет только
`reportlab`/`Flask`/`pytest` — калькулятор обязан оставаться запускаемым
через `RUN_WEBAPP.cmd` без установки дополнительных пакетов на машине
пользователя (см. верхнеуровневый README_RU.md — предпосылка "работает из
коробки"). Метод перемещений для пространственной рамы (core/frame_model.py)
не требует ничего сложнее решения СЛАУ методом Гаусса с выбором главного
элемента по столбцу — для реальных размеров рам/корпусов этого репозитория
(десятки-сотни степеней свободы) производительность чистого Python
достаточна, а новая обязательная зависимость — нет.
"""

from __future__ import annotations

import math

Matrix = list  # list[list[float]]
Vector = list  # list[float]


class LinAlgError(ValueError):
    pass


def zeros(rows: int, cols: int) -> Matrix:
    return [[0.0] * cols for _ in range(rows)]


def zeros_vector(n: int) -> Vector:
    return [0.0] * n


def matmul(a: Matrix, b: Matrix) -> Matrix:
    n, k = len(a), len(a[0]) if a else 0
    k2, m = len(b), len(b[0]) if b else 0
    if k != k2:
        raise LinAlgError(f"Несовместные размеры матриц для умножения: {k} != {k2}.")
    result = zeros(n, m)
    for i in range(n):
        row = a[i]
        for p in range(k):
            v = row[p]
            if v == 0.0:
                continue
            brow = b[p]
            rrow = result[i]
            for j in range(m):
                rrow[j] += v * brow[j]
    return result


def transpose(a: Matrix) -> Matrix:
    if not a:
        return []
    return [list(row) for row in zip(*a)]


def mat_vec(a: Matrix, x: Vector) -> Vector:
    n = len(a)
    k = len(a[0]) if a else 0
    if k != len(x):
        raise LinAlgError(f"Несовместные размеры для умножения матрицы на вектор: {k} != {len(x)}.")
    return [sum(a[i][j] * x[j] for j in range(k)) for i in range(n)]


def solve_linear_system(a: Matrix, b: Vector, *, tol: float = 1e-9) -> Vector:
    """
    Решает A·x = b методом Гаусса с выбором главного элемента по столбцу
    (частичный pivoting) — устойчиво для симметричных положительно
    определённых матриц жёсткости метода перемещений. Явно проверяет
    вырожденность (нулевой ведущий элемент после перестановки строк) —
    это обычно означает механизм (недостаточно опор) в модели, а не
    численную случайность, поэтому диагностируется отдельной ошибкой,
    а не "тихим" NaN/Inf.
    """
    n = len(a)
    if n == 0:
        return []
    if any(len(row) != n for row in a):
        raise LinAlgError("Матрица A должна быть квадратной.")
    if len(b) != n:
        raise LinAlgError(f"Размер b ({len(b)}) не совпадает с размером A ({n}).")

    # Копия с расширенным столбцом b, чтобы не портить вход вызывающего кода.
    aug = [row[:] + [b[i]] for i, row in enumerate(a)]

    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(aug[r][col]))
        pivot_val = aug[pivot_row][col]
        if abs(pivot_val) < tol:
            raise LinAlgError(
                f"Вырожденная матрица (нулевой главный элемент в столбце {col}) — "
                "модель, вероятно, является механизмом (недостаточно опор/связей для "
                "устойчивого равновесия), а не численная погрешность."
            )
        if pivot_row != col:
            aug[col], aug[pivot_row] = aug[pivot_row], aug[col]
        pivot_val = aug[col][col]
        for r in range(col + 1, n):
            factor = aug[r][col] / pivot_val
            if factor == 0.0:
                continue
            for c in range(col, n + 1):
                aug[r][c] -= factor * aug[col][c]

    x = [0.0] * n
    for row in range(n - 1, -1, -1):
        s = aug[row][n] - sum(aug[row][c] * x[c] for c in range(row + 1, n))
        x[row] = s / aug[row][row]
    return x


def is_finite_matrix(a: Matrix) -> bool:
    return all(math.isfinite(v) for row in a for v in row)
