"""Броски кубиков для Мастера: d4, d6, d8, d10, d12, d20."""

import random

from gm_hub.logic.errors import ValidationError

SIDES = (4, 6, 8, 10, 12, 20)


def roll(sides: int, count: int = 1, rng=random) -> list:
    """Бросает count кубиков с sides гранями.

    Args:
        sides: Число граней (4, 6, 8, 10, 12 или 20).
        count: Сколько кубиков бросить (от 1 до 10).
        rng: Генератор случайных чисел (в тестах — с фиксированным seed).

    Returns:
        Список выпавших значений.

    Raises:
        ValidationError: Если такого кубика нет или их число неверное.
    """
    if sides not in SIDES:
        raise ValidationError("Кубик", f"Кубика d{sides} нет.")
    if not 1 <= count <= 10:
        raise ValidationError("Кубик", "Можно бросить от 1 до 10 кубиков.")
    return [rng.randint(1, sides) for _ in range(count)]
