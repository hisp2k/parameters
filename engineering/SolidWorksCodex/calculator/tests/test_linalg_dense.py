# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.core.linalg_dense import (
    LinAlgError, solve_linear_system, matmul, transpose, mat_vec, zeros,
)


def test_solve_linear_system_matches_known_solution():
    # 2x + y = 5 ; x + 3y = 10  → x=1, y=3
    a = [[2.0, 1.0], [1.0, 3.0]]
    b = [5.0, 10.0]
    x = solve_linear_system(a, b)
    assert x[0] == pytest.approx(1.0)
    assert x[1] == pytest.approx(3.0)


def test_solve_linear_system_requires_pivoting_for_zero_leading_entry():
    # Первый ведущий элемент нулевой — без pivoting наивный Гаусс сломается.
    a = [[0.0, 2.0], [3.0, 1.0]]
    b = [4.0, 5.0]
    x = solve_linear_system(a, b)
    # Проверка подстановкой.
    assert 0.0 * x[0] + 2.0 * x[1] == pytest.approx(4.0)
    assert 3.0 * x[0] + 1.0 * x[1] == pytest.approx(5.0)


def test_solve_linear_system_detects_singular_matrix():
    a = [[1.0, 2.0], [2.0, 4.0]]  # вторая строка = 2×первая — вырождена
    with pytest.raises(LinAlgError):
        solve_linear_system(a, [1.0, 2.0])


def test_matmul_and_transpose_identity_roundtrip():
    a = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    at = transpose(a)
    ata = matmul(a, at)
    assert ata[0][0] == pytest.approx(1 + 4 + 9)
    assert ata[1][1] == pytest.approx(16 + 25 + 36)


def test_mat_vec():
    a = [[1.0, 0.0], [0.0, 1.0]]
    assert mat_vec(a, [3.0, 7.0]) == pytest.approx([3.0, 7.0])
