"""Показатели прогресса студента."""
from typing import List

from .domain import Status


def calculate_progress(statuses: List[Status]) -> int:
    """Процент принятых работ (целое число от 0 до 100)."""
    if not statuses:
        return 0
    accepted = sum(1 for s in statuses if s == Status.ACCEPTED)
    return accepted * 100 // len(statuses)


def format_days_left(days: int) -> str:
    """Подпись срока для интерфейса: «сегодня», «завтра», «через N дней», «просрочено на N дней»."""
    if days == 0:
        return "сегодня"
    if days == 1:
        return "завтра"
    if days < 0:
        n = -days
        return f"просрочено на {n} " + _days_word(n)
    return f"через {days} " + _days_word(days)


def _days_word(n: int) -> str:
    """Правильная форма слова «день» для числа n (1 день, 2 дня, 5 дней)."""
    if 11 <= n % 100 <= 14:
        return "дней"
    last = n % 10
    if last == 1:
        return "день"
    if 2 <= last <= 4:
        return "дня"
    return "дней"
