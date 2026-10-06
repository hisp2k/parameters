# -*- coding: utf-8 -*-
"""
Веб-интерфейс на русском языке (раздел 2 задания): "пользователь никогда
не редактирует JSON напрямую". Отдельный пакет `calculator.webapp`, поверх
уже существующего расчётного конвейера `calculator/app.py` — веб-слой не
пересчитывает инженерное ядро/привод/технологию самостоятельно, а вызывает
те же функции (`create_project`, `recompute_and_save`), которыми пользуется
CLI-сценарий, чтобы не разойтись с ним в цифрах.

Запуск:
    cd calculator
    python3 -m webapp.app

ИСПРАВЛЕНИЕ: раньше здесь был абсолютный импорт `from calculator.webapp.app
import create_app`, который требует, чтобы пакет `calculator` был на
sys.path ДО того, как этот файл вообще начнёт выполняться — а именно в
этот момент (инициализация пакета `webapp` при `python -m webapp.app` из
каталога `calculator/`) это ещё не так: получалась
`ModuleNotFoundError: No module named 'calculator'` прямо при запуске
веб-интерфейса, хотя `calculator/app.py` (CLI) сам себе чинит sys.path и
поэтому запускался нормально. Здесь чиним sys.path так же, до импорта, и
используем ОТНОСИТЕЛЬНЫЙ импорт `.app` — он работает независимо от того,
виден ли пакет `webapp` как `webapp` (запуск из `calculator/`) или как
`calculator.webapp` (запуск из корня репозитория).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from .app import create_app

__all__ = ["create_app"]
